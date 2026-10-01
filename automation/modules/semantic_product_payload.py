"""Bind Product Intelligence V2 into the canonical PREPRODUCTION UI payload.

The base multi-shop payload remains authoritative for Command Center/Compare.
This wrapper adds a shop-only Product destination and re-fingerprints the payload
so Product lineage participates in downstream Native QA.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from . import semantic_payload as _base


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _load_product(path: str | Path, *, period: str, expected_shop_ids: list[str]) -> Dict[str, Any]:
    root = Path(path)
    product = _base._read_json(root / "product_intelligence.json")
    qa = _base._read_json(root / "product_intelligence_qa_report.json")
    manifest = _base._read_json(root / "product_intelligence_manifest.json")
    meta = product.get("meta") or {}
    if s(meta.get("layer")) != "multi_shop_product_intelligence_v1":
        raise ValueError("unexpected Product Intelligence layer")
    if s(meta.get("status")) != "PREPRODUCTION":
        raise ValueError("Product Intelligence must remain PREPRODUCTION")
    if s(meta.get("asOfPeriod")) != period:
        raise ValueError("Product Intelligence period mismatch")
    if qa.get("status") != "PASS":
        raise ValueError("Product Intelligence QA is not PASS")
    fp = s(meta.get("productIntelligenceFingerprint"))
    if not fp or fp != s(qa.get("productIntelligenceFingerprint")) or fp != s(manifest.get("productIntelligenceFingerprint")):
        raise ValueError("Product Intelligence fingerprint mismatch")
    if set((product.get("shops") or {}).keys()) != set(expected_shop_ids):
        raise ValueError("Product destination shop scope differs from canonical payload")
    scope = product.get("scopePolicy") or {}
    if not bool(scope.get("singleShopOnly")) or bool(scope.get("compareAllowed")):
        raise ValueError("Product destination must be single-shop only")
    if s(scope.get("canonicalSourceGrain")) != "MONTHLY" or not bool(scope.get("dayWeekForbidden")):
        raise ValueError("Product monthly-grain scope contract missing")
    return product


def _validate_binding(payload: Mapping[str, Any]) -> Dict[str, Any]:
    checks = []
    def ck(name: str, ok: bool, detail: Any = None):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})
    product = ((payload.get("destinations") or {}).get("product") or {})
    scope = product.get("scopePolicy") or {}
    shops = product.get("shops") or {}
    canonical_shop_ids = set((payload.get("shops") or {}).keys())
    ck("product_destination_present", bool(product))
    ck("product_destination_single_shop_only", bool(scope.get("singleShopOnly")) and not bool(scope.get("compareAllowed")))
    ck("product_destination_monthly_grain", s(scope.get("canonicalSourceGrain")) == "MONTHLY" and bool(scope.get("dayWeekForbidden")))
    ck("product_destination_time_scopes", list(scope.get("allowedTimeScopes") or []) == ["oneMonth", "threeMonths", "sixMonths", "year"])
    ck("product_destination_shop_scope_matches", set(shops) == canonical_shop_ids, {"product": sorted(shops), "canonical": sorted(canonical_shop_ids)})
    ck("product_destination_has_no_compare_surface", "compare" not in product)
    for sid, shop in shops.items():
        ck(f"{sid}_product_compare_disabled", shop.get("compareAllowed") is False)
        ck(f"{sid}_product_source_grain_monthly", s(shop.get("sourceGrain")) == "MONTHLY")
        ck(f"{sid}_product_horizon_order", list(shop.get("timeScopeOrder") or []) == ["oneMonth", "threeMonths", "sixMonths", "year"])
    safety = payload.get("safety") or {}
    ck("product_binding_production_safety", not bool(safety.get("productionCutoverAuthorized")) and not bool(safety.get("productionActivationEnabled")))
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_ui_payload(
    *,
    semantic_dir: str | Path,
    output_dir: str | Path,
    contract_path: str | Path,
    historical_path: str | Path | None = None,
    product_intelligence_dir: str | Path | None = None,
):
    result = _base.build_ui_payload(
        semantic_dir=semantic_dir,
        output_dir=output_dir,
        contract_path=contract_path,
        historical_path=historical_path,
    )
    if not product_intelligence_dir:
        raise ValueError("Product Intelligence binding is required for Product V2 destination")

    output_dir = Path(output_dir)
    payload_path = output_dir / "ui_payload.json"
    manifest_path = output_dir / "payload_manifest.json"
    qa_path = output_dir / "payload_qa_report.json"
    payload = _base._read_json(payload_path)
    manifest = _base._read_json(manifest_path)
    qa = _base._read_json(qa_path)
    period = s((payload.get("meta") or {}).get("period"))
    shop_ids = list((payload.get("shops") or {}).keys())
    product = _load_product(product_intelligence_dir, period=period, expected_shop_ids=shop_ids)
    product_fp = s((product.get("meta") or {}).get("productIntelligenceFingerprint"))

    payload.setdefault("destinations", {})["product"] = product
    payload.setdefault("capabilities", {})["productDestinationV2"] = True
    payload["capabilities"]["productMultiMonthScopes"] = True
    payload["capabilities"]["productStructuralIntelligence"] = bool((product.get("capabilities") or {}).get("productStructuralIntelligence"))
    payload["meta"]["sourceProductIntelligenceFingerprint"] = product_fp

    binding_qa = _validate_binding(payload)
    if binding_qa["status"] != "PASS":
        failed = [x["name"] for x in binding_qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Product payload binding QA failed: {failed}")

    payload_hash = _base._sha256_json(payload)
    fingerprint = _base._sha256_json({
        "contractVersion": payload["meta"].get("payloadContractVersion"),
        "semanticFingerprint": payload["meta"].get("sourceSemanticFingerprint"),
        "historicalFingerprint": payload["meta"].get("sourceHistoricalFingerprint"),
        "productIntelligenceFingerprint": product_fp,
        "payloadSha256": payload_hash,
    })
    _base._write_json(payload_path, payload)
    manifest.update({
        "payloadBuildFingerprint": fingerprint,
        "payloadSha256": payload_hash,
        "sourceProductIntelligenceFingerprint": product_fp,
        "files": [{"file": "ui_payload.json", "sha256": payload_hash}],
    })
    _base._write_json(manifest_path, manifest)
    qa.update({
        "payloadBuildFingerprint": fingerprint,
        "sourceProductIntelligenceFingerprint": product_fp,
        "productDestinationBinding": binding_qa,
    })
    _base._write_json(qa_path, qa)
    return {
        **result,
        "payloadBuildFingerprint": fingerprint,
        "sourceProductIntelligenceFingerprint": product_fp,
        "productDestinationReady": True,
    }
