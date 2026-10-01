"""Content-driven resolver for Shopee Business Insights workbooks.

Shopee BI exports have changed worksheet ordering over time and may prepend cover
or overview tabs. The trusted business normalizers in ``multi_shop_staging`` are
kept unchanged; this module only resolves worksheet roles by content and then
feeds a logical workbook in the legacy order those normalizers expect.

This deliberately separates layout discovery from business metric semantics.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .multi_shop_staging import (
    BI_DAILY_HEADERS,
    _aliases_present,
    _hdr,
    _traffic_sections,
    audit_bi_workbook_schema as _legacy_audit_bi_workbook_schema,
    normalize_bi_shop_daily as _legacy_normalize_bi_shop_daily,
    normalize_bi_traffic as _legacy_normalize_bi_traffic,
)


def _daily_header_index(rows: Sequence[Sequence[Any]]) -> int | None:
    required=(BI_DAILY_HEADERS["date"],BI_DAILY_HEADERS["sales"],BI_DAILY_HEADERS["orders"])
    matches=[]
    for idx,row in enumerate(rows):
        vals=[_hdr(x) for x in row]
        if all(_aliases_present(vals,aliases) for aliases in required):
            matches.append(idx)
    return matches[-1] if matches else None


def _traffic_profile(rows: Sequence[Sequence[Any]]) -> Dict[str,Any]:
    # Reuse the already-tested traffic parser instead of creating a second
    # interpretation of Shopee traffic semantics. A daily sheet can also emit
    # summary-shaped source labels, so dated facts take precedence.
    daily=_traffic_sections(
        rows,shop_id="__layout_probe__",stage="placed",daily=True,data_month="2000-01"
    )
    summary=_traffic_sections(
        rows,shop_id="__layout_probe__",stage="placed",daily=False,data_month="2000-01"
    )
    if daily:
        kind="daily"
    elif summary:
        kind="summary"
    else:
        kind="other"
    return {"kind":kind,"dailyFactCount":len(daily),"summaryFactCount":len(summary)}


def resolve_bi_workbook_layout(sheets: Sequence[Sequence[Sequence[Any]]]) -> Dict[str,Any]:
    shop_daily=[]; traffic_summary=[]; traffic_daily=[]; diagnostics=[]
    for idx,rows in enumerate(sheets):
        header_idx=_daily_header_index(rows)
        traffic=_traffic_profile(rows)
        roles=[]
        if header_idx is not None:
            shop_daily.append((idx,rows)); roles.append("shop_daily")
        if traffic["kind"]=="summary":
            traffic_summary.append((idx,rows)); roles.append("traffic_summary")
        elif traffic["kind"]=="daily":
            traffic_daily.append((idx,rows)); roles.append("traffic_daily")
        diagnostics.append({
            "sheetIndex":idx,
            "roles":roles or ["ignored"],
            "dailyHeaderIndex":header_idx,
            "trafficKind":traffic["kind"],
            "trafficDailyFactCount":traffic["dailyFactCount"],
            "trafficSummaryFactCount":traffic["summaryFactCount"],
        })

    counts={
        "shopDaily":len(shop_daily),
        "trafficSummary":len(traffic_summary),
        "trafficDaily":len(traffic_daily),
    }
    bad={key:value for key,value in counts.items() if value!=3}
    if bad:
        raise ValueError(
            f"BI layout resolution failed; expected exactly 3 sheets per required role; "
            f"counts={counts}; diagnostics={diagnostics}"
        )

    # Stage semantics remain workbook-order semantics *within each role*:
    # placed -> confirmed -> paid. Absolute worksheet indices are not trusted.
    daily_rows=[x[1] for x in shop_daily]
    summary_rows=[x[1] for x in traffic_summary]
    traffic_daily_rows=[x[1] for x in traffic_daily]
    logical=[
        daily_rows[0],daily_rows[1],daily_rows[2],
        summary_rows[0],traffic_daily_rows[0],[],
        summary_rows[1],traffic_daily_rows[1],[],
        summary_rows[2],traffic_daily_rows[2],
    ]
    return {
        "logicalSheets":logical,
        "sourceIndices":{
            "shopDaily":[x[0] for x in shop_daily],
            "trafficSummary":[x[0] for x in traffic_summary],
            "trafficDaily":[x[0] for x in traffic_daily],
        },
        "diagnostics":diagnostics,
    }


def audit_bi_workbook_schema(sheets, *, source_name:str=""):
    resolved=resolve_bi_workbook_layout(sheets)
    return _legacy_audit_bi_workbook_schema(resolved["logicalSheets"],source_name=source_name)


def normalize_bi_shop_daily(sheets, *, shop_id:str):
    resolved=resolve_bi_workbook_layout(sheets)
    return _legacy_normalize_bi_shop_daily(resolved["logicalSheets"],shop_id=shop_id)


def normalize_bi_traffic(sheets, *, shop_id:str, data_month:str):
    resolved=resolve_bi_workbook_layout(sheets)
    return _legacy_normalize_bi_traffic(
        resolved["logicalSheets"],shop_id=shop_id,data_month=data_month
    )


def load_bi_resolved(drive,root_id,month,shop_id, *, legacy_runner):
    """Drop-in replacement for runner.load_bi with layout lineage metadata."""
    mid=legacy_runner.domain_month(drive,root_id,"business_insights",month)
    f=legacy_runner.one_file(
        drive,legacy_runner.child_folder(drive,mid,"final"),".xlsx"
    )
    sheets=legacy_runner.xlsx_sheets(legacy_runner.download_bytes(drive,f["id"]))
    resolved=resolve_bi_workbook_layout(sheets)
    logical=resolved["logicalSheets"]
    schema_audits=_legacy_audit_bi_workbook_schema(logical,source_name=f["name"])
    shop_rows=_legacy_normalize_bi_shop_daily(logical,shop_id=shop_id)
    td,tm=_legacy_normalize_bi_traffic(logical,shop_id=shop_id,data_month=month)
    return shop_rows,td,tm,{
        "id":f["id"],"name":f["name"],"sheetCount":len(sheets),
        "modifiedTime":f.get("modifiedTime"),"schema_audits":schema_audits,
        "layoutResolution":{
            "mode":"CONTENT_DRIVEN_ROLE_RESOLUTION_V1",
            "sourceIndices":resolved["sourceIndices"],
            "diagnostics":resolved["diagnostics"],
        },
    }
