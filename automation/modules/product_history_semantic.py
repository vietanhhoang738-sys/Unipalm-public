"""Product-domain historical Semantic backfill.

This layer intentionally has its own failure boundary. A historical month may be
invalid for full-shop Processed promotion (for example Orders vs BI
reconciliation) while Product Performance itself is structurally valid. In that
case we do NOT relax full-shop QA; we validate Product-specific staging facts and
persist only Product semantic history.

Canonical portfolio Semantic v2 still has precedence whenever the same
shop/month exists there.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .semantic_mart import _product_monthly_rows


LAYER_NAME = "product_history_semantic_v1"


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def n(v: Any) -> float:
    if v in (None, ""):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def ratio(num: Any, den: Any) -> float:
    d = n(den)
    return n(num) / d if d else 0.0


def sha256_json(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}: line {line_no} is not an object")
            out.append(row)
    return out


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")


def load_contract(path: str | Path) -> Dict[str, Any]:
    data = read_json(Path(path))
    if s(data.get("layer_name")) != LAYER_NAME or s(data.get("status")) != "PREPRODUCTION":
        raise ValueError("unexpected Product history backfill contract")
    source = data.get("source_policy") or {}
    if s(source.get("failure_domain")) != "PRODUCT_ONLY":
        raise ValueError("Product history backfill must remain Product-only")
    if bool(source.get("full_shop_processed_promotion_implied")) or bool(source.get("full_shop_semantic_promotion_implied")):
        raise ValueError("Product history backfill cannot imply full-shop promotion")
    safety = data.get("safety") or {}
    if any(bool(safety.get(key)) for key in (
        "write_legacy_processed", "write_production_data_mart", "modify_production_ui",
        "publish_canonical_portfolio_semantic", "platform_mutation_allowed", "production_activation_enabled",
    )):
        raise ValueError("unsafe Product history backfill contract")
    return data


def _normalize_historical_catalog_state(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        if (
            s(row.get("catalog_join_status")) == "MISSING_CURRENT_CATALOG"
            and not bool(row.get("current_listing_present"))
        ):
            row["catalog_join_status"] = "HISTORICAL_NO_CURRENT_LISTING"
            if not s(row.get("catalog_status")):
                row["catalog_status"] = "NOT_IN_CURRENT_CATALOG"
        out.append(row)
    return out


def _check_map(staging_qa: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {s(x.get("name")): x for x in staging_qa.get("checks") or [] if s(x.get("name"))}


def _domain_schema_state(schema_report: Mapping[str, Any], relevant_contracts: Sequence[str]) -> Dict[str, Any]:
    relevant = set(relevant_contracts)
    selected = [x for x in schema_report.get("audits") or [] if s(x.get("contract")) in relevant]
    failures = [x for x in selected if s(x.get("status")) == "FAIL"]
    warnings = [x for x in selected if s(x.get("status")) == "WARN"]
    return {
        "status": "FAIL" if failures else ("WARN" if warnings else "PASS"),
        "auditCount": len(selected),
        "warningCount": len(warnings),
        "failureCount": len(failures),
        "warnings": [
            {
                "contract": s(x.get("contract")),
                "sourceName": s(x.get("source_name")),
                "unknownColumns": list(x.get("unknown_columns") or []),
                "fingerprint": s(x.get("fingerprint")),
            }
            for x in warnings
        ],
        "failures": [
            {
                "contract": s(x.get("contract")),
                "sourceName": s(x.get("source_name")),
                "missingRequired": list(x.get("missing_required") or x.get("missing_required_columns") or []),
                "unknownColumns": list(x.get("unknown_columns") or []),
            }
            for x in failures
        ],
    }


def build_product_history_partition(
    *,
    staging_dir: str | Path,
    output_dir: str | Path,
    shop: Mapping[str, Any],
    period: str,
    contract_path: str | Path,
    generated_at: str = "",
) -> Dict[str, Any]:
    staging_dir = Path(staging_dir)
    output_dir = Path(output_dir)
    contract = load_contract(contract_path)
    sid = s(shop.get("shop_id")); sk = s(shop.get("shop_key"))
    if not sid or not sk:
        raise ValueError("Product history backfill requires shop identity")

    required_files = list(contract.get("required_staging_files") or [])
    missing_files = [name for name in required_files if not (staging_dir / name).exists()]
    if missing_files:
        raise FileNotFoundError(f"{sk}/{period}: Product history staging files missing: {missing_files}")

    staging_qa = read_json(staging_dir / "staging_qa_report.json")
    schema_report = read_json(staging_dir / "schema_drift_report.json")
    if s(staging_qa.get("shop_id")) != sid or s(staging_qa.get("target_month")) != period:
        raise ValueError(f"{sk}/{period}: staging QA scope mismatch")
    if s(schema_report.get("shop_id")) != sid or s(schema_report.get("month")) != period:
        raise ValueError(f"{sk}/{period}: schema report scope mismatch")

    checks: List[Dict[str, Any]] = []
    def ck(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    source_checks = _check_map(staging_qa)
    required_checks = list(contract.get("required_staging_checks") or [])
    for name in required_checks:
        source = source_checks.get(name) or {}
        ck(f"staging_{name}", s(source.get("status")) == "PASS", source.get("detail") or {})

    schema_policy = contract.get("schema_policy") or {}
    domain_schema = _domain_schema_state(schema_report, schema_policy.get("relevant_contracts") or [])
    ck("product_domain_schema_no_fail", domain_schema["status"] != "FAIL", domain_schema)

    products = read_jsonl(staging_dir / "fact_product_performance_monthly.jsonl")
    ads_product = read_jsonl(staging_dir / "dm_ads_product_daily_candidate.jsonl")
    catalog = read_jsonl(staging_dir / "catalog_resolution_staging.jsonl")
    listing_products = read_jsonl(staging_dir / "listing_catalog_products_snapshot.jsonl")

    for label, rows in (
        ("products", products), ("adsProduct", ads_product),
        ("catalog", catalog), ("listingProducts", listing_products),
    ):
        foreign = sorted({s(r.get("shop_id")) for r in rows if s(r.get("shop_id")) != sid})
        ck(f"{label}_shop_isolation", not foreign, {"foreignShopIds": foreign})

    wrong_product_months = sorted({s(r.get("data_month")) for r in products if s(r.get("data_month")) != period})
    ck("product_source_month_alignment", not wrong_product_months, {"wrongMonths": wrong_product_months})

    part = {
        "shop": dict(shop),
        "products": products,
        "ads_product": ads_product,
        "catalog": catalog,
        "listing_products": listing_products,
    }
    semantic_rows = _normalize_historical_catalog_state(
        _product_monthly_rows(part, period, ads_product)
    )

    foreign_semantic = sorted({s(r.get("shop_id")) for r in semantic_rows if s(r.get("shop_id")) != sid})
    wrong_semantic_months = sorted({s(r.get("data_month")) for r in semantic_rows if s(r.get("data_month")) != period})
    seen = set(); duplicates = []; ratio_errors = []
    for row in semantic_rows:
        pid = s(row.get("product_id"))
        if pid in seen:
            duplicates.append(pid)
        seen.add(pid)
        expected_aov = ratio(row.get("placed_gmv"), row.get("placed_orders"))
        expected_roas = ratio(row.get("ads_attributed_sales"), row.get("ads_spend"))
        if abs(n(row.get("placed_aov")) - expected_aov) > 1e-9:
            ratio_errors.append((pid, "placed_aov"))
        if abs(n(row.get("roas")) - expected_roas) > 1e-9:
            ratio_errors.append((pid, "roas"))
    ck("semantic_shop_isolation", not foreign_semantic, {"foreignShopIds": foreign_semantic})
    ck("semantic_month_alignment", not wrong_semantic_months, {"wrongMonths": wrong_semantic_months})
    ck("semantic_product_grain_unique", not duplicates, {"duplicates": duplicates[:20]})
    ck("semantic_ratios_recomputed", not ratio_errors, {"errors": ratio_errors[:20]})
    ck("semantic_has_product_rows", bool(semantic_rows), {"rowCount": len(semantic_rows)})

    failed = [x for x in checks if x["status"] == "FAIL"]
    if failed:
        raise ValueError(f"{sk}/{period}: Product history QA failed: {[x['name'] for x in failed]}")

    source_files = {
        name: sha256_file(staging_dir / name)
        for name in required_files
    }
    source_fingerprint = sha256_json({
        "shopId": sid,
        "period": period,
        "files": source_files,
        "domainSchema": domain_schema,
        "requiredCheckStates": {
            name: s((source_checks.get(name) or {}).get("status"))
            for name in required_checks
        },
    })
    semantic_fingerprint = sha256_json({
        "layer": LAYER_NAME,
        "contractVersion": contract.get("version"),
        "shopId": sid,
        "period": period,
        "sourceFingerprint": source_fingerprint,
        "rows": semantic_rows,
    })

    output_dir.mkdir(parents=True, exist_ok=True)
    mart_path = output_dir / "dm_product_monthly.jsonl"
    write_jsonl(mart_path, semantic_rows)
    qa = {
        "status": "PASS",
        "shopKey": sk,
        "shopId": sid,
        "period": period,
        "productHistorySemanticReady": True,
        "sourceFullShopStagingStatus": s(staging_qa.get("status")),
        "sourceFullShopPromotionAllowed": bool(staging_qa.get("production_write_allowed")),
        "productDomainSchema": domain_schema,
        "sourceFingerprint": source_fingerprint,
        "productHistorySemanticFingerprint": semantic_fingerprint,
        "failedCheckCount": 0,
        "checks": checks,
        "safety": {
            "fullShopProcessedPromotionPerformed": False,
            "canonicalPortfolioSemanticPublished": False,
            "productionDataMartWritten": False,
            "productionUiModified": False,
            "platformMutationAllowed": False,
        },
    }
    manifest = {
        "layer": LAYER_NAME,
        "contractVersion": s(contract.get("version")),
        "shopKey": sk,
        "shopId": sid,
        "period": period,
        "generatedAt": generated_at,
        "sourceFingerprint": source_fingerprint,
        "productHistorySemanticFingerprint": semantic_fingerprint,
        "sourceFullShopStagingStatus": s(staging_qa.get("status")),
        "sourceFullShopPromotionAllowed": bool(staging_qa.get("production_write_allowed")),
        "files": [
            {"file": "dm_product_monthly.jsonl", "rows": len(semantic_rows), "sha256": sha256_file(mart_path)}
        ],
        "safety": qa["safety"],
    }
    (output_dir / "product_history_qa_report.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return {
        "status": "PASS",
        "shopKey": sk,
        "shopId": sid,
        "period": period,
        "rowCount": len(semantic_rows),
        "sourceFingerprint": source_fingerprint,
        "productHistorySemanticFingerprint": semantic_fingerprint,
        "sourceFullShopStagingStatus": s(staging_qa.get("status")),
        "sourceFullShopPromotionAllowed": bool(staging_qa.get("production_write_allowed")),
        "outputLocation": str(output_dir),
        "safety": qa["safety"],
    }
