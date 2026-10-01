#!/usr/bin/env python3
"""Build Product Intelligence from canonical + Product-history semantics."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from googleapiclient.discovery import build

from modules.drive_auth import resolve_drive_credentials
from modules.product_intelligence_shop_metrics import build_product_intelligence
from modules.product_shop_metrics import monthly_from_semantic_shop_daily
from modules.shop_registry import enabled_shops, load_shop_registry
from multi_shop_staging_runner import children, download_bytes

FOLDER_MIME = "application/vnd.google-apps.folder"
HISTORY_LAYER = "product_history_semantic_v1"


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def child_file(items: Sequence[Mapping[str, Any]], name: str) -> Mapping[str, Any] | None:
    matches = [x for x in items if x.get("mimeType") != FOLDER_MIME and s(x.get("name")) == name]
    if len(matches) > 1:
        raise ValueError(f"duplicate file {name!r}")
    return matches[0] if matches else None


def child_folder(items: Sequence[Mapping[str, Any]], name: str) -> Mapping[str, Any] | None:
    matches = [x for x in items if x.get("mimeType") == FOLDER_MIME and s(x.get("name")) == name]
    if len(matches) > 1:
        raise ValueError(f"duplicate folder {name!r}")
    return matches[0] if matches else None


def json_file(drive, item: Mapping[str, Any]) -> Dict[str, Any]:
    return json.loads(download_bytes(drive, s(item.get("id"))).decode("utf-8"))


def jsonl_file(drive, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
    raw = download_bytes(drive, s(item.get("id"))).decode("utf-8")
    out = []
    for line_no, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{item.get('name')} line {line_no} is not an object")
        out.append(row)
    return out


def scan_trusted_canonical_product_history(drive, *, semantic_root_id: str, expected_shop_ids: List[str], as_of_period: str):
    trusted = []; product_rows: List[Dict[str, Any]] = []; shop_metrics: List[Dict[str, Any]] = []; partitions = []
    expected = set(expected_shop_ids)
    for item in children(drive, semantic_root_id):
        month = s(item.get("name"))
        if item.get("mimeType") != FOLDER_MIME or not re.fullmatch(r"\d{4}-\d{2}", month) or month > as_of_period:
            continue
        files = children(drive, s(item.get("id")))
        manifest_item = child_file(files, "manifest.json")
        qa_item = child_file(files, "semantic_qa_report.json")
        product_item = child_file(files, "dm_product_monthly.jsonl")
        shop_item = child_file(files, "dm_shop_daily.jsonl")
        status = "NOT_TRUSTED"; fp = ""; selected: List[str] = []; reason = "MISSING_REQUIRED_ARTIFACT"; product_count = 0; shop_metric_count = 0
        if manifest_item and qa_item and product_item and shop_item:
            manifest = json_file(drive, manifest_item); qa = json_file(drive, qa_item)
            fp = s(manifest.get("semantic_build_fingerprint")); selected = [s(x) for x in qa.get("selected_shop_ids") or []]
            trusted_ok = qa.get("status") == "PASS" and bool(qa.get("semantic_mart_ready")) and bool(fp) and fp == s(qa.get("semantic_build_fingerprint")) and set(selected) == expected
            if trusted_ok:
                month_products = jsonl_file(drive, product_item)
                foreign = sorted({s(r.get("shop_id")) for r in month_products if s(r.get("shop_id")) not in expected})
                wrong = sorted({s(r.get("data_month")) for r in month_products if s(r.get("data_month")) != month})
                if foreign:
                    reason = f"FOREIGN_SHOP_IDS:{foreign}"
                elif wrong:
                    reason = f"WRONG_DATA_MONTH:{wrong}"
                else:
                    month_shop_daily = jsonl_file(drive, shop_item)
                    month_metrics = monthly_from_semantic_shop_daily(month_shop_daily, month=month, expected_shop_ids=expected_shop_ids)
                    if {s(r.get('shop_id')) for r in month_metrics} != expected:
                        reason = "SHOP_METRIC_SCOPE_INCOMPLETE"
                    else:
                        product_rows.extend(month_products); shop_metrics.extend(month_metrics)
                        product_count = len(month_products); shop_metric_count = len(month_metrics)
                        trusted.append((month, fp)); status = "TRUSTED"; reason = "SEMANTIC_QA_PASS_WITH_BI_SHOP_METRICS"
            else:
                reason = "SEMANTIC_QA_OR_SCOPE_NOT_TRUSTED"
        partitions.append({
            "month": month, "status": status, "semanticFingerprint": fp, "selectedShopIds": selected,
            "productRowCount": product_count, "shopMetricRowCount": shop_metric_count, "reason": reason,
        })
    trusted.sort()
    return {
        "partitions": sorted(partitions, key=lambda x: x["month"]),
        "trustedMonths": [x[0] for x in trusted],
        "trustedFingerprints": [x[1] for x in trusted],
        "trustedMonthCount": len(trusted),
        "policy": "PUBLISHED_SEMANTIC_QA_PASS_ALL_ENABLED_SHOPS_WITH_BI_SHOP_METRICS",
    }, product_rows, shop_metrics


def scan_product_history_backfill(drive, *, semantic_root_id: str, namespace_root_name: str, shops: Sequence[Mapping[str, Any]], canonical_rows: Sequence[Mapping[str, Any]], as_of_period: str):
    canonical_by_shop = {
        s(shop.get("shop_id")): {s(r.get("data_month")) for r in canonical_rows if s(r.get("shop_id")) == s(shop.get("shop_id"))}
        for shop in shops
    }
    root = child_folder(children(drive, semantic_root_id), namespace_root_name)
    root_items = children(drive, s(root.get("id"))) if root else []
    all_products: List[Dict[str, Any]] = []; all_metrics: List[Dict[str, Any]] = []; inventory: Dict[str, Any] = {}; lineage_shops: Dict[str, Any] = {}
    for shop in shops:
        sid = s(shop.get("shop_id")); sk = s(shop.get("shop_key")); canonical_months = sorted(canonical_by_shop[sid])
        shop_folder = child_folder(root_items, sk); records = []; backfill_products: List[Dict[str, Any]] = []; backfill_metrics: List[Dict[str, Any]] = []
        if shop_folder:
            for month_folder in children(drive, s(shop_folder.get("id"))):
                month = s(month_folder.get("name"))
                if month_folder.get("mimeType") != FOLDER_MIME or not re.fullmatch(r"\d{4}-\d{2}", month) or month > as_of_period or month in canonical_by_shop[sid]:
                    continue
                items = children(drive, s(month_folder.get("id")))
                manifest_item = child_file(items, "manifest.json"); qa_item = child_file(items, "product_history_qa_report.json")
                product_item = child_file(items, "dm_product_monthly.jsonl"); metric_item = child_file(items, "dm_shop_commercial_monthly.jsonl")
                rec = {"month": month, "status": "NOT_TRUSTED", "reason": "MISSING_REQUIRED_ARTIFACT"}
                if manifest_item and qa_item and product_item and metric_item:
                    manifest = json_file(drive, manifest_item); qa = json_file(drive, qa_item); fp = s(manifest.get("productHistorySemanticFingerprint"))
                    trusted = (
                        s(manifest.get("layer")) == HISTORY_LAYER and s(manifest.get("shopId")) == sid and s(manifest.get("period")) == month
                        and qa.get("status") == "PASS" and bool(qa.get("productHistorySemanticReady")) and bool(qa.get("shopCommercialMetricReady"))
                        and bool(fp) and fp == s(qa.get("productHistorySemanticFingerprint"))
                    )
                    if trusted:
                        month_products = jsonl_file(drive, product_item); month_metrics = jsonl_file(drive, metric_item)
                        foreign = sorted({s(r.get("shop_id")) for r in month_products + month_metrics if s(r.get("shop_id")) != sid})
                        wrong = sorted({s(r.get("data_month")) for r in month_products + month_metrics if s(r.get("data_month")) != month})
                        if not foreign and not wrong and len(month_metrics) == 1:
                            backfill_products.extend(month_products); backfill_metrics.extend(month_metrics)
                            rec.update({"status": "TRUSTED_BACKFILL", "reason": "PRODUCT_AND_BI_HISTORY_QA_PASS", "productHistorySemanticFingerprint": fp, "productRowCount": len(month_products), "shopMetricRowCount": 1, "sourceFullShopStagingStatus": s(qa.get("sourceFullShopStagingStatus"))})
                        else:
                            rec["reason"] = f"SCOPE_MISMATCH:foreign={foreign}:months={wrong}:metricRows={len(month_metrics)}"
                    else:
                        rec["reason"] = "HISTORY_QA_OR_BI_LINEAGE_NOT_TRUSTED"
                records.append(rec)
        all_products.extend(backfill_products); all_metrics.extend(backfill_metrics)
        backfill_months = sorted({s(r.get("data_month")) for r in backfill_products})
        month_sources = [{"month": m, "source": "CANONICAL_SEMANTIC_V2"} for m in canonical_months]
        month_sources += [{"month": r["month"], "source": "PRODUCT_HISTORY_SEMANTIC_V1", "fingerprint": r.get("productHistorySemanticFingerprint", "")} for r in records if r.get("status") == "TRUSTED_BACKFILL"]
        month_sources.sort(key=lambda x: x["month"])
        inventory[sid] = {"shopKey": sk, "canonicalSemanticMonths": canonical_months, "historyPartitions": sorted(records, key=lambda x: x["month"]), "trustedBackfillMonths": backfill_months}
        lineage_shops[sid] = {"canonicalSemanticMonths": canonical_months, "semanticBackfillMonths": backfill_months, "monthSources": month_sources, "sourcePrecedence": "CANONICAL_SEMANTIC_V2_OVER_PRODUCT_HISTORY_SEMANTIC_V1"}
    return {"policy": "CANONICAL_SEMANTIC_FIRST__PRODUCT_AND_BI_HISTORY_QA_PASS_FOR_MISSING_SHOP_MONTHS", "shops": lineage_shops}, inventory, all_products, all_metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True); ap.add_argument("--registry", default="config/shop_registry.json")
    ap.add_argument("--storage-registry", default="config/storage_registry.json"); ap.add_argument("--contract", default="config/product_intelligence_contract.json")
    ap.add_argument("--output-dir", default="product_intelligence_artifacts")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.month): raise ValueError("--month must be YYYY-MM")
    registry = load_shop_registry(args.registry); shops = enabled_shops(registry); expected = [s(x.get("shop_id")) for x in shops]; storage = read_json(args.storage_registry)
    semantic_root_id = s((storage.get("semantic_v2") or {}).get("drive_root_id")); history_cfg = storage.get("product_history_semantic_v1") or {}; namespace_root_name = s(history_cfg.get("namespace_root_name"))
    if not semantic_root_id or not namespace_root_name: raise ValueError("semantic_v2 root and Product history namespace are required")
    creds, auth_mode = resolve_drive_credentials(auth_mode="user_oauth"); drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    canonical_inventory, canonical_rows, canonical_metrics = scan_trusted_canonical_product_history(drive, semantic_root_id=semantic_root_id, expected_shop_ids=expected, as_of_period=args.month)
    history_lineage, backfill_inventory, backfill_rows, backfill_metrics = scan_product_history_backfill(
        drive, semantic_root_id=semantic_root_id, namespace_root_name=namespace_root_name, shops=shops, canonical_rows=canonical_rows, as_of_period=args.month,
    )
    rows = list(canonical_rows) + list(backfill_rows); shop_metrics = list(canonical_metrics) + list(backfill_metrics)
    out = Path(args.output_dir) / args.month; out.mkdir(parents=True, exist_ok=True)
    (out / "product_history_inventory.json").write_text(json.dumps({"authMode": auth_mode, "canonicalSemantic": canonical_inventory, "productHistorySemantic": backfill_inventory, "historyLineage": history_lineage, "shopMetricRowCount": len(shop_metrics)}, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    result = build_product_intelligence(
        product_rows=rows, shop_metric_rows=shop_metrics, shops=shops, trusted_months=canonical_inventory["trustedMonths"], trusted_fingerprints=canonical_inventory["trustedFingerprints"],
        as_of_period=args.month, contract_path=args.contract, output_dir=out, history_lineage=history_lineage,
    )
    summary = {**result, "trustedCanonicalProductMonths": canonical_inventory["trustedMonths"], "trustedBackfillMonths": {sid: x["trustedBackfillMonths"] for sid, x in backfill_inventory.items()}, "shopMetricRowCount": len(shop_metrics), "outputLocation": str(out)}
    root = Path(args.output_dir); (root / f"multi_shop_product_intelligence_summary_{args.month}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
