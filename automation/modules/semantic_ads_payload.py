"""Bind Ads Intelligence V2 into canonical PREPRODUCTION UI payload.

Command Center/Compare and Product remain unchanged. This layer adds a shop-only
Ads destination and re-fingerprints the payload so Ads lineage participates in
Native QA.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from . import semantic_product_payload as _product
from . import semantic_payload as _base


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _load_ads(path: str | Path, *, period: str, expected_shop_ids: list[str]) -> Dict[str, Any]:
    root = Path(path)
    ads = _base._read_json(root / "ads_intelligence.json")
    qa = _base._read_json(root / "ads_intelligence_qa_report.json")
    manifest = _base._read_json(root / "ads_intelligence_manifest.json")
    meta = ads.get("meta") or {}
    if s(meta.get("layer")) != "multi_shop_ads_intelligence_v1":
        raise ValueError("unexpected Ads Intelligence layer")
    if s(meta.get("status")) != "PREPRODUCTION":
        raise ValueError("Ads Intelligence must remain PREPRODUCTION")
    if s(meta.get("asOfPeriod")) != period:
        raise ValueError("Ads Intelligence period mismatch")
    if qa.get("status") != "PASS":
        raise ValueError("Ads Intelligence QA is not PASS")
    fp = s(meta.get("adsIntelligenceFingerprint"))
    if not fp or fp != s(qa.get("adsIntelligenceFingerprint")) or fp != s(manifest.get("adsIntelligenceFingerprint")):
        raise ValueError("Ads Intelligence fingerprint mismatch")
    if set((ads.get("shops") or {}).keys()) != set(expected_shop_ids):
        raise ValueError("Ads destination shop scope differs from canonical payload")
    scope = ads.get("scopePolicy") or {}
    if not bool(scope.get("singleShopOnly")) or bool(scope.get("compareAllowed")):
        raise ValueError("Ads destination must be single-shop only")
    if s(scope.get("canonicalSourceGrain")) != "DAILY":
        raise ValueError("Ads daily-grain scope contract missing")
    if list(scope.get("allowedTimeScopes") or []) != ["day", "week", "month", "year"]:
        raise ValueError("Ads time-scope contract mismatch")
    return ads


def _validate_binding(payload: Mapping[str, Any]) -> Dict[str, Any]:
    checks = []
    def ck(name: str, ok: bool, detail: Any = None):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    ads = ((payload.get("destinations") or {}).get("ads") or {})
    scope = ads.get("scopePolicy") or {}
    shops = ads.get("shops") or {}
    canonical_shop_ids = set((payload.get("shops") or {}).keys())
    ck("ads_destination_present", bool(ads))
    ck("ads_destination_single_shop_only", bool(scope.get("singleShopOnly")) and not bool(scope.get("compareAllowed")))
    ck("ads_destination_daily_grain", s(scope.get("canonicalSourceGrain")) == "DAILY")
    ck("ads_destination_time_scopes", list(scope.get("allowedTimeScopes") or []) == ["day", "week", "month", "year"])
    ck("ads_destination_shop_scope_matches", set(shops) == canonical_shop_ids, {"ads": sorted(shops), "canonical": sorted(canonical_shop_ids)})
    ck("ads_destination_has_no_compare_surface", "compare" not in ads)
    for sid, shop in shops.items():
        ck(f"{sid}_ads_compare_disabled", shop.get("compareAllowed") is False)
        ck(f"{sid}_ads_source_grain_daily", s(shop.get("sourceGrain")) == "DAILY")
        ck(f"{sid}_ads_time_scope_order", list(shop.get("timeScopeOrder") or []) == ["day", "week", "month", "year"])
    safety = payload.get("safety") or {}
    ck("ads_binding_production_safety", not bool(safety.get("productionCutoverAuthorized")) and not bool(safety.get("productionActivationEnabled")))
    failed = [x for x in checks if x["status"] == "FAIL"]
    return {"status": "PASS" if not failed else "FAIL", "failedCheckCount": len(failed), "checks": checks}


def build_ui_payload(
    *,
    semantic_dir: str | Path,
    output_dir: str | Path,
    contract_path: str | Path,
    historical_path: str | Path | None = None,
    product_intelligence_dir: str | Path | None = None,
    ads_intelligence_dir: str | Path | None = None,
):
    result = _product.build_ui_payload(
        semantic_dir=semantic_dir,
        output_dir=output_dir,
        contract_path=contract_path,
        historical_path=historical_path,
        product_intelligence_dir=product_intelligence_dir,
    )
    if not ads_intelligence_dir:
        raise ValueError("Ads Intelligence binding is required for Ads V2 destination")

    output_dir = Path(output_dir)
    payload_path = output_dir / "ui_payload.json"
    manifest_path = output_dir / "payload_manifest.json"
    qa_path = output_dir / "payload_qa_report.json"
    payload = _base._read_json(payload_path)
    manifest = _base._read_json(manifest_path)
    qa = _base._read_json(qa_path)
    period = s((payload.get("meta") or {}).get("period"))
    shop_ids = list((payload.get("shops") or {}).keys())
    ads = _load_ads(ads_intelligence_dir, period=period, expected_shop_ids=shop_ids)
    ads_fp = s((ads.get("meta") or {}).get("adsIntelligenceFingerprint"))

    payload.setdefault("destinations", {})["ads"] = ads
    payload.setdefault("capabilities", {})["adsDestinationV2"] = True
    payload["capabilities"]["adsDailyScopes"] = True
    payload["capabilities"]["adsPeriodComparison"] = True
    payload["capabilities"]["adsRoasDriverAttribution"] = True
    payload["meta"]["sourceAdsIntelligenceFingerprint"] = ads_fp

    binding_qa = _validate_binding(payload)
    if binding_qa["status"] != "PASS":
        failed = [x["name"] for x in binding_qa["checks"] if x["status"] == "FAIL"]
        raise ValueError(f"Ads payload binding QA failed: {failed}")

    payload_hash = _base._sha256_json(payload)
    fingerprint = _base._sha256_json({
        "contractVersion": payload["meta"].get("payloadContractVersion"),
        "semanticFingerprint": payload["meta"].get("sourceSemanticFingerprint"),
        "historicalFingerprint": payload["meta"].get("sourceHistoricalFingerprint"),
        "productIntelligenceFingerprint": payload["meta"].get("sourceProductIntelligenceFingerprint"),
        "adsIntelligenceFingerprint": ads_fp,
        "payloadSha256": payload_hash,
    })
    _base._write_json(payload_path, payload)
    manifest.update({
        "payloadBuildFingerprint": fingerprint,
        "payloadSha256": payload_hash,
        "sourceAdsIntelligenceFingerprint": ads_fp,
        "files": [{"file": "ui_payload.json", "sha256": payload_hash}],
    })
    _base._write_json(manifest_path, manifest)
    qa.update({
        "payloadBuildFingerprint": fingerprint,
        "sourceAdsIntelligenceFingerprint": ads_fp,
        "adsDestinationBinding": binding_qa,
    })
    _base._write_json(qa_path, qa)
    return {
        **result,
        "payloadBuildFingerprint": fingerprint,
        "sourceAdsIntelligenceFingerprint": ads_fp,
        "adsDestinationReady": True,
    }
