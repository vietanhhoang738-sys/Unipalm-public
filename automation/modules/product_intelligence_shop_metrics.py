"""Post-build Product Intelligence adapter for BI-authoritative shop metrics."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import product_intelligence as _base
from .product_shop_metrics import summarize


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def build_product_intelligence(*, shop_metric_rows: Sequence[Mapping[str, Any]], **kwargs):
    result = _base.build_product_intelligence(**kwargs)
    out = Path(kwargs["output_dir"])
    payload_path = out / "product_intelligence.json"
    qa_path = out / "product_intelligence_qa_report.json"
    manifest_path = out / "product_intelligence_manifest.json"
    payload = _read(payload_path); qa = _read(qa_path); manifest = _read(manifest_path)

    checks = list(qa.get("checks") or [])
    def ck(name, ok, detail=None):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})

    for sid, scope in (payload.get("shops") or {}).items():
        for key, horizon in (scope.get("horizons") or {}).items():
            if str(horizon.get("status") or "") != "READY":
                continue
            months = list(horizon.get("requiredMonths") or [])
            metrics = summarize(shop_metric_rows, shop_id=sid, months=months)
            ck(f"{sid}_{key}_bi_shop_metrics_ready", metrics.get("status") == "READY", metrics)
            if metrics.get("status") != "READY":
                continue
            sm = horizon.get("summary") or {}
            product_orders = int(round(float(sm.get("placedOrders") or 0)))
            product_confirmed_orders = int(round(float(sm.get("confirmedOrders") or 0)))
            sm.update({
                "productOrderOccurrences": product_orders,
                "productConfirmedOrderOccurrences": product_confirmed_orders,
                "placedOrders": metrics["placedOrders"],
                "placedAov": metrics["placedAov"],
                "confirmedOrders": metrics["confirmedOrders"],
                "confirmedAov": metrics["confirmedAov"],
                "shopPlacedGmv": metrics["placedGmv"],
                "shopConfirmedGmv": metrics["confirmedGmv"],
                "shopMetricSource": metrics["source"],
                "shopMetricSourceLayers": metrics.get("sourceLayers") or [],
                "orderSemantics": metrics["orderSemantics"],
                "productOrderOccurrenceInflation": (product_orders / metrics["placedOrders"]) if metrics["placedOrders"] else None,
            })
            horizon["summary"] = sm
            ck(
                f"{sid}_{key}_aov_uses_bi_unique_shop_orders",
                abs(float(sm["placedAov"]) - (float(sm["shopPlacedGmv"]) / float(sm["placedOrders"]) if sm["placedOrders"] else 0.0)) <= 1e-9,
                {"placedOrders": sm["placedOrders"], "productOrderOccurrences": product_orders, "source": sm["shopMetricSource"]},
            )

    failed = [x for x in checks if x.get("status") == "FAIL"]
    if failed:
        raise ValueError(f"Product BI shop-metric binding failed: {[x['name'] for x in failed]}")
    payload.setdefault("meta", {})["shopMetricPolicy"] = "BUSINESS_INSIGHTS_SHOP_LEVEL_UNIQUE_ORDERS"
    payload.setdefault("capabilities", {})["productShopLevelAovFromBI"] = True
    old_fp = str((payload.get("meta") or {}).get("productIntelligenceFingerprint") or "")
    payload["meta"].pop("productIntelligenceFingerprint", None)
    new_fp = _base._sha({
        "baseProductIntelligenceFingerprint": old_fp,
        "shopMetricPolicy": payload["meta"]["shopMetricPolicy"],
        "payload": payload,
    })
    payload["meta"]["productIntelligenceFingerprint"] = new_fp
    qa.update({
        "status": "PASS",
        "failedCheckCount": 0,
        "checks": checks,
        "productIntelligenceFingerprint": new_fp,
        "shopMetricPolicy": payload["meta"]["shopMetricPolicy"],
    })
    manifest["productIntelligenceFingerprint"] = new_fp
    manifest["shopMetricPolicy"] = payload["meta"]["shopMetricPolicy"]
    _write(payload_path, payload); _write(qa_path, qa); _write(manifest_path, manifest)
    return {
        **result,
        "status": "PASS",
        "productIntelligenceFingerprint": new_fp,
        "shopMetricPolicy": payload["meta"]["shopMetricPolicy"],
    }
