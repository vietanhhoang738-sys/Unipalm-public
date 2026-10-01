#!/usr/bin/env python3
"""Compatibility entrypoint for Multi-Shop RAW -> staging.

The validated staging implementation is preserved in
``multi_shop_staging_runner_legacy``. This wrapper overrides only Business
Insights workbook layout discovery so Shopee may reorder or prepend worksheets
without changing business normalization semantics.
"""
from __future__ import annotations

from multi_shop_staging_runner_legacy import *  # noqa: F401,F403
import multi_shop_staging_runner_legacy as _legacy

from modules.bi_workbook_layout import load_bi_resolved


def load_bi(drive,root_id,month,shop_id):
    return load_bi_resolved(
        drive,root_id,month,shop_id,legacy_runner=_legacy
    )


def select_orders_source_folder(drive,mid,month):
    """Compatibility shim for tests/runtime overrides on this public entrypoint.

    Historical tests monkey-patch ``multi_shop_staging_runner.children``. Keep
    that contract intact even though the validated implementation now lives in
    the legacy core module.
    """
    original=_legacy.children
    _legacy.children=children
    try:
        return _legacy.select_orders_source_folder(drive,mid,month)
    finally:
        _legacy.children=original


# legacy.main resolves load_bi through its module globals, so patch exactly this
# dependency and leave every other staging function unchanged.
_legacy.load_bi=load_bi


if __name__=="__main__":
    raise SystemExit(_legacy.main())
