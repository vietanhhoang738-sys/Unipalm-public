"""Deterministic Product short-name resolver for operator-facing UI.

The canonical Product title remains untouched. This module derives a compact
operator label from explicit category/family/model tokens and falls back to the
full title whenever the structure is not sufficiently clear.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Mapping


RULE_VERSION = "product-short-name-v1"
MODEL_RE = re.compile(r"\b(Cool|Air|Slim)\s+([SF]\d+(?:\s+Plus)?)\b", re.I)
BARE_MODEL_RE = re.compile(r"\b([SF]\d+(?:\s+Plus)?)\b", re.I)
COMBO_RE = re.compile(r"\bCombo\s+(\d+)\b", re.I)


def s(v: Any) -> str:
    return "" if v is None else re.sub(r"\s+", " ", str(v)).strip()


def _model(family: str, model: str) -> str:
    fam = family[:1].upper() + family[1:].lower()
    raw = re.sub(r"\s+", " ", model.strip())
    raw = re.sub(r"\bplus\b", "Plus", raw, flags=re.I)
    if raw:
        raw = raw[0].upper() + raw[1:]
    return f"{fam} {raw}".strip()


def _component_category(text: str) -> str:
    low = text.casefold()
    if "khẩu trang" in low:
        return "Khẩu trang"
    if "ống tay" in low:
        return "Ống tay"
    if "găng tay" in low:
        return "Găng tay"
    return ""


def _category(text: str) -> str:
    low = text.casefold()
    if "không thể lấy thông tin sản phẩm do bị xóa" in low:
        return "DELETED"
    if "cặp đôi" in low:
        return "Cặp đôi"
    if "bao lì xì" in low:
        return "Bao lì xì"
    if "scrunchie" in low or "dây buộc tóc" in low:
        return "Scrunchie"
    if ("thẻ" in low or "card" in low) and any(x in low for x in ("tia uv", "uva", "uvb", "cực tím")):
        return "Thẻ UV"
    if re.search(r"\b(tất|vớ)\b", low):
        return "Tất"
    if "khẩu trang" in low:
        return "Khẩu trang"
    if "ống tay" in low:
        return "Ống tay"
    if "găng tay" in low:
        return "Găng tay"
    return ""


def _extract_model(text: str, category_hint: str = "") -> str:
    explicit = MODEL_RE.search(text)
    if explicit:
        return _model(explicit.group(1), explicit.group(2))
    bare = BARE_MODEL_RE.search(text)
    if not bare:
        return ""
    model = re.sub(r"\bplus\b", "Plus", bare.group(1), flags=re.I)
    model = model[0].upper() + model[1:]
    if category_hint == "Khẩu trang":
        return f"Cool {model}"
    if category_hint in {"Găng tay", "Ống tay"}:
        return f"Air {model}"
    return ""


def _is_male_variant(name: str, sku: str) -> bool:
    low = name.casefold()
    return bool(re.search(r"\bcho nam\b", low) or re.search(r"\bnam\b", low) and "nữ" not in low or sku.upper().endswith("-MEN"))


def resolve_short_product_name(product_name: Any, parent_sku: Any = "", product_id: Any = "") -> Dict[str, Any]:
    full_name = s(product_name)
    sku = s(parent_sku)
    pid = s(product_id)
    category = _category(full_name)
    short = ""
    confidence = "FALLBACK"
    rule = "FULL_NAME_FALLBACK"
    model_tokens = []

    if not full_name:
        short = sku or pid or "Sản phẩm chưa xác định"
        rule = "EMPTY_TITLE_FALLBACK"
    elif category == "DELETED":
        suffix = sku or pid
        short = "Sản phẩm đã xóa" + (f" · {suffix}" if suffix else "")
        confidence = "HIGH"
        rule = "DELETED_PRODUCT"
    elif category == "Cặp đôi":
        parts = re.split(r"\s*&\s*", full_name, maxsplit=1)
        for part in parts:
            token = _extract_model(part, _component_category(part))
            if token:
                model_tokens.append(token)
        if len(model_tokens) < 2:
            model_tokens = [_model(m.group(1), m.group(2)) for m in MODEL_RE.finditer(full_name)]
        if len(model_tokens) >= 2:
            short = f"Cặp đôi {model_tokens[0]} + {model_tokens[1]}"
            confidence = "HIGH"
            rule = "PAIR_TWO_MODELS"
        else:
            short = "Cặp đôi" + (f" · {sku}" if sku else "")
            confidence = "MEDIUM"
            rule = "PAIR_CATEGORY_ONLY"
    elif category in {"Khẩu trang", "Găng tay", "Ống tay"}:
        token = _extract_model(full_name, category)
        if token:
            model_tokens = [token]
        combo = COMBO_RE.search(full_name)
        if combo:
            short = f"Combo {combo.group(1)} {category}"
            if token:
                short += f" {token}"
            confidence = "HIGH" if token else "MEDIUM"
            rule = "COMBO_CATEGORY_MODEL" if token else "COMBO_CATEGORY_ONLY"
        elif token:
            short = f"{category} {token}"
            confidence = "HIGH"
            rule = "CATEGORY_MODEL"
        else:
            short = full_name
        if short != full_name and _is_male_variant(full_name, sku):
            short += " · Nam"
    elif category in {"Scrunchie", "Thẻ UV", "Tất", "Bao lì xì"}:
        short = category
        confidence = "HIGH"
        rule = "ACCESSORY_ALIAS"
    else:
        short = full_name

    return {
        "shortName": short or full_name,
        "fullName": full_name,
        "category": category if category != "DELETED" else "Sản phẩm đã xóa",
        "modelTokens": model_tokens,
        "confidence": confidence,
        "rule": rule,
        "ruleVersion": RULE_VERSION,
        "parentSku": sku,
        "productId": pid,
    }


def short_name_for_product(product: Mapping[str, Any]) -> Dict[str, Any]:
    return resolve_short_product_name(
        product.get("productName") or product.get("product_name"),
        product.get("resolvedParentSku") or product.get("resolved_parent_sku") or product.get("productSkuObserved"),
        product.get("productId") or product.get("product_id"),
    )
