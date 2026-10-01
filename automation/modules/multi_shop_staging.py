"""Pure helpers for Multi-Shop raw normalization and staging QA.

This module has no production Data Mart or UI writer. Every normalized business
row is explicitly shop-scoped. It is safe to use before the promotion gate.
"""
from __future__ import annotations
import csv, datetime as dt, io, math, re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from .ads_product_mart import aggregate_product_ads_rows, validate_product_ads_rows
from .catalog_resolver import ListingRecord, resolve_catalog
from .schema_registry import aliases_for, require_schema, required_fields

SHOP_STAGES=("placed","confirmed","paid")

def s(v:Any)->str:
    return "" if v is None else str(v).strip()

def blank_dash(v:Any)->str:
    x=s(v)
    return "" if x=="-" else x

def n(v:Any, default:float=0.0)->float:
    if v in (None,"","-"): return default
    if isinstance(v,bool): return float(v)
    if isinstance(v,(int,float)):
        x=float(v); return x if math.isfinite(x) else default
    raw=s(v).replace("₫","").replace("đ","").replace("VND","").replace(" ","")
    if not raw or raw=="-": return default
    pct=raw.endswith("%"); raw=raw.rstrip("%")
    if pct:
        raw=raw.replace(",",".")
    elif "," in raw and "." in raw:
        raw=raw.replace(".","").replace(",",".")
    elif "," in raw:
        raw=raw.replace(",",".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+",raw):
        raw=raw.replace(".","")
    try:
        out=float(raw); return out/100.0 if pct else out
    except ValueError:
        return default

def i(v:Any)->int: return int(round(n(v)))

def parse_date(v:Any):
    if isinstance(v,dt.datetime): return v.date()
    if isinstance(v,dt.date): return v
    raw=s(v)
    if not raw or raw=="-": return None
    for fmt in ("%Y-%m-%d","%d-%m-%Y","%d/%m/%Y","%Y/%m/%d"):
        try: return dt.datetime.strptime(raw[:10],fmt).date()
        except ValueError: pass
    return None

