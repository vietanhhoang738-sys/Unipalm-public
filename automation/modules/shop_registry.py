"""Registry-driven shop configuration for N-shop ingestion.

The registry is the only place where concrete shop identities belong. Generic
pipeline modules must not embed shop IDs, names, or a fixed shop count.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

CORE_STAGING_DOMAINS=("orders","ads","product_performance","business_insights")
OPTIONAL_STAGING_DOMAINS=("returns_refunds","listing_catalog")
SUPPORTED_PLATFORMS={"shopee"}
SUPPORTED_ROOT_TYPES={"folder_id","child_folder"}

def _s(v:Any)->str:
    return "" if v is None else str(v).strip()

def load_shop_registry(path:str|Path)->Dict[str,Any]:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    shops=data.get("shops")
    if not isinstance(shops,list) or not shops:
        raise ValueError("shop_registry.shops must be a non-empty list")

    seen={k:set() for k in ("shop_key","shop_id","shopee_shop_id")}
    for idx,shop in enumerate(shops):
        if not isinstance(shop,dict):
            raise ValueError(f"shop_registry.shops[{idx}] must be an object")
        for field in ("shop_key","shop_id","shopee_shop_id","display_name"):
            if not _s(shop.get(field)):
                raise ValueError(f"shop_registry.shops[{idx}] missing {field}")
        for field in seen:
            value=_s(shop.get(field))
            if value in seen[field]:
                raise ValueError(f"duplicate {field}: {value}")
            seen[field].add(value)

        platform=_s(shop.get("platform") or "shopee").lower()
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"{shop['shop_key']}: unsupported platform {platform}")
        shop["platform"]=platform
        shop["enabled"]=bool(shop.get("enabled",True))

        roots=shop.get("raw_root_candidates")
        if not isinstance(roots,list) or not roots:
            raise ValueError(f"{shop['shop_key']}: raw_root_candidates must be non-empty")
        for ridx,root in enumerate(roots):
            if not isinstance(root,dict):
                raise ValueError(f"{shop['shop_key']}: raw_root_candidates[{ridx}] must be an object")
            typ=_s(root.get("type"))
            if typ not in SUPPORTED_ROOT_TYPES:
                raise ValueError(f"{shop['shop_key']}: unsupported raw root type {typ!r}")
            if typ=="folder_id" and not _s(root.get("folder_id")):
                raise ValueError(f"{shop['shop_key']}: folder_id root missing folder_id")
            if typ=="child_folder" and (not _s(root.get("parent_folder_id")) or not _s(root.get("folder_name"))):
                raise ValueError(f"{shop['shop_key']}: child_folder root requires parent_folder_id + folder_name")
            root["priority"]=int(root.get("priority",0))

    return data

def enabled_shops(registry:Dict[str,Any])->List[Dict[str,Any]]:
    return [x for x in registry["shops"] if bool(x.get("enabled",True))]

def get_shop(registry:Dict[str,Any],shop_key:str)->Dict[str,Any]:
    for shop in registry["shops"]:
        if _s(shop.get("shop_key"))==_s(shop_key):
            return shop
    raise KeyError(f"shop_key not found: {shop_key}")

def select_shops(registry:Dict[str,Any],selector:str|Iterable[str])->List[Dict[str,Any]]:
    if isinstance(selector,str):
        keys=[selector]
    else:
        keys=list(selector)
    normalized=[_s(x) for x in keys if _s(x)]
    if not normalized or normalized==["all"]:
        return enabled_shops(registry)
    if "all" in normalized:
        raise ValueError("'all' cannot be combined with explicit shop keys")
    out=[]
    seen=set()
    for key in normalized:
        if key in seen:
            continue
        shop=get_shop(registry,key)
        if not bool(shop.get("enabled",True)):
            raise ValueError(f"shop {key} is disabled")
        out.append(shop); seen.add(key)
    return out

def registry_summary(registry:Dict[str,Any])->Dict[str,Any]:
    enabled=enabled_shops(registry)
    return {
        "version":_s(registry.get("version")),
        "shops_total":len(registry["shops"]),
        "shops_enabled":len(enabled),
        "shop_keys":[_s(x.get("shop_key")) for x in enabled],
        "platforms":sorted({_s(x.get("platform")) for x in enabled}),
    }
