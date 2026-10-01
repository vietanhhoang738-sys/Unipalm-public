#!/usr/bin/env python3
"""Build and persist one Product-history semantic partition from staging facts."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

from googleapiclient.discovery import build

from modules.drive_auth import resolve_drive_credentials
from modules.product_history_commercial_extension import (
    build_product_history_partition,
    load_storage,
    publish_product_history_partition,
)
from modules.shop_registry import load_shop_registry, select_shops


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--shop-key", required=True)
    ap.add_argument("--registry", default="config/shop_registry.json")
    ap.add_argument("--staging-dir", default="staging_artifacts")
    ap.add_argument("--output-dir", default="product_history_artifacts")
    ap.add_argument("--contract", default="config/product_history_backfill_contract.json")
    ap.add_argument("--storage-registry", default="config/storage_registry.json")
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        raise ValueError("--month must be YYYY-MM")
    registry = load_shop_registry(args.registry)
    selected = select_shops(registry, [args.shop_key])
    if len(selected) != 1:
        raise ValueError("Product history backfill requires exactly one shop")
    shop = selected[0]
    shop_key = str(shop["shop_key"])
    staging = Path(args.staging_dir) / shop_key / args.month
    local = Path(args.output_dir) / shop_key / args.month
    built = build_product_history_partition(
        staging_dir=staging,
        output_dir=local,
        shop=shop,
        period=args.month,
        contract_path=args.contract,
        generated_at=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    )

    storage = load_storage(args.storage_registry)
    creds, auth_mode = resolve_drive_credentials(auth_mode="user_oauth")
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    published = publish_product_history_partition(
        drive,
        storage=storage,
        partition_dir=local,
        shop_key=shop_key,
        period=args.month,
        run_id=args.run_id,
    )
    summary = {
        "status": "PASS",
        "mode": "PRODUCT_HISTORY_BACKFILL",
        "authMode": auth_mode,
        "shopKey": shop_key,
        "shopId": shop["shop_id"],
        "period": args.month,
        "domainBuild": built,
        "drivePublish": published,
        "safety": {
            "fullShopProcessedPromotionPerformed": False,
            "canonicalPortfolioSemanticPublished": False,
            "productionDataMartWritten": False,
            "productionUiModified": False,
            "platformMutationAllowed": False,
        },
    }
    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / f"product_history_backfill_summary_{shop_key}_{args.month}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