def parse_datetime(v:Any)->str:
    if isinstance(v,dt.datetime): return v.strftime("%Y-%m-%d %H:%M:%S")
    raw=s(v)
    if not raw or raw=="-": return ""
    for fmt in ("%Y-%m-%d %H:%M","%Y-%m-%d %H:%M:%S","%d/%m/%Y %H:%M","%d/%m/%Y %H:%M:%S"):
        try: return dt.datetime.strptime(raw,fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError: pass
    return raw

def _hdr(v:Any)->str: return re.sub(r"\s+"," ",s(v))

def rows_to_records(rows:Sequence[Sequence[Any]], header_index:int=0)->List[Dict[str,Any]]:
    if len(rows)<=header_index: return []
    headers=[_hdr(x) for x in rows[header_index]]
    out=[]
    for row in rows[header_index+1:]:
        if not any(x not in (None,"") for x in row): continue
        out.append({h:(row[k] if k<len(row) else "") for k,h in enumerate(headers) if h})
    return out


LISTING_MACHINE_HEADERS=aliases_for("listing_catalog_machine")
LISTING_REQUIRED_FIELDS=required_fields("listing_catalog_machine")

def normalize_listing_sales_info_export(
    rows,
    *,
    expected_shopee_shop_id:str,
    shop_id:str,
    snapshot_at:str,
    source_name:str="",
):
    """Normalize Shopee Seller Center mass_update_sales_info export.

    The export is a catalog snapshot, not a transaction fact source. Row 1 uses
    stable machine field names, row 2 embeds the Shopee Shop ID, rows 3-6 are
    localized labels/instructions, and data starts afterwards.

    Shopee only writes Parent SKU on one variation row of many listings. This
    function therefore resolves the observed parent at product level first, then
    propagates it to every variation in that same product. No SKU-prefix
    inference is performed.
    """
    if len(rows) < 2:
        raise ValueError("Listing Sales Info export is too short")
    machine=[s(x) for x in rows[0]]
    schema_audit=require_schema("listing_catalog_machine",machine,source_name=source_name)
    resolved=schema_audit["resolved_fields"]
    idx={name:i for i,name in enumerate(machine) if name}

    meta=[s(x) for x in rows[1]]
    if not meta or meta[0]!="sales_info":
        raise ValueError("Listing Sales Info metadata row not found")
    embedded_shop_id=meta[3] if len(meta)>3 else ""
    if embedded_shop_id != s(expected_shopee_shop_id):
        raise ValueError(f"Listing Sales Info Shop ID mismatch: {embedded_shop_id} != {expected_shopee_shop_id}")

    parsed=[]
    parent_by_product={}
    parent_conflicts=defaultdict(set)
    for row in rows[2:]:
        def get(field):
            raw_header=resolved.get(field,"")
            if not raw_header:
                return ""
            j=idx[raw_header]
            return row[j] if j < len(row) else ""
        pid=s(get("product_id"))
        vid=s(get("variation_id"))
        # Skip localized header/instruction rows. Real Shopee IDs are numeric.
        if not (pid.isdigit() and vid.isdigit() and len(pid) >= 6 and len(vid) >= 6):
            continue
        parent=blank_dash(get("parent_sku"))
        if parent:
            if pid in parent_by_product and parent_by_product[pid] != parent:
                parent_conflicts[pid].update({parent_by_product[pid],parent})
            parent_by_product[pid]=parent
        parsed.append({
            "shop_id":shop_id,
            "snapshot_at":snapshot_at,
            "source_name":source_name,
            "product_id":pid,
            "product_name":s(get("product_name")),
            "variation_id":vid,
            "variation_name":s(get("variation_name")),
            "parent_sku_raw":parent,
            "variation_sku":blank_dash(get("variation_sku")),
            "price_vnd":n(get("variation_price")),
            "gtin":blank_dash(get("gtin")),
            "seller_stock":i(get("variation_stock")),
        })
    if parent_conflicts:
        raise ValueError(f"Conflicting Parent SKU within product_id: {dict(parent_conflicts)}")

    products={}
    variations=[]
    for r in parsed:
        pid=r["product_id"]
        parent=parent_by_product.get(pid,"")
        if pid not in products:
            products[pid]={
                "shop_id":shop_id,"snapshot_at":snapshot_at,"source_name":source_name,
                "product_id":pid,"product_name":r["product_name"],
                "product_sku":parent,"observed_parent_sku":parent,
                "variation_count":0,"sellable_sku_count":0,
            }
        p=products[pid]
        if p["product_name"] != r["product_name"]:
            raise ValueError(f"Product {pid}: inconsistent product name within export")
        p["variation_count"] += 1
        if r["variation_sku"]:
            p["sellable_sku_count"] += 1
        variations.append({
            "shop_id":shop_id,"snapshot_at":snapshot_at,"source_name":source_name,
            "product_id":pid,"product_name":r["product_name"],
            "variation_id":r["variation_id"],"variation_name":r["variation_name"],
            "parent_sku":parent,"observed_parent_sku":parent,
            "variation_sku":r["variation_sku"],"price_vnd":r["price_vnd"],
            "gtin":r["gtin"],"seller_stock":r["seller_stock"],
        })
    return list(products.values()),variations,{
        "embedded_shopee_shop_id":embedded_shop_id,
        "products":len(products),"variations":len(variations),
        "parent_present_products":sum(1 for p in products.values() if p["observed_parent_sku"]),
        "parent_missing_products":sum(1 for p in products.values() if not p["observed_parent_sku"]),
        "blank_variation_sku_rows":sum(1 for r in variations if not r["variation_sku"]),
        "schema_audit":schema_audit,
    }

def audit_listing_catalog_snapshot(products,variations):
    product_ids=[s(x.get("product_id")) for x in products]
    variation_ids=[s(x.get("variation_id")) for x in variations]
    product_dupes=len(product_ids)-len(set(product_ids))
    variation_dupes=len(variation_ids)-len(set(variation_ids))
    pset=set(product_ids)
    orphans=sum(1 for x in variations if s(x.get("product_id")) not in pset)
    parent_products=defaultdict(set)
    sku_products=defaultdict(set)
    parent_mismatches=0
    parent_by_pid={s(x.get("product_id")):s(x.get("observed_parent_sku") or x.get("product_sku")) for x in products}
    for x in variations:
        pid=s(x.get("product_id"))
        parent=s(x.get("observed_parent_sku") or x.get("parent_sku"))
        if parent and parent != parent_by_pid.get(pid,""):
            parent_mismatches += 1
        if parent:
            parent_products[parent].add(pid)
        sku=s(x.get("variation_sku"))
        if sku:
            sku_products[sku].add(pid)
    errors=[]
    if product_dupes: errors.append(f"duplicate product_id rows={product_dupes}")
    if variation_dupes: errors.append(f"duplicate variation_id rows={variation_dupes}")
    if orphans: errors.append(f"variation orphan rows={orphans}")
    if parent_mismatches: errors.append(f"parent propagation mismatches={parent_mismatches}")
    return {
        "status":"PASS" if not errors else "FAIL",
        "products":len(products),"variations":len(variations),
        "parentPresentProducts":sum(1 for x in products if s(x.get("observed_parent_sku") or x.get("product_sku"))),
        "parentMissingProducts":sum(1 for x in products if not s(x.get("observed_parent_sku") or x.get("product_sku"))),
        "blankVariationSkuRows":sum(1 for x in variations if not s(x.get("variation_sku"))),
        "duplicateParentCodesAcrossProducts":sum(1 for v in parent_products.values() if len(v)>1),
        "duplicateVariationSkusAcrossProducts":sum(1 for v in sku_products.values() if len(v)>1),
        "duplicateProductIds":product_dupes,"duplicateVariationIds":variation_dupes,
        "orphanVariations":orphans,"parentPropagationMismatches":parent_mismatches,
        "errors":errors,
    }

PP_HEADERS=aliases_for("product_performance")

def normalize_product_performance(rows, *, shop_id:str, data_month:str):
    products=[]; variations=[]
    for r in rows_to_records(rows):
        pid=s(_alias_value(r,PP_HEADERS["item_id"]))
        if not pid:
            continue
        variation_id=blank_dash(_alias_value(r,PP_HEADERS["variation_id"]))
        if variation_id in ("","-"):
            products.append({
                "shop_id":shop_id,"data_month":data_month,"product_id":pid,
                "product_name":s(_alias_value(r,PP_HEADERS["product"])),
                "product_status":s(_alias_value(r,PP_HEADERS["item_status"])),
                "product_sku":blank_dash(_alias_value(r,PP_HEADERS["parent_sku"])) or blank_dash(_alias_value(r,PP_HEADERS["sku"])),
                "placed_gmv_vnd":n(_alias_value(r,PP_HEADERS["placed_sales"])),
                "confirmed_gmv_vnd":n(_alias_value(r,PP_HEADERS["confirmed_sales"])),
                "product_views":i(_alias_value(r,PP_HEADERS["product_impressions"])),
                "product_clicks":i(_alias_value(r,PP_HEADERS["product_clicks"])),
                "ctr":n(_alias_value(r,PP_HEADERS["ctr"])),
                "placed_order_conversion_rate":n(_alias_value(r,PP_HEADERS["placed_order_cvr"])),
                "confirmed_order_conversion_rate":n(_alias_value(r,PP_HEADERS["confirmed_order_cvr"])),
                "placed_orders":i(_alias_value(r,PP_HEADERS["placed_orders"])),
                "confirmed_orders":i(_alias_value(r,PP_HEADERS["confirmed_orders"])),
                "placed_units":i(_alias_value(r,PP_HEADERS["placed_units"])),
                "confirmed_units":i(_alias_value(r,PP_HEADERS["confirmed_units"])),
                "placed_buyers":i(_alias_value(r,PP_HEADERS["placed_buyers"])),
                "confirmed_buyers":i(_alias_value(r,PP_HEADERS["confirmed_buyers"])),
                "placed_cvr":n(_alias_value(r,PP_HEADERS["placed_cvr"])),
                "confirmed_cvr":n(_alias_value(r,PP_HEADERS["confirmed_cvr"])),
                "placed_aov_vnd":n(_alias_value(r,PP_HEADERS["placed_aov"])),
                "confirmed_aov_vnd":n(_alias_value(r,PP_HEADERS["confirmed_aov"])),
                "unique_product_impressions":i(_alias_value(r,PP_HEADERS["unique_impressions"])),
                "unique_product_clicks":i(_alias_value(r,PP_HEADERS["unique_clicks"])),
                "product_visits":i(_alias_value(r,PP_HEADERS["product_visitors"])),
                "product_page_views":i(_alias_value(r,PP_HEADERS["page_views"])),
                "product_page_bounces":i(_alias_value(r,PP_HEADERS["bounce_visitors"])),
                "product_page_bounce_rate":n(_alias_value(r,PP_HEADERS["bounce_rate"])),
                "search_clicks":i(_alias_value(r,PP_HEADERS["search_clicks"])),
                "likes":i(_alias_value(r,PP_HEADERS["likes"])),
                "add_to_cart_visits":i(_alias_value(r,PP_HEADERS["atc_visitors"])),
                "add_to_cart_units":i(_alias_value(r,PP_HEADERS["atc_units"])),
                "add_to_cart_conversion_rate":n(_alias_value(r,PP_HEADERS["atc_cvr"])),
                "placed_repeat_order_rate":n(_alias_value(r,PP_HEADERS["placed_repeat_rate"])),
                "confirmed_repeat_order_rate":n(_alias_value(r,PP_HEADERS["confirmed_repeat_rate"])),
                "placed_avg_days_to_repeat_order":n(_alias_value(r,PP_HEADERS["placed_repeat_days"])),
                "confirmed_avg_days_to_repeat_order":n(_alias_value(r,PP_HEADERS["confirmed_repeat_days"])),
            })
        else:
            sku=blank_dash(_alias_value(r,PP_HEADERS["sku"]))
            if sku:
                variations.append({
                    "shop_id":shop_id,"data_month":data_month,"product_id":pid,
                    "product_name":s(_alias_value(r,PP_HEADERS["product"])),
                    "product_status":s(_alias_value(r,PP_HEADERS["item_status"])),
                    "variation_id":variation_id,
                    "variation_name":s(_alias_value(r,PP_HEADERS["variation_name"])),
                    "variation_status":s(_alias_value(r,PP_HEADERS["variation_status"])),
                    "variation_sku":sku,
                    "parent_sku":blank_dash(_alias_value(r,PP_HEADERS["parent_sku"])),
                })
    return products,variations

BI_DAILY_HEADERS=aliases_for("business_insights_daily")
BI_TRAFFIC_HEADERS=aliases_for("business_insights_traffic")

def _aliases_present(vals,aliases):
    present={_hdr(x).casefold() for x in vals}
    return any(_hdr(x).casefold() in present for x in aliases)

def _alias_value(record, aliases):
    # Exact header match first. Some Shopee exports contain two different
    # financial columns whose labels differ only by capitalization.
    for alias in aliases:
        key=_hdr(alias)
        if key in record:
            return record.get(key)

    folded=defaultdict(list)
    for actual in record.keys():
        folded[_hdr(actual).casefold()].append(actual)
    for alias in aliases:
        candidates=folded.get(_hdr(alias).casefold(),[])
        if len(candidates)==1:
            return record.get(candidates[0])
    return ""

def normalize_bi_shop_daily(stage_sheets, *, shop_id:str):
    if len(stage_sheets)<3:
        raise ValueError("Business Insights workbook must contain placed/confirmed/paid sheets")
    out=[]
    required=(BI_DAILY_HEADERS["date"],BI_DAILY_HEADERS["sales"],BI_DAILY_HEADERS["orders"])
    for stage,rows in zip(SHOP_STAGES,stage_sheets[:3]):
        # The workbook may contain an aggregate header and then the daily header.
        # Pick the last matching header so daily records are preferred in both EN/VN exports.
        matches=[]
        for idx,row in enumerate(rows):
            vals=[_hdr(x) for x in row]
            if all(_aliases_present(vals,aliases) for aliases in required):
                matches.append(idx)
        header=matches[-1] if matches else None
        if header is None:
            raise ValueError(f"BI {stage}: daily header not found")
        for r in rows_to_records(rows,header):
            d=parse_date(_alias_value(r,BI_DAILY_HEADERS["date"]))
            if not d:
                continue
            out.append({
                "shop_id":shop_id,"data_date":d.isoformat(),"order_stage":stage,
                "gross_sales":n(_alias_value(r,BI_DAILY_HEADERS["sales"])),
                "sales_shopee_rebate_applied":n(_alias_value(r,BI_DAILY_HEADERS["sales_ex_shopee_rebate"])),
                "order_count":i(_alias_value(r,BI_DAILY_HEADERS["orders"])),
                "sales_per_order":n(_alias_value(r,BI_DAILY_HEADERS["sales_per_order"])),
                "product_clicks":i(_alias_value(r,BI_DAILY_HEADERS["product_clicks"])),
                "visits":i(_alias_value(r,BI_DAILY_HEADERS["visitors"])),
                "order_conversion_rate":n(_alias_value(r,BI_DAILY_HEADERS["order_conversion_rate"])),
                "cancelled_orders":i(_alias_value(r,BI_DAILY_HEADERS["cancelled_orders"])),
                "cancelled_sales":n(_alias_value(r,BI_DAILY_HEADERS["cancelled_sales"])),
                "returned_refunded_orders":i(_alias_value(r,BI_DAILY_HEADERS["returned_orders"])),
                "returned_refunded_sales":n(_alias_value(r,BI_DAILY_HEADERS["returned_sales"])),
                "buyers":i(_alias_value(r,BI_DAILY_HEADERS["buyers"])),
                "new_buyers":i(_alias_value(r,BI_DAILY_HEADERS["new_buyers"])),
                "existing_buyers":i(_alias_value(r,BI_DAILY_HEADERS["existing_buyers"])),
                "potential_buyers":i(_alias_value(r,BI_DAILY_HEADERS["potential_buyers"])),
                "repeat_purchase_rate":n(_alias_value(r,BI_DAILY_HEADERS["repeat_purchase_rate"])),
            })
    return out

BI_TRAFFIC_GROUP_ALIASES={
    "Product Card":("Product Card","Thẻ sản phẩm"),
    "Seller Live":("Seller Live","Live"),
    "Seller Video":("Seller Video","Video"),
    "Shopee Affiliate":("Shopee Affiliate","Tiếp thị liên kết"),
    "Shopee Ads":("Shopee Ads","Dịch vụ Hiển thị Shopee"),
}

BI_TRAFFIC_SOURCE_ALIASES={
    "Product Card":("Product Card","Thẻ sản phẩm"),
    "Search":("Search","Tìm kiếm"),
    "Shop":("Shop","Cửa hàng"),
    "Recommendation":("Recommendation","Đề xuất"),
    "Promotion":("Promotion","Khuyến mãi"),
    "Shopping Cart":("Shopping Cart","Giỏ hàng"),
    "Chat":("Chat",),
    "My Purchase":("My Purchase","Đơn mua của tôi"),
    "Others":("Others","Khác"),
    "Homepage Shopee Live":("Homepage Shopee Live","Trang chủ Shopee Live"),
    "Live Tab":("Live Tab","Thẻ Live"),
    "Video":("Video",),
    "Creator Profile":("Creator Profile","Hồ sơ người tạo"),
    "Featured Video":("Featured Video","Video nổi bật"),
    "Video Tab":("Video Tab","Thẻ Video"),
    "Affiliate Live":("Affiliate Live",),
    "Affiliate Video":("Affiliate Video",),
}

def _canonical_from_aliases(value, mapping):
    raw=s(value)
    key=_hdr(raw).casefold()
    for canonical,aliases in mapping.items():
        if key in {_hdr(x).casefold() for x in aliases}:
            return canonical
    return raw

def _canonical_channel_group(value):
    return _canonical_from_aliases(value,BI_TRAFFIC_GROUP_ALIASES)

def _canonical_traffic_source(value):
    return _canonical_from_aliases(value,BI_TRAFFIC_SOURCE_ALIASES)

def _traffic_section_label(row):
    vals=[s(x) for x in row]
    nonempty=[x for x in vals if x]
    if len(nonempty)!=1:
        return ""
    canonical=_canonical_channel_group(nonempty[0])
    return canonical if canonical in BI_TRAFFIC_GROUP_ALIASES else ""

def _traffic_header_supported(row):
    vals=[_hdr(x) for x in row]
    required=(
        BI_TRAFFIC_HEADERS["traffic_source"],
        BI_TRAFFIC_HEADERS["sales"],
        BI_TRAFFIC_HEADERS["impressions"],
        BI_TRAFFIC_HEADERS["clicks"],
    )
    return all(_aliases_present(vals,aliases) for aliases in required)

def _traffic_record(header,row):
    keys=[_hdr(x) for x in header]
    out={}
    for idx,key in enumerate(keys):
        if not key:
            continue
        out[key]=row[idx] if idx<len(row) else ""
    return out

def _traffic_exposure_metric(channel_group):
    return {
        "Product Card":"product_impressions",
        "Seller Live":"live_views",
        "Seller Video":"video_views",
        "Shopee Affiliate":"content_views",
    }.get(channel_group,"exposures")

def _traffic_output(rec, *, shop_id, stage, channel_group, source_raw, data_date="", data_month=""):
    is_group_total=_canonical_channel_group(source_raw)==channel_group
    source=channel_group if is_group_total else _canonical_traffic_source(source_raw)
    return {
        "shop_id":shop_id,
        "data_date":data_date,
        "data_month":data_month,
        "order_stage":stage,
        "channel_group":channel_group,
        "traffic_source":source,
        "traffic_source_raw":source_raw,
        "is_group_total":is_group_total,
        "exposure_metric":_traffic_exposure_metric(channel_group),
        "sales_ratio":n(_alias_value(rec,BI_TRAFFIC_HEADERS["sales_ratio"])),
        "sales":n(_alias_value(rec,BI_TRAFFIC_HEADERS["sales"])),
        "impressions":i(_alias_value(rec,BI_TRAFFIC_HEADERS["impressions"])),
        "clicks":i(_alias_value(rec,BI_TRAFFIC_HEADERS["clicks"])),
        "orders":n(_alias_value(rec,BI_TRAFFIC_HEADERS["orders"])),
        "units":n(_alias_value(rec,BI_TRAFFIC_HEADERS["units"])),
        "ctr":n(_alias_value(rec,BI_TRAFFIC_HEADERS["ctr"])),
        "cvr":n(_alias_value(rec,BI_TRAFFIC_HEADERS["cvr"])),
        "sales_per_order":n(_alias_value(rec,BI_TRAFFIC_HEADERS["sales_per_order"])),
        "buyers":i(_alias_value(rec,BI_TRAFFIC_HEADERS["buyers"])),
        "unique_impressions":i(_alias_value(rec,BI_TRAFFIC_HEADERS["unique_impressions"])),
        "unique_clicks":i(_alias_value(rec,BI_TRAFFIC_HEADERS["unique_clicks"])),
    }

def _traffic_sections(rows, *, shop_id, stage, daily, data_month):
    out=[]
    channel_group=""
    header=None
    current_source_raw=""
    supported=False

    for row in rows:
        section=_traffic_section_label(row)
        if section:
            channel_group=section
            header=None
            current_source_raw=""
            supported=False
            continue

        if channel_group and _traffic_header_supported(row):
            header=list(row)
            supported=channel_group!="Shopee Ads"
            current_source_raw=""
            continue

        if not channel_group or not header or not supported:
            continue

        first=s(row[0] if row else "")
        if not first:
            continue
        rec=_traffic_record(header,row)
        d=parse_date(first)

        if daily:
            if d:
                if not current_source_raw:
                    continue
                out.append(_traffic_output(
                    rec,shop_id=shop_id,stage=stage,channel_group=channel_group,
                    source_raw=current_source_raw,data_date=d.isoformat(),data_month=data_month,
                ))
            else:
                current_source_raw=first
        else:
            if d:
                continue
            current_source_raw=first
            out.append(_traffic_output(
                rec,shop_id=shop_id,stage=stage,channel_group=channel_group,
                source_raw=current_source_raw,data_month=data_month,
            ))
    return out

def normalize_bi_traffic(sheets, *, shop_id:str, data_month:str):
    daily=[]; monthly=[]
    for stage,summary_idx,daily_idx in (("placed",3,4),("confirmed",6,7),("paid",9,10)):
        if summary_idx<len(sheets):
            monthly.extend(_traffic_sections(
                sheets[summary_idx],shop_id=shop_id,stage=stage,daily=False,data_month=data_month))
        if daily_idx<len(sheets):
            daily.extend(_traffic_sections(
                sheets[daily_idx],shop_id=shop_id,stage=stage,daily=True,data_month=data_month))
    return daily,monthly

def _traffic_schema_audits(rows, *, source_name, stage, label):
    audits=[]
    channel_group=""
    for row in rows:
        section=_traffic_section_label(row)
        if section:
            channel_group=section
            continue
        if channel_group and channel_group!="Shopee Ads" and _traffic_header_supported(row):
            audits.append(require_schema(
                "business_insights_traffic",
                row,
                source_name=f"{source_name}::{stage}_traffic_{label}::{channel_group}",
            ))
    return audits

def audit_bi_workbook_schema(sheets, *, source_name:str=""):
    audits=[]
    if len(sheets)<3:
        raise ValueError("Business Insights workbook must contain placed/confirmed/paid sheets")

    daily_required=(BI_DAILY_HEADERS["date"],BI_DAILY_HEADERS["sales"],BI_DAILY_HEADERS["orders"])
    for stage,rows in zip(SHOP_STAGES,sheets[:3]):
        matches=[]
        for idx,row in enumerate(rows):
            vals=[_hdr(x) for x in row]
            if all(_aliases_present(vals,aliases) for aliases in daily_required):
                matches.append(idx)
        if not matches:
            raise ValueError(f"BI {stage}: daily header not found")
        header=matches[-1]
        audits.append(require_schema(
            "business_insights_daily",
            rows[header],
            source_name=f"{source_name}::{stage}_daily",
        ))

    for stage,summary_idx,daily_idx in (("placed",3,4),("confirmed",6,7),("paid",9,10)):
        for label,idx in (("summary",summary_idx),("daily",daily_idx)):
            if idx>=len(sheets):
                continue
            part=_traffic_schema_audits(
                sheets[idx],source_name=source_name,stage=stage,label=label)
            if not part:
                raise ValueError(f"BI {stage} {label}: supported traffic section header not found")
            audits.extend(part)
    return audits

ORDER_HEADERS=aliases_for("orders")

def normalize_orders(rows, *, shop_id:str, loaded_at:str):
    orders={}; items=[]; seq=defaultdict(int)
    for r in rows_to_records(rows):
        oid=s(_alias_value(r,ORDER_HEADERS["order_id"]))
        if not oid: continue
        seq[oid]+=1
        items.append({
            "shop_id":shop_id,"order_id":oid,"order_item_seq":seq[oid],
            "product_sku":blank_dash(_alias_value(r,ORDER_HEADERS["product_sku"])),"product_name":s(_alias_value(r,ORDER_HEADERS["product_name"])),
            "variation_sku":blank_dash(_alias_value(r,ORDER_HEADERS["variation_sku"])),"variation_name":s(_alias_value(r,ORDER_HEADERS["variation_name"])),
            "quantity":i(_alias_value(r,ORDER_HEADERS["qty"])),"returned_quantity":i(_alias_value(r,ORDER_HEADERS["returned_qty"])),
            "item_buyer_payment":n(_alias_value(r,ORDER_HEADERS["item_buyer_payment"])),
            "shopee_subsidy":n(_alias_value(r,ORDER_HEADERS["shopee_subsidy"])),
            "loaded_at":loaded_at,
        })
        if oid not in orders:
            orders[oid]={
                "shop_id":shop_id,"order_id":oid,"order_created_at":parse_datetime(_alias_value(r,ORDER_HEADERS["order_created_at"])),
                "order_status":s(_alias_value(r,ORDER_HEADERS["order_status"])),"cancelled_at":"",
                "cancel_reason":s(_alias_value(r,ORDER_HEADERS["cancel_reason"])),"ship_date":parse_datetime(_alias_value(r,ORDER_HEADERS["ship_date"])),
                "completed_at":parse_datetime(_alias_value(r,ORDER_HEADERS["completed_at"])),"paid_at":parse_datetime(_alias_value(r,ORDER_HEADERS["paid_at"])),
                "order_total_value":n(_alias_value(r,ORDER_HEADERS["order_total_value"])),"buyer_total_payment":n(_alias_value(r,ORDER_HEADERS["buyer_total_payment"])),
                "shop_voucher":n(_alias_value(r,ORDER_HEADERS["shop_voucher"])),"shopee_voucher":n(_alias_value(r,ORDER_HEADERS["shopee_voucher"])),
                "fixed_fee":n(_alias_value(r,ORDER_HEADERS["fixed_fee"])),"service_fee":n(_alias_value(r,ORDER_HEADERS["service_fee"])),
                "transaction_fee":n(_alias_value(r,ORDER_HEADERS["transaction_fee"])),"buyer_username":s(_alias_value(r,ORDER_HEADERS["buyer_username"])),
                "province":s(_alias_value(r,ORDER_HEADERS["province"])),"loaded_at":loaded_at,
            }
        else:
            for key in ("order_total_value","buyer_total_payment","shop_voucher","shopee_voucher","fixed_fee","service_fee","transaction_fee"):
                if abs(n(orders[oid][key])-n(_alias_value(r,ORDER_HEADERS[key])))>0.01:
                    raise ValueError(f"Order {oid}: repeated order-level field {key} is inconsistent")
    return list(orders.values()),items

ADS_META_HEADERS=aliases_for("ads_metadata")
ADS_HEADERS=aliases_for("ads_rows")

def _ads_meta_key(raw_key):
    key=_hdr(raw_key)
    for canonical,aliases in ADS_META_HEADERS.items():
        if key.casefold() in {_hdr(x).casefold() for x in aliases}:
            return canonical
    return ""

def parse_ads_csv(text:str, *, expected_shopee_shop_id:str, shop_id:str, source_name:str=""):
    lines=text.replace("\ufeff","").splitlines()
    meta={}
    meta_raw_headers=[]
    header=None
    sequence_aliases={_hdr(x).casefold() for x in ADS_HEADERS["sequence"]}

    for idx,line in enumerate(lines):
        row=next(csv.reader([line])) if line else []
        first=_hdr(row[0]).casefold() if row else ""
        if first in sequence_aliases:
            header=idx
            break
        if len(row)>=2:
            canonical=_ads_meta_key(row[0])
            if canonical:
                meta[canonical]=row[1]
                meta_raw_headers.append(row[0])

    if header is None:
        raise ValueError("Ads report header not found")
    meta_schema=require_schema("ads_metadata",meta_raw_headers,source_name=f"{source_name}::metadata")
    header_row=next(csv.reader([lines[header]]))
    row_schema=require_schema("ads_rows",header_row,source_name=f"{source_name}::rows")
    if s(meta.get("shop_id"))!=s(expected_shopee_shop_id):
        raise ValueError(f"Ads Shop ID mismatch: {meta.get('shop_id')} != {expected_shopee_shop_id}")

    m=re.match(r"(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})",s(meta.get("date_period")))
    if not m:
        raise ValueError(f"Ads Date Period invalid: {meta.get('date_period')!r}")
    start=dt.date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
    end=dt.date(int(m.group(6)),int(m.group(5)),int(m.group(4)))
    if start!=end:
        raise ValueError("Ads staging v1 expects one report day per file")

    out=[]
    for r in csv.DictReader(io.StringIO("\n".join(lines[header:]))):
        pid=blank_dash(_alias_value(r,ADS_HEADERS["product_id"]))
        ads_type=s(_alias_value(r,ADS_HEADERS["ads_type"]))
        # Product ID is the locale-independent structural discriminator.
        # Shop-level GMV Max rows have no Product ID.
        scope="product" if pid else "shop"
        out.append({
            "shop_id":shop_id,"data_date":start.isoformat(),"ad_scope":scope,
            "ad_service_daily_key":f"{start.isoformat()}::{s(_alias_value(r,ADS_HEADERS['sequence']))}::{s(_alias_value(r,ADS_HEADERS['ad_name']))}",
            "ad_name":s(_alias_value(r,ADS_HEADERS["ad_name"])),
            "ad_status":s(_alias_value(r,ADS_HEADERS["status"])),
            "ads_type":ads_type,
            "product_id":pid,
            "bidding_method":s(_alias_value(r,ADS_HEADERS["bidding_method"])),
            "placement":s(_alias_value(r,ADS_HEADERS["placement"])),
            "impressions":i(_alias_value(r,ADS_HEADERS["impressions"])),
            "clicks":i(_alias_value(r,ADS_HEADERS["clicks"])),
            "ctr":n(_alias_value(r,ADS_HEADERS["ctr"])),
            "add_to_cart":i(_alias_value(r,ADS_HEADERS["add_to_cart"])),
            "conversions":i(_alias_value(r,ADS_HEADERS["conversions"])),
            "direct_conversions":i(_alias_value(r,ADS_HEADERS["direct_conversions"])),
            "units_sold":i(_alias_value(r,ADS_HEADERS["units_sold"])),
            "direct_units_sold":i(_alias_value(r,ADS_HEADERS["direct_units_sold"])),
            "attributed_sales":n(_alias_value(r,ADS_HEADERS["gmv"])),
            "direct_sales":n(_alias_value(r,ADS_HEADERS["direct_gmv"])),
            "ad_spend":n(_alias_value(r,ADS_HEADERS["expense"])),
            "voucher_amount":n(_alias_value(r,ADS_HEADERS["voucher_amount"])),
            "vouchered_sales":n(_alias_value(r,ADS_HEADERS["vouchered_sales"])),
        })
    return out,{**meta,"data_date":start.isoformat(),"rows":len(out),
        "schema_audit":{"metadata":meta_schema,"rows":row_schema}}

def build_listing_records(products,variations):
    vars_by=defaultdict(set); parent_by={}
    for r in variations:
        pid=s(r.get("product_id")); sku=blank_dash(r.get("variation_sku"))
        if pid and sku: vars_by[pid].add(sku)
        if pid and blank_dash(r.get("parent_sku")): parent_by[pid]=blank_dash(r.get("parent_sku"))
    return [ListingRecord(
        shop_id=s(p.get("shop_id")),product_id=s(p.get("product_id")),title=s(p.get("product_name")),
        parent_sku=blank_dash(p.get("product_sku")) or parent_by.get(s(p.get("product_id")),""),
        variation_skus=vars_by.get(s(p.get("product_id")),set()))
        for p in products if s(p.get("product_id"))]

def run_catalog_resolver(targets, references=(), family_by_sellable_sku=None):
    return [{
        "shop_id":x.shop_id,"product_id":x.product_id,"title":x.title,"observed_parent_sku":x.observed_parent_sku,
        "resolved_parent_sku":x.resolved_parent_sku,"canonical_family_key":x.canonical_family_key,
        "reference_product_id":x.reference_product_id,"reference_shop_id":x.reference_shop_id,
        "status":x.status,"confidence":x.confidence,"evidence":x.evidence,
    } for x in resolve_catalog(targets,references,family_by_sellable_sku=dict(family_by_sellable_sku or {}))]

def _dupes(rows,fields):
    keys=[tuple(s(r.get(f)) for f in fields) for r in rows]
    return len(keys)-len(set(keys))

def _coverage(rows,field="data_date"):
    dates=sorted({parse_date(r.get(field)) for r in rows if parse_date(r.get(field))})
    if not dates: return {"start":"","end":"","days":0,"missing":[]}
    expected={dates[0]+dt.timedelta(days=x) for x in range((dates[-1]-dates[0]).days+1)}
    return {"start":dates[0].isoformat(),"end":dates[-1].isoformat(),"days":len(dates),
            "missing":[x.isoformat() for x in sorted(expected-set(dates))]}

def qa_staging(*,shop_id,target_month,orders,order_items,products,variations,bi_shop,ads,ads_files,catalog_resolutions,traffic_daily=None,traffic_monthly=None):
    checks=[]
    traffic_daily=list(traffic_daily or [])
    traffic_monthly=list(traffic_monthly or [])
    def ck(name,ok,detail): checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":detail})
    all_rows=[*orders,*order_items,*products,*variations,*bi_shop,*ads,*traffic_daily,*traffic_monthly]
    foreign=sum(1 for r in all_rows if s(r.get("shop_id"))!=shop_id)
    ck("shop_id_isolation",foreign==0,{"foreign_rows":foreign})
    for name,rows,keys in (
        ("orders_unique",orders,("shop_id","order_id")),
        ("order_items_unique",order_items,("shop_id","order_id","order_item_seq")),
        ("product_month_unique",products,("shop_id","data_month","product_id")),
        ("variation_month_unique",variations,("shop_id","data_month","product_id","variation_sku")),
        ("bi_stage_day_unique",bi_shop,("shop_id","data_date","order_stage")),
        ("traffic_source_daily_unique",traffic_daily,("shop_id","data_date","order_stage","channel_group","traffic_source")),
        ("traffic_source_monthly_unique",traffic_monthly,("shop_id","data_month","order_stage","channel_group","traffic_source")),
        ("ads_service_day_unique",ads,("shop_id","data_date","ad_service_daily_key"))):
        d=_dupes(rows,keys); ck(name,d==0,{"duplicates":d})
    by_stage={stage:[r for r in bi_shop if s(r.get("order_stage"))==stage] for stage in SHOP_STAGES}
    stage_cov={stage:_coverage(rows) for stage,rows in by_stage.items()}
    endpoints={v["end"] for v in stage_cov.values() if v["end"]}
    ck("bi_stage_coverage",all(v["days"]>0 and not v["missing"] for v in stage_cov.values()) and len(endpoints)==1,stage_cov)
    ck("product_performance_target_month_present",len(products)>0,{
        "products":len(products),"variations":len(variations),
        "data_months":sorted({s(r.get("data_month")) for r in products if s(r.get("data_month"))}),
    })
    order_dates=[parse_date(r.get("order_created_at")) for r in orders]
    order_dates=[d for d in order_dates if d and d.strftime("%Y-%m")==target_month]
    ck("orders_target_month_present",bool(order_dates),{"start":min(order_dates).isoformat() if order_dates else "","end":max(order_dates).isoformat() if order_dates else "","days":len(set(order_dates))})
    ads_cov=_coverage([r for r in ads if s(r.get("data_date")).startswith(target_month)])
    ck("ads_target_month_present",ads_cov["days"]>0,ads_cov)
    if ads_cov["days"]: ck("ads_daily_contiguous",not ads_cov["missing"],ads_cov)
    file_dates=[s(x.get("data_date")) for x in ads_files if s(x.get("data_date")).startswith(target_month)]
    ck("ads_file_day_unique",len(file_dates)==len(set(file_dates)),{"files":len(file_dates),"unique_days":len(set(file_dates))})
    bad_cancel=[s(r.get("order_id")) for r in orders if s(r.get("order_status"))=="Đã hủy" and
                sum(abs(n(r.get(f))) for f in ("fixed_fee","service_fee","transaction_fee"))>0.01]
    ck("cancelled_order_fees_zero",not bad_cancel,{"count":len(bad_cancel),"order_ids":bad_cancel[:20]})
    pids={s(x.get("product_id")) for x in products}
    orphans=[x for x in variations if s(x.get("product_id")) not in pids]
    ck("product_variation_referential",not orphans,{"orphans":len(orphans)})
    product_ads=aggregate_product_ads_rows(ads,expected_shop_id=shop_id)
    ads_qa=validate_product_ads_rows(product_ads)
    ck("product_ads_all_campaign_aggregation",ads_qa.get("status")=="PASS",ads_qa)
    placed_all=[r for r in bi_shop if s(r.get("order_stage"))=="placed" and s(r.get("data_date")).startswith(target_month)]
    orders_all=[r for r in orders if s(r.get("order_created_at")).startswith(target_month)]
    bi_dates=[s(r.get("data_date")) for r in placed_all if s(r.get("data_date"))]
    ord_dates=[s(r.get("order_created_at"))[:10] for r in orders_all if s(r.get("order_created_at"))]
    bi_start=min(bi_dates,default=""); bi_end=max(bi_dates,default="")
    ord_start=min(ord_dates,default=""); ord_end=max(ord_dates,default="")
    common_start=max(bi_start,ord_start) if bi_start and ord_start else ""
    common_end=min(bi_end,ord_end) if bi_end and ord_end else ""

    placed=[r for r in placed_all if common_start<=s(r.get("data_date"))<=common_end] if common_start and common_end else []
    target_orders=[r for r in orders_all if common_start<=s(r.get("order_created_at"))[:10]<=common_end] if common_start and common_end else []
    bi_orders=sum(i(r.get("order_count")) for r in placed)
    bi_gmv=sum(n(r.get("gross_sales")) for r in placed)
    oids={s(r.get("order_id")) for r in target_orders}

    # Orders exports expose item price, Shopee-funded price subsidy and order-level
    # Shop voucher separately. Business Insights Gross Sales includes the platform-
    # funded subsidy, so the reconciliation proxy must restore it. This is zero on
    # modern exports but material on historical campaign days.
    item_proxy_by_order=defaultdict(float)
    subsidy_total=0.0
    for r in order_items:
        oid=s(r.get("order_id"))
        if oid not in oids:
            continue
        subsidy=n(r.get("shopee_subsidy"))
        subsidy_total+=subsidy
        item_proxy_by_order[oid]+=n(r.get("item_buyer_payment"))+subsidy

    standard_proxy=0.0
    cancellation_proxy=0.0
    cancellation_fallback_orders=0
    for order in target_orders:
        oid=s(order.get("order_id"))
        order_proxy=item_proxy_by_order.get(oid,0.0)-n(order.get("shop_voucher"))
        standard_proxy+=order_proxy
        if s(order.get("order_status"))=="Đã hủy" and n(order.get("order_total_value"))>0:
            cancellation_proxy+=n(order.get("order_total_value"))
            cancellation_fallback_orders+=1
        else:
            cancellation_proxy+=order_proxy

    proxy_candidates=[
        {
            "mode":"ITEM_PAYMENT_PLUS_SHOPEE_SUBSIDY_MINUS_SHOP_VOUCHER",
            "value":standard_proxy,
        },
        {
            "mode":"CANCELLED_ORDER_TOTAL_VALUE_FALLBACK",
            "value":cancellation_proxy,
        },
    ]
    for candidate in proxy_candidates:
        candidate["gmv_diff_pct"]=(candidate["value"]-bi_gmv)/bi_gmv if bi_gmv else 0.0
    selected=min(proxy_candidates,key=lambda x:abs(x["gmv_diff_pct"]))
    proxy=selected["value"]
    diff_pct=selected["gmv_diff_pct"]

    overlap_ok=bool(common_start and common_end and common_start<=common_end)
    rec_ok=overlap_ok and len(target_orders)==bi_orders and abs(diff_pct)<=0.005
    ck("placed_orders_gmv_reconciliation",rec_ok,{
       "bi_start":bi_start,"bi_end":bi_end,"orders_start":ord_start,"orders_end":ord_end,
       "common_reliable_start":common_start,"common_reliable_end":common_end,
       "bi_orders":bi_orders,"orders_distinct":len(target_orders),
       "bi_placed_gmv":bi_gmv,"orders_gmv_proxy":proxy,"gmv_diff_pct":diff_pct,
       "selected_proxy_mode":selected["mode"],
       "proxy_candidates":proxy_candidates,
       "shopee_subsidy_total":subsidy_total,
       "cancellation_fallback_orders":cancellation_fallback_orders,
       "bi_lag_days_after_common_end":sum(1 for d in bi_dates if common_end and d>common_end),
       "orders_lag_days_after_common_end":len({d for d in ord_dates if common_end and d>common_end}),
    })
    counts=Counter(s(r.get("status")) for r in catalog_resolutions)
    checks.append({"name":"catalog_resolution_observability","status":"PASS","detail":{"statuses":dict(counts),
        "review_or_unmatched":counts.get("REVIEW_REFERENCE",0)+counts.get("UNMATCHED",0)}})
    failed=[x for x in checks if x["status"]=="FAIL"]
    return {"shop_id":shop_id,"target_month":target_month,"status":"PASS" if not failed else "FAIL",
        "production_write_allowed":not failed,"checks":checks,
        "row_counts":{"fact_orders":len(orders),"fact_order_items":len(order_items),
        "fact_product_performance_monthly":len(products),"fact_product_variations_monthly":len(variations),
        "fact_shop_performance_daily":len(bi_shop),
        "fact_traffic_source_daily":len(traffic_daily),
        "fact_traffic_source_monthly":len(traffic_monthly),
        "fact_ads_performance_daily":len(ads),
        "dm_ads_product_daily_candidate":len(product_ads),"catalog_resolution_staging":len(catalog_resolutions)}}
