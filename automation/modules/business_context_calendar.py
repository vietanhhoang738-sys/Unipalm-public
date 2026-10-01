"""Explicit-source business context calendar for PREPRODUCTION.

This layer converts reviewed platform/government/industry sources into
deterministic dated context records. It must never infer campaign dates from
metric movements.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")


def _sha256_json(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _to_date(v: str) -> dt.date:
    return dt.date.fromisoformat(v)


def _dates(start: str, end: str) -> List[str]:
    a, b = _to_date(start), _to_date(end)
    return [(a + dt.timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]


def load_contract(path: str | Path) -> Dict[str, Any]:
    data = _read_json(path)
    if s(data.get("layer_name")) != "multi_shop_business_context_v1":
        raise ValueError("unexpected business context layer")
    if s(data.get("status")) != "PREPRODUCTION":
        raise ValueError("business context contract must remain PREPRODUCTION")
    policy = data.get("source_policy") or {}
    if not bool(policy.get("explicit_source_only")):
        raise ValueError("business context must be explicit-source-only")
    if not bool(policy.get("search_snippet_only_forbidden")):
        raise ValueError("search snippets must not be canonical context evidence")
    if not bool(policy.get("inferred_from_metric_movement_forbidden")):
        raise ValueError("metric-movement inference must remain forbidden")
    safety = data.get("safety") or {}
    if any(bool(safety.get(k)) for k in (
        "enable_alerts", "enable_diagnosis", "infer_campaign_from_metrics",
        "write_production_data_mart", "modify_production_ui",
    )):
        raise ValueError("business context safety contract is not fail-closed")
    return data


def _validate_source(source: Mapping[str, Any], allowed_tiers: set[str]) -> None:
    required = ("source_id", "source_tier", "publisher", "platform", "title", "url", "checked_at")
    for field in required:
        if not s(source.get(field)):
            raise ValueError(f"business context source missing {field}")
    if s(source.get("source_tier")) not in allowed_tiers:
        raise ValueError(f"unsupported source tier: {source.get('source_tier')}")
    if not s(source.get("url")).startswith("https://"):
        raise ValueError(f"source URL must use https: {source.get('source_id')}")


def _validate_event(
    event: Mapping[str, Any],
    *,
    source_map: Mapping[str, Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> None:
    required = (
        "context_id", "label", "platform", "scope_type", "context_type",
        "context_family", "start_date", "end_date", "window_type",
        "source_id", "verification_status",
    )
    for field in required:
        if not s(event.get(field)):
            raise ValueError(f"business context event missing {field}")
    if s(event.get("source_id")) not in source_map:
        raise ValueError(f"event source not found: {event.get('context_id')}")
    if s(event.get("scope_type")) not in set(contract.get("scope_types") or []):
        raise ValueError(f"unsupported scope type: {event.get('context_id')}")
    if s(event.get("context_type")) not in set(contract.get("context_types") or []):
        raise ValueError(f"unsupported context type: {event.get('context_id')}")
    if s(event.get("context_family")) not in set(contract.get("context_families") or []):
        raise ValueError(f"unsupported context family: {event.get('context_id')}")
    start, end = s(event.get("start_date")), s(event.get("end_date"))
    if _to_date(start) > _to_date(end):
        raise ValueError(f"event start after end: {event.get('context_id')}")
    peak_dates = [s(x) for x in event.get("peak_dates") or []]
    if any(d < start or d > end for d in peak_dates):
        raise ValueError(f"peak date outside event window: {event.get('context_id')}")
    source = source_map[s(event.get("source_id"))]
    exact_tiers = set((contract.get("source_policy") or {}).get("exact_date_matching_tiers") or [])
    if bool(event.get("matching_eligible")):
        if not bool(event.get("exact_date_verified")):
            raise ValueError(f"matching-eligible event must have verified exact dates: {event.get('context_id')}")
        if s(source.get("source_tier")) not in exact_tiers:
            raise ValueError(f"matching-eligible event uses non-exact source tier: {event.get('context_id')}")
        if s(source.get("machine_readability")) == "IMAGE_ONLY_FOR_MONTHLY_CALENDAR":
            raise ValueError(f"image-only calendar cannot be auto-matching evidence: {event.get('context_id')}")
    if s(source.get("source_tier")) == "C1_INDUSTRY_ANALYTICS" and bool(event.get("matching_eligible")):
        raise ValueError("industry analytics cannot create exact-date matching context")


def validate_calendar(
    calendar: Mapping[str, Any],
    contract: Mapping[str, Any],
    as_of_period: str = "",
) -> Dict[str, Any]:
    checks = []
    def ck(name: str, ok: bool, detail: Mapping[str, Any] | None = None) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": dict(detail or {})})

    sources = list(calendar.get("sources") or [])
    events = list(calendar.get("events") or [])
    allowed_tiers = set((contract.get("source_policy") or {}).get("allowed_source_tiers") or [])

    source_ids = [s(x.get("source_id")) for x in sources]
    event_ids = [s(x.get("context_id")) for x in events]
    ck("source_ids_unique", len(source_ids) == len(set(source_ids)))
    ck("event_ids_unique", len(event_ids) == len(set(event_ids)))

    refresh=contract.get("refresh_policy") or {}
    review_date=s(calendar.get(s(refresh.get("calendar_review_date_field")) or "checked_at"))
    review_month=review_date[:7] if len(review_date)>=7 else ""
    if as_of_period and bool(refresh.get("block_if_review_month_precedes_as_of_period")):
        ck(
            "calendar_review_covers_as_of_period",
            bool(review_month) and review_month>=as_of_period,
            {"reviewMonth":review_month,"asOfPeriod":as_of_period},
        )

    errors = []
    source_map = {}
    for source in sources:
        try:
            _validate_source(source, allowed_tiers)
            source_map[s(source.get("source_id"))] = source
        except Exception as exc:
            errors.append(str(exc))
    ck("sources_valid", not errors, {"errors": errors[:20]})

    event_errors = []
    if not errors:
        for event in events:
            try:
                _validate_event(event, source_map=source_map, contract=contract)
            except Exception as exc:
                event_errors.append(str(exc))
    ck("events_valid", not event_errors, {"errors": event_errors[:20]})

    canonical_search_snippet = [
        x.get("source_id") for x in sources
        if s(x.get("machine_readability")) == "SEARCH_SNIPPET_ONLY"
    ]
    ck("no_search_snippet_canonical_sources", not canonical_search_snippet, {
        "sourceIds": canonical_search_snippet
    })

    failed = [x for x in checks if x["status"] == "FAIL"]
    return {
        "status": "PASS" if not failed else "FAIL",
        "failedCheckCount": len(failed),
        "checks": checks,
    }


def build_business_context(
    *,
    contract_path: str | Path,
    calendar_path: str | Path,
    as_of_period: str,
    output_dir: str | Path,
) -> Dict[str, Any]:
    contract = load_contract(contract_path)
    calendar = _read_json(calendar_path)
    qa = validate_calendar(calendar, contract, as_of_period=as_of_period)
    if qa["status"] != "PASS":
        raise ValueError(
            f"business context QA failed: {[x['name'] for x in qa['checks'] if x['status']=='FAIL']}"
        )

    source_map = {s(x.get("source_id")): dict(x) for x in calendar.get("sources") or []}
    month_end = (
        (dt.date.fromisoformat(as_of_period + "-01").replace(day=28) + dt.timedelta(days=4))
        .replace(day=1) - dt.timedelta(days=1)
    ).isoformat()

    selected_events = []
    day_rows = []
    for raw in calendar.get("events") or []:
        event = dict(raw)
        if s(event.get("start_date")) > month_end:
            continue
        source = source_map[s(event.get("source_id"))]
        selected_events.append({
            **event,
            "source": {
                "sourceId": s(source.get("source_id")),
                "sourceTier": s(source.get("source_tier")),
                "publisher": s(source.get("publisher")),
                "title": s(source.get("title")),
                "url": s(source.get("url")),
                "publishedAt": s(source.get("published_at")),
                "checkedAt": s(source.get("checked_at")),
                "machineReadability": s(source.get("machine_readability")),
                "evidence": s(source.get("evidence")),
            },
        })
        for d in _dates(s(event.get("start_date")), min(s(event.get("end_date")), month_end)):
            day_rows.append({
                "data_date": d,
                "context_id": s(event.get("context_id")),
                "label": s(event.get("label")),
                "platform": s(event.get("platform")),
                "scope_type": s(event.get("scope_type")),
                "shop_id": s(event.get("shop_id")),
                "context_type": s(event.get("context_type")),
                "context_family": s(event.get("context_family")),
                "window_type": s(event.get("window_type")),
                "is_peak_date": d in set(s(x) for x in event.get("peak_dates") or []),
                "source_id": s(event.get("source_id")),
                "source_tier": s(source.get("source_tier")),
                "verification_status": s(event.get("verification_status")),
                "exact_date_verified": bool(event.get("exact_date_verified")),
                "matching_eligible": bool(event.get("matching_eligible")),
            })

    selected_events.sort(key=lambda x: (x["start_date"], x["platform"], x["context_id"]))
    day_rows.sort(key=lambda x: (
        x["data_date"], x["platform"], x["scope_type"], x["context_id"]
    ))

    fingerprint = _sha256_json({
        "contractVersion": s(contract.get("version")),
        "calendarVersion": s(calendar.get("version")),
        "checkedAt": s(calendar.get("checked_at")),
        "asOfPeriod": as_of_period,
        "sources": [source_map[k] for k in sorted(source_map)],
        "events": selected_events,
        "referenceOnly": calendar.get("reference_only") or [],
    })

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "context_events.json", {
        "meta": {
            "layer": s(contract.get("layer_name")),
            "contractVersion": s(contract.get("version")),
            "calendarVersion": s(calendar.get("version")),
            "status": "PREPRODUCTION",
            "market": s(calendar.get("market")),
            "asOfPeriod": as_of_period,
            "contextBuildFingerprint": fingerprint,
            "explicitSourceOnly": True,
        },
        "sources": [source_map[k] for k in sorted(source_map)],
        "events": selected_events,
        "referenceOnly": list(calendar.get("reference_only") or []),
        "safety": {
            "alertsEnabled": False,
            "diagnosisEnabled": False,
            "campaignInferenceFromMetrics": False,
            "productionDataMartWritten": False,
            "productionUiModified": False,
        },
    })
    _write_jsonl(out / "context_days.jsonl", day_rows)
    qa.update({
        "contextBuildFingerprint": fingerprint,
        "asOfPeriod": as_of_period,
        "selectedEventCount": len(selected_events),
        "contextDayRowCount": len(day_rows),
        "matchingEligibleEventCount": sum(bool(x.get("matching_eligible")) for x in selected_events),
        "explicitSourceOnly": True,
    })
    _write_json(out / "context_qa_report.json", qa)
    _write_json(out / "context_manifest.json", {
        "layer": s(contract.get("layer_name")),
        "contractVersion": s(contract.get("version")),
        "calendarVersion": s(calendar.get("version")),
        "asOfPeriod": as_of_period,
        "contextBuildFingerprint": fingerprint,
        "files": ["context_events.json", "context_days.jsonl", "context_qa_report.json"],
        "sourceCount": len(source_map),
        "eventCount": len(selected_events),
        "safety": {
            "alertsEnabled": False,
            "diagnosisEnabled": False,
            "productionDataMartWritten": False,
            "productionUiModified": False,
        },
    })
    return {
        "status": "PASS",
        "asOfPeriod": as_of_period,
        "contextBuildFingerprint": fingerprint,
        "selectedEventCount": len(selected_events),
        "contextDayRowCount": len(day_rows),
        "matchingEligibleEventCount": sum(bool(x.get("matching_eligible")) for x in selected_events),
        "outputLocation": str(out),
        "safety": {
            "alertsEnabled": False,
            "diagnosisEnabled": False,
            "productionDataMartWritten": False,
            "productionUiModified": False,
        },
    }
