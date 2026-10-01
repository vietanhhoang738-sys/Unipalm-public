"""Extend Product-history partitions with BI-authoritative shop commercial metrics.

The base Product history boundary stays Product-only for promotion purposes. This
adapter persists one additional supporting mart derived only from normalized
Business Insights placed/confirmed/paid stages. It never upgrades a failed
full-shop staging partition to Processed/Semantic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from . import product_history_drive_writer as _drive
from . import product_history_semantic as _base
from .product_shop_metrics import monthly_from_bi_stage


COMMERCIAL_MART = "dm_shop_commercial_monthly.jsonl"
PRODUCT_MART = "dm_product_monthly.jsonl"


def _write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")


def build_product_history_partition(*, staging_dir, output_dir, shop, period, contract_path, generated_at="") -> Dict[str, Any]:
    result = _base.build_product_history_partition(
        staging_dir=staging_dir,
        output_dir=output_dir,
        shop=shop,
        period=period,
        contract_path=contract_path,
        generated_at=generated_at,
    )
    staging = Path(staging_dir)
    out = Path(output_dir)
    sid = str(shop.get("shop_id") or "").strip()
    bi_path = staging / "fact_shop_performance_daily.jsonl"
    if not bi_path.exists():
        raise FileNotFoundError(f"{shop.get('shop_key')}/{period}: missing {bi_path.name}")
    bi_rows = _base.read_jsonl(bi_path)
    commercial = monthly_from_bi_stage(bi_rows, shop_id=sid, period=period)

    commercial_path = out / COMMERCIAL_MART
    _write_jsonl(commercial_path, [commercial])
    qa_path = out / "product_history_qa_report.json"
    manifest_path = out / "manifest.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    product_rows = _base.read_jsonl(out / PRODUCT_MART)
    product_gmv = sum(_base.n(r.get("placed_gmv")) for r in product_rows)
    bi_gmv = _base.n(commercial.get("placed_gmv"))
    gmv_diff = abs(product_gmv - bi_gmv) / bi_gmv if bi_gmv else (0.0 if product_gmv == 0 else 1.0)
    qa.setdefault("checks", []).extend([
        {
            "name": "supporting_bi_shop_metric_present",
            "status": "PASS",
            "detail": {
                "placedOrders": commercial.get("placed_orders"),
                "placedAov": commercial.get("placed_aov"),
                "coverageStart": commercial.get("coverage_start"),
                "coverageEnd": commercial.get("coverage_end"),
            },
        },
        {
            "name": "product_gmv_vs_bi_observability",
            "status": "PASS",
            "detail": {
                "productPlacedGmv": product_gmv,
                "biPlacedGmv": bi_gmv,
                "relativeDifference": gmv_diff,
                "gateRole": "OBSERVABILITY_ONLY",
            },
        },
    ])
    qa["shopCommercialMetricReady"] = True
    qa["shopCommercialMetricSource"] = "BUSINESS_INSIGHTS_SHOP_LEVEL"

    new_fp = _base.sha256_json({
        "baseProductHistorySemanticFingerprint": manifest.get("productHistorySemanticFingerprint"),
        "shopCommercialMetric": commercial,
        "supportingMetricVersion": "1.0",
    })
    qa["productHistorySemanticFingerprint"] = new_fp
    manifest["productHistorySemanticFingerprint"] = new_fp
    manifest["files"] = [
        {"file": PRODUCT_MART, "rows": len(product_rows), "sha256": _base.sha256_file(out / PRODUCT_MART)},
        {"file": COMMERCIAL_MART, "rows": 1, "sha256": _base.sha256_file(commercial_path)},
    ]
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {
        **result,
        "productHistorySemanticFingerprint": new_fp,
        "shopCommercialMetricReady": True,
        "shopCommercialMetric": commercial,
    }


def _validate_extended_local_partition(partition_dir, *, shop_key: str, period: str):
    root = Path(partition_dir)
    manifest_path = root / "manifest.json"
    qa_path = root / "product_history_qa_report.json"
    for name in (PRODUCT_MART, COMMERCIAL_MART):
        if not (root / name).exists():
            raise FileNotFoundError(f"Product history partition missing {name}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    if _drive.s(manifest.get("layer")) != _drive.LAYER_NAME:
        raise ValueError("Product history layer mismatch")
    if _drive.s(manifest.get("shopKey")) != shop_key or _drive.s(manifest.get("period")) != period:
        raise ValueError("Product history manifest scope mismatch")
    if qa.get("status") != "PASS" or not bool(qa.get("productHistorySemanticReady")) or not bool(qa.get("shopCommercialMetricReady")):
        raise ValueError("Product history Product/BI QA is not ready")
    fp = _drive.s(manifest.get("productHistorySemanticFingerprint"))
    if not fp or fp != _drive.s(qa.get("productHistorySemanticFingerprint")):
        raise ValueError("Product history fingerprint mismatch")
    listed = {str(x.get("file") or ""): x for x in manifest.get("files") or []}
    if set(listed) != {PRODUCT_MART, COMMERCIAL_MART}:
        raise ValueError("Product history extended manifest file contract mismatch")
    for name in (PRODUCT_MART, COMMERCIAL_MART):
        if _drive.sha256_file(root / name) != _drive.s(listed[name].get("sha256")):
            raise ValueError(f"Product history hash mismatch: {name}")
    safety = manifest.get("safety") or {}
    if any(bool(safety.get(k)) for k in (
        "fullShopProcessedPromotionPerformed", "canonicalPortfolioSemanticPublished",
        "productionDataMartWritten", "productionUiModified", "platformMutationAllowed",
    )):
        raise ValueError("Product history safety boundary violated")
    files = [{"path": p, "name": p.name, "size": p.stat().st_size} for p in sorted(root.iterdir()) if p.is_file()]
    return {
        "shopKey": shop_key,
        "shopId": _drive.s(manifest.get("shopId")),
        "period": period,
        "fingerprint": fp,
        "files": files,
        "manifest": manifest,
        "qa": qa,
    }


def publish_product_history_partition(drive, **kwargs):
    original = _drive.validate_local_partition
    _drive.validate_local_partition = _validate_extended_local_partition
    try:
        return _drive.publish_product_history_partition(drive, **kwargs)
    finally:
        _drive.validate_local_partition = original


def load_storage(path):
    return _drive.load_storage(path)
