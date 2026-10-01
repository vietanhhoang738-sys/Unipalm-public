"""Multi-shop semantic marts built from shop-scoped processed v2 partitions.

The semantic layer is intentionally storage/UI agnostic. It combines multiple
shop partitions only after every input partition has PASSed processed QA.

Design rules:
- every shop-grain business row carries shop_id;
- joins use shop_id + business key;
- cross-shop Product ID joins are forbidden;
- ratios are recomputed from additive numerators/denominators;
- combined daily KPIs use the common reliable window across Orders, Ads and BI;
- source-specific marts keep their own available freshness.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


DEFAULT_CONTRACT_PATH=Path(__file__).resolve().parents[2]/"config"/"semantic_mart_contract.json"


def s(v:Any)->str:
    return "" if v is None else str(v).strip()


def n(v:Any)->float:
    if v in (None,""):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def i(v:Any)->int:
    return int(round(n(v)))


def ratio(num:Any,den:Any)->float:
    d=n(den)
    return n(num)/d if d else 0.0


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(value:Any)->str:
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_json(path:Path)->Dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path:Path)->List[Dict[str,Any]]:
    out=[]
    with path.open("r",encoding="utf-8") as f:
        for ln,line in enumerate(f,1):
            if not line.strip():
                continue
            row=json.loads(line)
            if not isinstance(row,dict):
                raise ValueError(f"{path}: line {ln} is not an object")
            out.append(row)
    return out


def write_jsonl(path:Path,rows:Sequence[Mapping[str,Any]])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(dict(row),ensure_ascii=False,sort_keys=True)+"\n")


def load_contract(path:str|Path="")->Dict[str,Any]:
    p=Path(path) if path else DEFAULT_CONTRACT_PATH
    data=read_json(p)
    if not data.get("marts"):
        raise ValueError("semantic mart contract has no marts")
    return data


def _month(value:Any)->str:
    return s(value)[:7]


def _date(value:Any)->str:
    return s(value)[:10]


def _required_file(partition:Path,relative:str)->Path:
    p=partition/relative
    if not p.exists():
        raise FileNotFoundError(f"{partition}: missing {relative}")
    return p


def _load_partition(partition:Path,shop:Mapping[str,Any],period:str)->Dict[str,Any]:
    manifest=read_json(_required_file(partition,"manifest.json"))
    qa=read_json(_required_file(partition,"processed_qa_report.json"))
    if qa.get("status")!="PASS" or not qa.get("processed_partition_ready"):
        raise ValueError(f"{shop['shop_key']}/{period}: processed QA not ready")
    if s(manifest.get("shop_id"))!=s(shop.get("shop_id")):
        raise ValueError(f"{shop['shop_key']}/{period}: manifest shop_id mismatch")
    if s(manifest.get("period"))!=period:
        raise ValueError(f"{shop['shop_key']}/{period}: manifest period mismatch")

    files={
        "orders":"orders/fact_orders.jsonl",
        "ads":"ads/fact_ads_performance_daily.jsonl",
        "ads_product":"ads/fact_ads_product_daily.jsonl",
        "products":"product_performance/fact_product_performance_monthly.jsonl",
        "bi_shop":"business_insights/fact_shop_performance_daily.jsonl",
        "traffic_daily":"business_insights/fact_traffic_source_daily.jsonl",
        "catalog":"catalog/catalog_resolution.jsonl",
        "listing_products":"listing_catalog/products_snapshot.jsonl",
        "pipeline_state":"control/pipeline_state.jsonl",
    }
    data={k:read_jsonl(_required_file(partition,v)) for k,v in files.items()}
    sid=s(shop.get("shop_id"))
    for label,rows in data.items():
        if label=="pipeline_state":
            continue
        foreign=sorted({s(r.get("shop_id")) for r in rows if s(r.get("shop_id"))!=sid})
        if foreign:
            raise ValueError(f"{shop['shop_key']}/{period}/{label}: foreign shop ids {foreign}")
    data["manifest"]=manifest
    data["qa"]=qa
    data["shop"]=dict(shop)
    data["partition"]=str(partition)
    return data


def _state_map(rows:Sequence[Mapping[str,Any]])->Dict[str,Mapping[str,Any]]:
    return {s(r.get("source_domain")):r for r in rows}


def _common_window(part:Mapping[str,Any],period:str)->Tuple[str,str,Dict[str,str]]:
    states=_state_map(part["pipeline_state"])
    ends={}
    for domain in ("orders","ads","business_insights"):
        end=_date((states.get(domain) or {}).get("verified_through"))
        if not end or _month(end)!=period:
            raise ValueError(f"{part['shop']['shop_key']}/{period}: no verified date for {domain}")
        ends[domain]=end

    source_starts={"orders":f"{period}-01"}
    ads=[_date(r.get("data_date")) for r in part["ads"] if _month(r.get("data_date"))==period]
    bi=[_date(r.get("data_date")) for r in part["bi_shop"] if _month(r.get("data_date"))==period]
    for domain,vals in (("ads",ads),("business_insights",bi)):
        vals=[x for x in vals if x]
        source_starts[domain]=min(vals) if vals else f"{period}-01"

    start=max(source_starts.values())
    end=min(ends.values())
    if start>end:
        raise ValueError(f"{part['shop']['shop_key']}/{period}: no common reliable daily window")
    return start,end,ends


def _agg_ads_daily(rows:Sequence[Mapping[str,Any]],period:str,shop_id:str)->List[Dict[str,Any]]:
    agg=defaultdict(lambda:defaultdict(float))
    for r in rows:
        if s(r.get("shop_id"))!=shop_id or _month(r.get("data_date"))!=period:
            continue
        d=_date(r.get("data_date"))
        for f in ("impressions","clicks","add_to_cart","conversions","units_sold","attributed_sales","ad_spend"):
            agg[d][f]+=n(r.get(f))
    out=[]
    for d,a in sorted(agg.items()):
        out.append({
            "shop_id":shop_id,"data_date":d,
            "impressions":i(a["impressions"]),"clicks":i(a["clicks"]),
            "add_to_cart":i(a["add_to_cart"]),"conversions":i(a["conversions"]),
            "units_sold":i(a["units_sold"]),
            "attributed_sales":a["attributed_sales"],"ad_spend":a["ad_spend"],
            "ctr":ratio(a["clicks"],a["impressions"]),
            "cvr":ratio(a["conversions"],a["clicks"]),
            "roas":ratio(a["attributed_sales"],a["ad_spend"]),
            "cpc":ratio(a["ad_spend"],a["clicks"]),
            "cpm":ratio(a["ad_spend"]*1000,a["impressions"]),
            "cpa":ratio(a["ad_spend"],a["conversions"]),
            "acos":ratio(a["ad_spend"],a["attributed_sales"]),
        })
    return out


def _commercial_rows(part:Mapping[str,Any],period:str)->List[Dict[str,Any]]:
    sid=s(part["shop"]["shop_id"])
    out=[]
    for r in part["bi_shop"]:
        if _month(r.get("data_date"))!=period:
            continue
        orders=i(r.get("order_count"))
        clicks=i(r.get("product_clicks"))
        cancelled=i(r.get("cancelled_orders"))
        rr=i(r.get("returned_refunded_orders"))
        gmv=n(r.get("gross_sales"))
        out.append({
            "shop_id":sid,"data_date":_date(r.get("data_date")),
            "order_stage":s(r.get("order_stage")),
            "gmv":gmv,"orders":orders,
            "aov":ratio(gmv,orders),
            "product_clicks":clicks,"visits":i(r.get("visits")),
            "cvr":ratio(orders,clicks),
            "cancelled_orders":cancelled,"cancelled_sales":n(r.get("cancelled_sales")),
            "cancel_rate":ratio(cancelled,orders),
            "rr_orders":rr,"rr_sales":n(r.get("returned_refunded_sales")),
            "rr_rate":ratio(rr,orders),
            "buyers":i(r.get("buyers")),"new_buyers":i(r.get("new_buyers")),
            "existing_buyers":i(r.get("existing_buyers")),
            "potential_buyers":i(r.get("potential_buyers")),
        })
    return sorted(out,key=lambda x:(x["shop_id"],x["data_date"],x["order_stage"]))


def _order_daily(part:Mapping[str,Any],period:str)->Dict[str,Dict[str,Any]]:
    out=defaultdict(lambda:{
        "orders":0,"fixed_fee":0.0,"service_fee":0.0,"transaction_fee":0.0,
        "completed_fulfill_hours":[],
    })
    for r in part["orders"]:
        if _month(r.get("order_created_at"))!=period:
            continue
        d=_date(r.get("order_created_at"))
        rec=out[d]
        rec["orders"]+=1
        rec["fixed_fee"]+=n(r.get("fixed_fee"))
        rec["service_fee"]+=n(r.get("service_fee"))
        rec["transaction_fee"]+=n(r.get("transaction_fee"))
    return out


def _build_shop_daily(
    part:Mapping[str,Any],
    period:str,
    common_start:str,
    common_end:str,
    ads_daily:Sequence[Mapping[str,Any]],
)->Tuple[List[Dict[str,Any]],List[Dict[str,Any]]]:
    sid=s(part["shop"]["shop_id"])
    stages={( _date(r["data_date"]),s(r.get("order_stage")) ):r
            for r in part["bi_shop"] if _month(r.get("data_date"))==period}
    ads={_date(r["data_date"]):r for r in ads_daily}
    orders=_order_daily(part,period)

    dates=sorted({d for d,stage in stages if common_start<=d<=common_end})
    daily=[]; quality=[]
    for d in dates:
        rows={stage:stages.get((d,stage)) for stage in ("placed","confirmed","paid")}
        if any(v is None for v in rows.values()):
            raise ValueError(f"{part['shop']['shop_key']}/{d}: missing BI stage row")
        placed,confirmed,paid=rows["placed"],rows["confirmed"],rows["paid"]
        ad=ads.get(d,{})
        od=orders.get(d,{})
        fees=n(od.get("fixed_fee"))+n(od.get("service_fee"))+n(od.get("transaction_fee"))
        placed_gmv=n(placed.get("gross_sales"))
        placed_orders=i(placed.get("order_count"))
        confirmed_gmv=n(confirmed.get("gross_sales"))
        confirmed_orders=i(confirmed.get("order_count"))
        paid_gmv=n(paid.get("gross_sales"))
        paid_orders=i(paid.get("order_count"))
        cancelled_sales=n(placed.get("cancelled_sales"))
        net=placed_gmv-cancelled_sales
        ad_spend=n(ad.get("ad_spend"))
        ad_sales=n(ad.get("attributed_sales"))
        product_clicks=i(placed.get("product_clicks"))
        daily.append({
            "shop_id":sid,"data_date":d,
            "common_reliable_start":common_start,"common_reliable_end":common_end,
            "visits":i(placed.get("visits")),"product_clicks":product_clicks,
            "buyers":i(placed.get("buyers")),"new_buyers":i(placed.get("new_buyers")),
            "existing_buyers":i(placed.get("existing_buyers")),
            "potential_buyers":i(placed.get("potential_buyers")),
            "placed_gmv":placed_gmv,"placed_orders":placed_orders,
            "placed_aov":ratio(placed_gmv,placed_orders),
            "placed_cvr":ratio(placed_orders,product_clicks),
            "confirmed_gmv":confirmed_gmv,"confirmed_orders":confirmed_orders,
            "confirmed_aov":ratio(confirmed_gmv,confirmed_orders),
            "paid_gmv":paid_gmv,"paid_orders":paid_orders,
            "cancelled_orders":i(placed.get("cancelled_orders")),
            "cancelled_sales":cancelled_sales,
            "returned_refunded_orders":i(placed.get("returned_refunded_orders")),
            "returned_refunded_sales":n(placed.get("returned_refunded_sales")),
            "net_sales_after_cancel":net,
            "ads_impressions":i(ad.get("impressions")),"ads_clicks":i(ad.get("clicks")),
            "ads_conversions":i(ad.get("conversions")),
            "ads_attributed_sales":ad_sales,"ads_spend":ad_spend,
            "ads_ctr":ratio(ad.get("clicks"),ad.get("impressions")),
            "ads_cvr":ratio(ad.get("conversions"),ad.get("clicks")),
            "roas":ratio(ad_sales,ad_spend),
            "fixed_fee":n(od.get("fixed_fee")),"service_fee":n(od.get("service_fee")),
            "transaction_fee":n(od.get("transaction_fee")),"order_fees":fees,
            "total_platform_cost_ratio":ratio(fees+ad_spend,net),
            "reliable_flag":True,
        })
        quality.append({
            "shop_id":sid,"data_date":d,
            "total_orders":i(od.get("orders")),
            "cancelled_orders":i(placed.get("cancelled_orders")),
            "cancel_rate":ratio(placed.get("cancelled_orders"),od.get("orders")),
            "rr_orders":i(placed.get("returned_refunded_orders")),
            "rr_rate":ratio(placed.get("returned_refunded_orders"),od.get("orders")),
            "fixed_fee":n(od.get("fixed_fee")),"service_fee":n(od.get("service_fee")),
            "transaction_fee":n(od.get("transaction_fee")),"order_fees":fees,
            "common_reliable_end":common_end,
        })
    return daily,quality


def _traffic_rows(rows:Sequence[Mapping[str,Any]],*,period:str)->List[Dict[str,Any]]:
    out=[]
    key="data_date"
    for r in rows:
        if _month(r.get(key))!=period:
            continue
        impressions=i(r.get("impressions")); clicks=i(r.get("clicks"))
        orders=n(r.get("orders")); sales=n(r.get("sales"))
        row={
            "shop_id":s(r.get("shop_id")),
            key:_date(r.get("data_date")),
            "order_stage":s(r.get("order_stage")),
            "channel_group":s(r.get("channel_group")),
            "traffic_source":s(r.get("traffic_source")),
            "sales_ratio":n(r.get("sales_ratio")),
            "sales":sales,"impressions":impressions,"clicks":clicks,
            "attributed_orders":orders,"attributed_units":n(r.get("units")),
            "ctr":ratio(clicks,impressions),
            "conversion_rate":ratio(orders,clicks),
            "sales_per_order":ratio(sales,orders),
            "buyers":i(r.get("buyers")),
            "unique_impressions":i(r.get("unique_impressions")),
            "unique_clicks":i(r.get("unique_clicks")),
        }
        out.append(row)
    grain=lambda x:(x["shop_id"],x[key],x["order_stage"],x["channel_group"],x["traffic_source"])
    return sorted(out,key=grain)


def _is_deleted_product_status(value:Any)->bool:
    return s(value).casefold() in {"đã xóa","deleted","removed"}


def _ads_product_rows(part:Mapping[str,Any],period:str)->List[Dict[str,Any]]:
    sid=s(part["shop"]["shop_id"])
    products={(sid,s(r.get("product_id"))):r for r in part["products"] if s(r.get("product_id"))}
    catalog={(sid,s(r.get("product_id"))):r for r in part["catalog"] if s(r.get("product_id"))}
    out=[]
    for r in part["ads_product"]:
        if _month(r.get("data_date"))!=period:
            continue
        pid=s(r.get("product_id"))
        p=products.get((sid,pid),{})
        c=catalog.get((sid,pid),{})
        impressions=i(r.get("impressions")); clicks=i(r.get("clicks"))
        conversions=i(r.get("conversions")); spend=n(r.get("ad_spend")); sales=n(r.get("attributed_sales"))
        out.append({
            "shop_id":sid,"data_date":_date(r.get("data_date")),"product_id":pid,
            "product_name":s(p.get("product_name")) or s(r.get("product_name")) or pid,
            "product_sku_observed":s(p.get("product_sku")),
            "resolved_parent_sku":s(c.get("resolved_parent_sku")),
            "catalog_status":s(c.get("status")),
            "impressions":impressions,"clicks":clicks,
            "add_to_cart":i(r.get("add_to_cart")),"conversions":conversions,
            "units_sold":i(r.get("units_sold")),
            "attributed_sales":sales,"ad_spend":spend,
            "ctr":ratio(clicks,impressions),"cvr":ratio(conversions,clicks),
            "roas":ratio(sales,spend),"cpc":ratio(spend,clicks),
            "cpa":ratio(spend,conversions),"acos":ratio(spend,sales),
        })
    return sorted(out,key=lambda x:(x["shop_id"],x["data_date"],x["product_id"]))


def _product_monthly_rows(
    part:Mapping[str,Any],
    period:str,
    ads_product:Sequence[Mapping[str,Any]],
)->List[Dict[str,Any]]:
    sid=s(part["shop"]["shop_id"])
    catalog={(sid,s(r.get("product_id"))):r for r in part["catalog"] if s(r.get("product_id"))}
    current_listing_ids={s(r.get("product_id")) for r in part["listing_products"] if s(r.get("product_id"))}
    ads=defaultdict(lambda:defaultdict(float))
    ads_end=""
    for r in ads_product:
        pid=s(r.get("product_id"))
        ads_end=max(ads_end,_date(r.get("data_date")))
        for f in ("impressions","clicks","conversions","units_sold","attributed_sales","ad_spend"):
            ads[pid][f]+=n(r.get(f))
    products=[r for r in part["products"] if _month(r.get("data_month"))==period]
    total_confirmed=sum(n(r.get("confirmed_gmv_vnd")) for r in products)
    out=[]
    for r in products:
        pid=s(r.get("product_id")); c=catalog.get((sid,pid),{}); a=ads[pid]
        current_listing_present=pid in current_listing_ids
        if c:
            catalog_join_status="MATCHED_CURRENT_CATALOG"
        elif (not current_listing_present) and _is_deleted_product_status(r.get("product_status")):
            catalog_join_status="HISTORICAL_DELETED_NO_CURRENT_LISTING"
        else:
            catalog_join_status="MISSING_CURRENT_CATALOG"
        placed_gmv=n(r.get("placed_gmv_vnd")); placed_orders=i(r.get("placed_orders"))
        confirmed_gmv=n(r.get("confirmed_gmv_vnd")); confirmed_orders=i(r.get("confirmed_orders"))
        product_views=i(r.get("product_views")); product_clicks=i(r.get("product_clicks"))
        spend=a["ad_spend"]; sales=a["attributed_sales"]
        out.append({
            "shop_id":sid,"data_month":period,"product_id":pid,
            "product_name":s(r.get("product_name")),
            "product_status":s(r.get("product_status")),
            "product_sku_observed":s(r.get("product_sku")),
            "resolved_parent_sku":s(c.get("resolved_parent_sku")),
            "canonical_family_key":s(c.get("canonical_family_key")),
            "catalog_status":s(c.get("status")) or ("NOT_IN_CURRENT_CATALOG" if not c else ""),
            "catalog_join_status":catalog_join_status,
            "current_listing_present":current_listing_present,
            "catalog_confidence":n(c.get("confidence")),
            "placed_gmv":placed_gmv,"placed_orders":placed_orders,
            "confirmed_gmv":confirmed_gmv,"confirmed_orders":confirmed_orders,
            "confirmed_gmv_share":ratio(confirmed_gmv,total_confirmed),
            "placed_aov":ratio(placed_gmv,placed_orders),
            "confirmed_aov":ratio(confirmed_gmv,confirmed_orders),
            "product_views":product_views,"product_clicks":product_clicks,
            "ctr":ratio(product_clicks,product_views),
            "unique_impressions":i(r.get("unique_product_impressions")),
            "unique_clicks":i(r.get("unique_product_clicks")),
            "product_visits":i(r.get("product_visits")),
            "product_page_views":i(r.get("product_page_views")),
            "page_bounces":i(r.get("product_page_bounces")),
            "bounce_rate":ratio(r.get("product_page_bounces"),r.get("product_visits")),
            "add_to_cart_visits":i(r.get("add_to_cart_visits")),
            "add_to_cart_units":i(r.get("add_to_cart_units")),
            "atc_rate":ratio(r.get("add_to_cart_visits"),r.get("product_visits")),
            "confirmed_units":i(r.get("confirmed_units")),
            "confirmed_buyers":i(r.get("confirmed_buyers")),
            "repeat_order_rate":n(r.get("confirmed_repeat_order_rate")),
            "avg_days_to_repeat":n(r.get("confirmed_avg_days_to_repeat_order")),
            "ads_coverage_end":ads_end,
            "ads_impressions":i(a["impressions"]),"ads_clicks":i(a["clicks"]),
            "ads_conversions":i(a["conversions"]),"ads_units_sold":i(a["units_sold"]),
            "ads_attributed_sales":sales,"ads_spend":spend,
            "ads_ctr":ratio(a["clicks"],a["impressions"]),
            "ads_cvr":ratio(a["conversions"],a["clicks"]),
            "roas":ratio(sales,spend),
        })
    return sorted(out,key=lambda x:(x["shop_id"],x["product_id"]))


def _unique_grain(rows:Sequence[Mapping[str,Any]],grain:Sequence[str])->Tuple[bool,List[Tuple[Any,...]]]:
    seen=set(); dup=[]
    for r in rows:
        key=tuple(r.get(x) for x in grain)
        if key in seen:
            dup.append(key)
        seen.add(key)
    return not dup,dup[:20]


def _ratio_close(actual:Any,expected:float,tol:float=1e-9)->bool:
    return abs(n(actual)-expected)<=tol


def validate_semantic(
    marts:Mapping[str,Sequence[Mapping[str,Any]]],
    contract:Mapping[str,Any],
    selected_shop_ids:Sequence[str],
)->Dict[str,Any]:
    checks=[]
    def ck(name,ok,detail=None):
        checks.append({"name":name,"status":"PASS" if ok else "FAIL","detail":detail or {}})

    allowed=set(selected_shop_ids)
    for name,spec in contract["marts"].items():
        rows=list(marts.get(name) or [])
        ok,dup=_unique_grain(rows,spec["grain"])
        ck(f"{name}_grain_unique",ok,{"rows":len(rows),"duplicates":dup})
        if name!="dim_shop":
            foreign=sorted({s(r.get("shop_id")) for r in rows if s(r.get("shop_id")) not in allowed})
            ck(f"{name}_shop_isolation",not foreign,{"foreign_shop_ids":foreign})

    daily=list(marts.get("dm_shop_daily") or [])
    ratio_errors=[]
    for r in daily:
        expectations={
            "placed_aov":ratio(r.get("placed_gmv"),r.get("placed_orders")),
            "placed_cvr":ratio(r.get("placed_orders"),r.get("product_clicks")),
            "confirmed_aov":ratio(r.get("confirmed_gmv"),r.get("confirmed_orders")),
            "ads_ctr":ratio(r.get("ads_clicks"),r.get("ads_impressions")),
            "ads_cvr":ratio(r.get("ads_conversions"),r.get("ads_clicks")),
            "roas":ratio(r.get("ads_attributed_sales"),r.get("ads_spend")),
        }
        for field,expected in expectations.items():
            if not _ratio_close(r.get(field),expected):
                ratio_errors.append((r.get("shop_id"),r.get("data_date"),field,r.get(field),expected))
    ck("dm_shop_daily_ratios_recomputed",not ratio_errors,{"errors":ratio_errors[:20]})

    product_rows=list(marts.get("dm_product_monthly") or [])
    invalid_catalog=[
        (r.get("shop_id"),r.get("product_id"),r.get("product_status"),r.get("catalog_join_status"))
        for r in product_rows
        if s(r.get("catalog_join_status")) not in {
            "MATCHED_CURRENT_CATALOG",
            "HISTORICAL_DELETED_NO_CURRENT_LISTING",
        }
    ]
    historical_deleted=[
        (r.get("shop_id"),r.get("product_id"))
        for r in product_rows
        if s(r.get("catalog_join_status"))=="HISTORICAL_DELETED_NO_CURRENT_LISTING"
    ]
    ck("product_catalog_join_scoped",not invalid_catalog,{
        "invalid_catalog":invalid_catalog[:20],
        "historical_deleted_without_current_listing":historical_deleted[:20],
    })

    failed=[x for x in checks if x["status"]=="FAIL"]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_check_count":len(failed)}


def build_semantic_marts(
    *,
    processed_root:str|Path,
    output_dir:str|Path,
    period:str,
    shops:Sequence[Mapping[str,Any]],
    contract_path:str|Path="",
    generated_at:str="",
)->Dict[str,Any]:
    processed_root=Path(processed_root)
    output_dir=Path(output_dir)
    contract=load_contract(contract_path)

    parts=[]
    for shop in shops:
        part_path=processed_root/s(shop["shop_key"])/period
        parts.append(_load_partition(part_path,shop,period))

    marts={
        "dim_shop":[],
        "dm_shop_daily":[],
        "dm_commercial_stage_daily":[],
        "dm_ads_daily":[],
        "dm_ads_product_daily":[],
        "dm_product_monthly":[],
        "dm_traffic_source_daily":[],
        "dm_order_quality_daily":[],
    }
    source_partitions=[]
    freshness={}
    for part in parts:
        shop=part["shop"]; sid=s(shop["shop_id"]); sk=s(shop["shop_key"])
        common_start,common_end,ends=_common_window(part,period)
        freshness[sid]={
            "common_reliable_start":common_start,
            "common_reliable_end":common_end,
            "source_verified_through":ends,
        }
        badge=shop.get("shop_badge") or {}
        marts["dim_shop"].append({
            "shop_id":sid,"shop_key":sk,"display_name":s(shop.get("display_name")),
            "platform":s(shop.get("platform")),"enabled":bool(shop.get("enabled")),
            "shop_badge_kind":s(badge.get("kind")),
            "shop_badge_label":s(badge.get("label")),
        })

        commercial=_commercial_rows(part,period)
        ads_daily=_agg_ads_daily(part["ads"],period,sid)
        shop_daily,quality=_build_shop_daily(part,period,common_start,common_end,ads_daily)
        ads_product=_ads_product_rows(part,period)
        products=_product_monthly_rows(part,period,ads_product)

        marts["dm_commercial_stage_daily"].extend(commercial)
        marts["dm_ads_daily"].extend(ads_daily)
        marts["dm_shop_daily"].extend(shop_daily)
        marts["dm_order_quality_daily"].extend(quality)
        marts["dm_ads_product_daily"].extend(ads_product)
        marts["dm_product_monthly"].extend(products)
        marts["dm_traffic_source_daily"].extend(
            _traffic_rows(part["traffic_daily"],period=period))

        source_partitions.append({
            "shop_key":sk,"shop_id":sid,"period":period,
            "processed_build_fingerprint":s(part["manifest"].get("build_fingerprint")),
        })

    qa=validate_semantic(
        marts,contract,[s(x["shop_id"]) for x in shops])

    output_dir.mkdir(parents=True,exist_ok=True)
    file_meta=[]
    for name,rows in marts.items():
        path=output_dir/f"{name}.jsonl"
        write_jsonl(path,rows)
        file_meta.append({
            "name":name,"file":path.name,"rows":len(rows),"sha256":sha256_file(path),
            "grain":contract["marts"][name]["grain"],
        })

    fingerprint=sha256_json({
        "contract_version":contract.get("version"),
        "period":period,
        "sources":sorted(source_partitions,key=lambda x:x["shop_id"]),
        "files":[{"name":x["name"],"sha256":x["sha256"],"rows":x["rows"]}
                 for x in sorted(file_meta,key=lambda x:x["name"])],
    })
    manifest={
        "layer":contract.get("layer_name"),"contract_version":contract.get("version"),
        "period":period,"generated_at":generated_at,
        "semantic_build_fingerprint":fingerprint,
        "source_partitions":source_partitions,"freshness":freshness,
        "files":file_meta,
        "safety":{
            "legacy_data_mart_written":False,
            "production_data_mart_written":False,
            "ui_modified":False,
        },
    }
    (output_dir/"manifest.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    qa.update({
        "period":period,"semantic_build_fingerprint":fingerprint,
        "selected_shop_count":len(shops),"selected_shop_ids":[s(x["shop_id"]) for x in shops],
        "semantic_mart_ready":qa["status"]=="PASS",
        "safety":manifest["safety"],
    })
    (output_dir/"semantic_qa_report.json").write_text(
        json.dumps(qa,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    if qa["status"]!="PASS":
        raise ValueError(f"semantic QA failed: {[x['name'] for x in qa['checks'] if x['status']=='FAIL']}")
    return {
        "status":"PASS","period":period,"semantic_mart_ready":True,
        "semantic_build_fingerprint":fingerprint,
        "selected_shop_count":len(shops),
        "output_location":str(output_dir),
        "files":file_meta,"freshness":freshness,
    }
