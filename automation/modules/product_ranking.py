"""Pure Product Signal priority ranking.

No Google Sheets, Ads ingestion, diagnosis, or UI dependency.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List


def n(v: Any, default: float = 0.0) -> float:
    try:
        if v in (None,""):
            return default
        x=float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def build_priority(
    *,
    recent_gmv: float,
    previous_gmv: float,
    recent_days: int,
    previous_days: int,
    recent_shop_gmv: float,
    gmv_delta: float,
    persistence_months: int,
    pace_delta: float | None,
    pace_support: float,
    confidence: float,
) -> Dict[str, Any]:
    normalized_previous = n(previous_gmv) * (max(int(recent_days),1) / max(int(previous_days),1))
    impact_value = n(recent_gmv) - normalized_previous
    impact_share = abs(impact_value) / max(n(recent_shop_gmv),1.0)

    impact = min(1.0, impact_share / .05)
    deviation = min(1.0, abs(n(gmv_delta)) / .60)
    tail_component = min(1.0, max(int(persistence_months),0) / 2.0)
    if pace_delta is None:
        persistence = max(.35, tail_component)
    else:
        persistence = min(1.0, .60*tail_component + .40*n(pace_support))
    conf = min(1.0,max(0.0,n(confidence)))

    score = 100.0 * (
        max(impact,1e-9) *
        max(deviation,1e-9) *
        max(persistence,1e-9) *
        max(conf,1e-9)
    ) ** .25

    return {
        "structuralImpactValue":impact_value,
        "structuralImpactShare":impact_share,
        "priorityScore":score,
        "priorityComponents":{
            "impact":impact,
            "deviation":deviation,
            "persistence":persistence,
            "confidence":conf,
        },
    }


def rank_signals(signals: List[Dict[str,Any]]) -> Dict[str,Any]:
    ranked=sorted(
        signals,
        key=lambda x:(
            -n(x.get("priorityScore")),
            -abs(n(x.get("structuralImpactValue"))),
            -n(x.get("confidence")),
        ),
    )
    for idx,row in enumerate(ranked,1):
        row["globalRank"]=idx

    problems=[x for x in ranked if x.get("type")=="Vấn đề"]
    opportunities=[x for x in ranked if x.get("type")=="Cơ hội"]
    for idx,row in enumerate(problems,1):
        row["rankWithinType"]=idx
    for idx,row in enumerate(opportunities,1):
        row["rankWithinType"]=idx

    return {
        "ranked":ranked,
        "problems":problems,
        "opportunities":opportunities,
    }
