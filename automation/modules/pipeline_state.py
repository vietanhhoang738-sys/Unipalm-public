"""Generic N-shop control-plane state contracts.

This module is intentionally storage-agnostic. It defines the minimum identity
and validation rules for future processed/control state without touching the
current legacy Control Center or production Data Mart.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Mapping, Tuple

VALID_STATES={"PENDING","RUNNING","READY","FAILED","BLOCKED","SKIPPED"}
VALID_SEVERITIES={"INFO","WARNING","ERROR"}


def _s(v:Any)->str:
    return "" if v is None else str(v).strip()


@dataclass(frozen=True)
class PipelineStateKey:
    shop_id:str
    source_domain:str
    period:str

    def validate(self)->"PipelineStateKey":
        if not _s(self.shop_id):
            raise ValueError("pipeline state key missing shop_id")
        if not _s(self.source_domain):
            raise ValueError("pipeline state key missing source_domain")
        if not _s(self.period):
            raise ValueError("pipeline state key missing period")
        return self

    def as_tuple(self)->Tuple[str,str,str]:
        self.validate()
        return (_s(self.shop_id),_s(self.source_domain),_s(self.period))


@dataclass
class PipelineState:
    shop_id:str
    source_domain:str
    period:str
    state:str
    run_id:str=""
    pipeline_version:str=""
    source_version:str=""
    verified_through:str=""
    dq_error:int=0
    dq_warning:int=0
    production_updated:bool=False
    output_location:str=""
    started_at:str=""
    finished_at:str=""
    error_stage:str=""
    error_message:str=""

    @property
    def key(self)->PipelineStateKey:
        return PipelineStateKey(self.shop_id,self.source_domain,self.period)

    def validate(self)->"PipelineState":
        self.key.validate()
        state=_s(self.state).upper()
        if state not in VALID_STATES:
            raise ValueError(f"invalid pipeline state {self.state!r}")
        self.state=state
        self.dq_error=int(self.dq_error or 0)
        self.dq_warning=int(self.dq_warning or 0)
        if self.dq_error<0 or self.dq_warning<0:
            raise ValueError("DQ counts cannot be negative")
        if self.state=="READY":
            if self.dq_error!=0:
                raise ValueError("READY state cannot have dq_error > 0")
            if not self.run_id:
                raise ValueError("READY state requires run_id")
        return self

    def to_dict(self)->Dict[str,Any]:
        self.validate()
        return asdict(self)


def validate_state_rows(rows:Iterable[Mapping[str,Any]])->Dict[str,Any]:
    """Validate arbitrary-shop control-plane rows.

    Unique grain is shop_id + source_domain + period. The same domain/period may
    appear for any number of shops without conflict.
    """
    seen=set()
    duplicates=[]
    invalid=[]
    states=[]
    for idx,row in enumerate(rows):
        try:
            state=PipelineState(
                shop_id=_s(row.get("shop_id")),
                source_domain=_s(row.get("source_domain")),
                period=_s(row.get("period")),
                state=_s(row.get("state")),
                run_id=_s(row.get("run_id")),
                pipeline_version=_s(row.get("pipeline_version")),
                source_version=_s(row.get("source_version")),
                verified_through=_s(row.get("verified_through")),
                dq_error=int(row.get("dq_error") or 0),
                dq_warning=int(row.get("dq_warning") or 0),
                production_updated=bool(row.get("production_updated",False)),
                output_location=_s(row.get("output_location")),
                started_at=_s(row.get("started_at")),
                finished_at=_s(row.get("finished_at")),
                error_stage=_s(row.get("error_stage")),
                error_message=_s(row.get("error_message")),
            ).validate()
            key=state.key.as_tuple()
            if key in seen:
                duplicates.append({"index":idx,"key":key})
            seen.add(key)
            states.append(state)
        except Exception as exc:
            invalid.append({"index":idx,"error":str(exc)})

    return {
        "status":"PASS" if not duplicates and not invalid else "FAIL",
        "row_count":len(states)+len(invalid),
        "valid_row_count":len(states),
        "duplicate_count":len(duplicates),
        "invalid_count":len(invalid),
        "duplicates":duplicates,
        "invalid":invalid,
        "shop_count":len({x.shop_id for x in states}),
        "domains":sorted({x.source_domain for x in states}),
        "periods":sorted({x.period for x in states}),
    }


def aggregate_shop_readiness(rows:Iterable[Mapping[str,Any]],required_domains:Iterable[str])->List[Dict[str,Any]]:
    """Summarize readiness independently by shop + period.

    This never treats one shop's failure as another shop's failure.
    """
    required=tuple(dict.fromkeys(_s(x) for x in required_domains if _s(x)))
    state_by_key={}
    for row in rows:
        state=PipelineState(
            shop_id=_s(row.get("shop_id")),
            source_domain=_s(row.get("source_domain")),
            period=_s(row.get("period")),
            state=_s(row.get("state")),
            run_id=_s(row.get("run_id")),
            dq_error=int(row.get("dq_error") or 0),
            dq_warning=int(row.get("dq_warning") or 0),
            production_updated=bool(row.get("production_updated",False)),
        ).validate()
        key=state.key.as_tuple()
        if key in state_by_key:
            raise ValueError(f"duplicate control-plane key {key}")
        state_by_key[key]=state

    scopes=sorted({(shop,period) for shop,_,period in state_by_key})
    out=[]
    for shop_id,period in scopes:
        domain_status={}
        blockers=[]
        for domain in required:
            state=state_by_key.get((shop_id,domain,period))
            if state is None:
                domain_status[domain]="MISSING"
                blockers.append(domain)
            else:
                domain_status[domain]=state.state
                if state.state!="READY":
                    blockers.append(domain)
        out.append({
            "shop_id":shop_id,
            "period":period,
            "status":"READY" if not blockers else "BLOCKED",
            "required_domains":list(required),
            "domain_status":domain_status,
            "blocking_domains":blockers,
        })
    return out
