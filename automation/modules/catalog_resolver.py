"""Cross-shop catalog resolver.

Resolve listing identity across Shopee shops without requiring every listing to
have a product-level SKU populated in Seller Center.

The resolver deliberately separates:
1) Shopee listing parent SKU (channel metadata),
2) canonical product family used for cross-shop analysis,
3) sellable variation SKU.

It never rewrites SKU Master and never guesses a parent SKU from string prefixes.
All automatic decisions require explicit evidence from a reference listing
and/or SKU Master family metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re
import unicodedata
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


@dataclass
class ListingRecord:
    shop_id: str
    product_id: str
    title: str
    parent_sku: str = ""
    variation_skus: Set[str] = field(default_factory=set)


@dataclass
class Resolution:
    shop_id: str
    product_id: str
    title: str
    observed_parent_sku: str
    resolved_parent_sku: str
    canonical_family_key: str
    reference_product_id: str
    reference_shop_id: str
    status: str
    confidence: float
    evidence: Dict[str, object]


STOPWORDS = {
    "unipalm","khau","trang","gang","tay","chong","tia","uv","upf","upf50",
    "cho","nu","nam","vai","lua","bang","mem","mai","mat","lanh","san","pham",
    "moi","cao","cap","danh","dai",
}


def _ascii(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def normalize_title(s: str) -> str:
    s = _ascii(s).lower()
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_tokens(s: str) -> Set[str]:
    return {t for t in normalize_title(s).split() if len(t) > 1 and t not in STOPWORDS}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_title(a), normalize_title(b)
    token = _jaccard(title_tokens(a), title_tokens(b))
    seq = SequenceMatcher(None, na, nb).ratio() if na or nb else 0.0
    return 0.65 * token + 0.35 * seq


def _variation_metrics(target: Set[str], reference: Set[str]) -> Dict[str, float]:
    if not target and not reference:
        return {"intersection": 0, "jaccard": 1.0, "target_coverage": 1.0, "reference_coverage": 1.0}
    inter = len(target & reference)
    union = len(target | reference)
    return {
        "intersection": inter,
        "jaccard": inter / union if union else 0.0,
        "target_coverage": inter / len(target) if target else 0.0,
        "reference_coverage": inter / len(reference) if reference else 0.0,
    }


def infer_family_from_master(
    variation_skus: Iterable[str],
    family_by_sellable_sku: Dict[str, str],
    *,
    min_votes: int = 2,
    min_share: float = 0.67,
) -> Tuple[str, float, Dict[str, int]]:
    """Infer canonical family from exact SKU Master lookups only."""
    votes: Dict[str, int] = {}
    mapped = 0
    for sku in set(variation_skus):
        fam = str(family_by_sellable_sku.get(sku, "") or "").strip()
        if not fam:
            continue
        mapped += 1
        votes[fam] = votes.get(fam, 0) + 1
    if not votes or mapped == 0:
        return "", 0.0, votes
    fam, count = max(votes.items(), key=lambda kv: (kv[1], kv[0]))
    share = count / mapped
    if count >= min_votes and share >= min_share:
        return fam, share, votes
    return "", share, votes


def resolve_listing(
    target: ListingRecord,
    references: Sequence[ListingRecord],
    *,
    family_by_sellable_sku: Optional[Dict[str, str]] = None,
) -> Resolution:
    family_by_sellable_sku = family_by_sellable_sku or {}

    if target.parent_sku:
        family, family_conf, votes = infer_family_from_master(target.variation_skus, family_by_sellable_sku)
        return Resolution(
            shop_id=target.shop_id,
            product_id=target.product_id,
            title=target.title,
            observed_parent_sku=target.parent_sku,
            resolved_parent_sku=target.parent_sku,
            canonical_family_key=family,
            reference_product_id="",
            reference_shop_id="",
            status="DIRECT_PARENT",
            confidence=1.0,
            evidence={"family_confidence": family_conf, "family_votes": votes, "variation_count": len(target.variation_skus)},
        )

    family, family_conf, family_votes = infer_family_from_master(target.variation_skus, family_by_sellable_sku)

    scored = []
    for ref in references:
        if ref.shop_id == target.shop_id:
            continue
        vm = _variation_metrics(target.variation_skus, ref.variation_skus)
        ts = title_similarity(target.title, ref.title)
        score = 0.45 * vm["target_coverage"] + 0.20 * vm["reference_coverage"] + 0.10 * vm["jaccard"] + 0.25 * ts
        scored.append((score, ts, vm, ref))

    scored.sort(key=lambda x: (x[0], x[2]["intersection"], x[1]), reverse=True)
    best = scored[0] if scored else None

    if best:
        score, ts, vm, ref = best
        if ref.parent_sku:
            competing_parent_scores = [
                cand_score
                for cand_score, _, _, cand_ref in scored
                if cand_ref.parent_sku and cand_ref.parent_sku != ref.parent_sku
            ]
            second_score = max(competing_parent_scores, default=0.0)
        else:
            second_score = scored[1][0] if len(scored) > 1 else 0.0
        margin = score - second_score
        same_parent_refs = [
            cand_ref
            for _, _, _, cand_ref in scored
            if ref.parent_sku and cand_ref.parent_sku == ref.parent_sku
        ]
        evidence = {
            "reference_score": round(score, 6),
            "reference_margin": round(margin, 6),
            "title_similarity": round(ts, 6),
            "variation_intersection": int(vm["intersection"]),
            "variation_target_coverage": round(vm["target_coverage"], 6),
            "variation_reference_coverage": round(vm["reference_coverage"], 6),
            "variation_jaccard": round(vm["jaccard"], 6),
            "variation_count": len(target.variation_skus),
            "reference_variation_count": len(ref.variation_skus),
            "family_confidence": round(family_conf, 6),
            "family_votes": family_votes,
            "reference_support_listing_count": len(same_parent_refs),
            "reference_support_shop_count": len({x.shop_id for x in same_parent_refs}),
        }

        competing_parents = {
            cand_ref.parent_sku
            for cand_score, cand_ts, cand_vm, cand_ref in scored
            if cand_ref.parent_sku
            and cand_vm["intersection"] >= 2
            and cand_vm["target_coverage"] >= 0.80
        }
        variation_parent_conflict = len(competing_parents) > 1
        evidence["variation_parent_conflict"] = variation_parent_conflict
        evidence["competing_parent_skus"] = sorted(competing_parents)

        auto_reference = (
            bool(ref.parent_sku)
            and not variation_parent_conflict
            and vm["intersection"] >= 2
            and vm["target_coverage"] >= 0.60
            and ts >= 0.55
            and margin >= 0.08
        )
        if auto_reference:
            return Resolution(
                shop_id=target.shop_id,
                product_id=target.product_id,
                title=target.title,
                observed_parent_sku="",
                resolved_parent_sku=ref.parent_sku,
                canonical_family_key=family,
                reference_product_id=ref.product_id,
                reference_shop_id=ref.shop_id,
                status="AUTO_REFERENCE_PARENT",
                confidence=min(0.98, 0.70 + 0.20 * score + 0.08 * min(1.0, margin)),
                evidence=evidence,
            )

        if family:
            return Resolution(
                shop_id=target.shop_id,
                product_id=target.product_id,
                title=target.title,
                observed_parent_sku="",
                resolved_parent_sku="",
                canonical_family_key=family,
                reference_product_id=ref.product_id if score >= 0.45 else "",
                reference_shop_id=ref.shop_id if score >= 0.45 else "",
                status="FAMILY_ONLY",
                confidence=min(0.95, 0.65 + 0.30 * family_conf),
                evidence=evidence,
            )

        if ts >= 0.84 and margin >= 0.10:
            return Resolution(
                shop_id=target.shop_id,
                product_id=target.product_id,
                title=target.title,
                observed_parent_sku="",
                resolved_parent_sku="",
                canonical_family_key="",
                reference_product_id=ref.product_id,
                reference_shop_id=ref.shop_id,
                status="REVIEW_REFERENCE",
                confidence=min(0.85, 0.55 + 0.25 * ts),
                evidence=evidence,
            )

        if score >= 0.45:
            return Resolution(
                shop_id=target.shop_id,
                product_id=target.product_id,
                title=target.title,
                observed_parent_sku="",
                resolved_parent_sku="",
                canonical_family_key="",
                reference_product_id=ref.product_id,
                reference_shop_id=ref.shop_id,
                status="REVIEW_REFERENCE",
                confidence=min(0.80, 0.45 + 0.30 * score),
                evidence=evidence,
            )

    return Resolution(
        shop_id=target.shop_id,
        product_id=target.product_id,
        title=target.title,
        observed_parent_sku="",
        resolved_parent_sku="",
        canonical_family_key=family,
        reference_product_id="",
        reference_shop_id="",
        status="FAMILY_ONLY" if family else "UNMATCHED",
        confidence=min(0.95, 0.65 + 0.30 * family_conf) if family else 0.0,
        evidence={"variation_count": len(target.variation_skus), "family_confidence": round(family_conf, 6), "family_votes": family_votes},
    )


def resolve_catalog(
    targets: Sequence[ListingRecord],
    references: Sequence[ListingRecord],
    *,
    family_by_sellable_sku: Optional[Dict[str, str]] = None,
) -> List[Resolution]:
    return [resolve_listing(t, references, family_by_sellable_sku=family_by_sellable_sku) for t in targets]
