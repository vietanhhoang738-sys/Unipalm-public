"""Deterministic source-schema registry and drift guard.

Rules:
- exact alias matching after conservative normalization only;
- no fuzzy matching;
- unknown/additional columns are WARN;
- missing required fields or ambiguous duplicate aliases are FAIL;
- header order does not affect schema fingerprint.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

DEFAULT_REGISTRY_PATH=Path(__file__).resolve().parents[2]/"config"/"source_schema_registry.json"


class SchemaContractError(ValueError):
    def __init__(self,message:str,audit:Dict[str,Any]|None=None):
        super().__init__(message)
        self.audit=dict(audit or {})


def normalize_header(value:Any)->str:
    raw="" if value is None else str(value)
    raw=raw.replace("\ufeff","")
    raw=unicodedata.normalize("NFC",raw)
    raw=re.sub(r"\s+"," ",raw.strip())
    return raw


@lru_cache(maxsize=8)
def load_schema_registry(path:str="")->Dict[str,Any]:
    p=Path(path) if path else DEFAULT_REGISTRY_PATH
    data=json.loads(p.read_text(encoding="utf-8"))
    contracts=data.get("contracts")
    if not isinstance(contracts,dict) or not contracts:
        raise ValueError("source schema registry has no contracts")
    return data


def get_contract(name:str,path:str="")->Dict[str,Any]:
    registry=load_schema_registry(path)
    contract=(registry.get("contracts") or {}).get(name)
    if not isinstance(contract,dict):
        raise KeyError(f"schema contract not found: {name}")
    return contract


def aliases_for(name:str,path:str="")->Dict[str,Tuple[str,...]]:
    contract=get_contract(name,path)
    out={}
    for canonical,spec in (contract.get("fields") or {}).items():
        aliases=tuple(str(x) for x in (spec.get("aliases") or []) if str(x).strip())
        if not aliases:
            raise ValueError(f"{name}.{canonical}: aliases must be non-empty")
        out[str(canonical)]=aliases
    return out


def required_fields(name:str,path:str="")->Tuple[str,...]:
    return tuple(str(x) for x in (get_contract(name,path).get("required") or []))


def header_fingerprint(headers:Sequence[Any])->str:
    # Sort so simple column reordering does not produce drift.
    normalized=sorted(normalize_header(x) for x in headers if normalize_header(x))
    payload=json.dumps(normalized,ensure_ascii=False,separators=(",",":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _alias_index(contract:Mapping[str,Any], *, folded:bool=False)->Dict[str,List[str]]:
    index={}
    for canonical,spec in (contract.get("fields") or {}).items():
        for alias in spec.get("aliases") or []:
            key=normalize_header(alias)
            if folded:
                key=key.casefold()
            index.setdefault(key,[]).append(str(canonical))
    return index


def canonical_for_header(name:str,header:Any,path:str="")->str:
    contract=get_contract(name,path)
    key=normalize_header(header)
    exact=_alias_index(contract).get(key,[])
    if len(exact)==1:
        return exact[0]
    folded=_alias_index(contract,folded=True).get(key.casefold(),[])
    return folded[0] if len(set(folded))==1 else ""


def audit_schema(
    name:str,
    headers:Sequence[Any],
    *,
    source_name:str="",
    path:str="",
)->Dict[str,Any]:
    contract=get_contract(name,path)
    required=set(str(x) for x in (contract.get("required") or []))
    alias_index=_alias_index(contract)
    folded_alias_index=_alias_index(contract,folded=True)
    ignored_exact={normalize_header(x) for x in (contract.get("known_ignored_headers") or [])}
    ignored_folded={x.casefold() for x in ignored_exact}

    raw_headers=[str(x).strip() for x in headers if str(x or "").strip()]
    normalized=[normalize_header(x) for x in raw_headers]

    resolved={}
    ambiguous_alias_definitions=[]
    duplicate_canonical_fields=[]
    unknown=[]

    # Registry itself must not define one alias for multiple canonicals.
    for key,canonicals in alias_index.items():
        if len(set(canonicals))>1:
            ambiguous_alias_definitions.append({
                "normalized_alias":key,
                "canonicals":sorted(set(canonicals)),
            })

    for raw,key in zip(raw_headers,normalized):
        canonicals=alias_index.get(key,[])
        if not canonicals:
            folded=folded_alias_index.get(key.casefold(),[])
            canonicals=list(dict.fromkeys(folded)) if len(set(folded))==1 else []
        if len(canonicals)==1:
            canonical=canonicals[0]
            if canonical in resolved:
                duplicate_canonical_fields.append({
                    "canonical":canonical,
                    "headers":[resolved[canonical],raw],
                })
            else:
                resolved[canonical]=raw
        elif not canonicals:
            if key not in ignored_exact and key.casefold() not in ignored_folded:
                unknown.append(raw)

    missing_required=sorted(required-set(resolved))
    optional=set((contract.get("fields") or {}).keys())-required
    missing_optional=sorted(optional-set(resolved))

    fingerprint=header_fingerprint(raw_headers)
    accepted=set(str(x) for x in (contract.get("accepted_fingerprints") or []))
    fingerprint_known=fingerprint in accepted if accepted else False
    fingerprint_state="KNOWN" if fingerprint_known else ("UNBASELINED" if not accepted else "NEW")

    errors=[]
    warnings=[]
    if ambiguous_alias_definitions:
        errors.append("registry_alias_collision")
    if duplicate_canonical_fields:
        errors.append("duplicate_canonical_field")
    if missing_required:
        errors.append("missing_required_fields")
    if unknown:
        warnings.append("unknown_columns")
    if fingerprint_state!="KNOWN":
        warnings.append("schema_fingerprint_"+fingerprint_state.lower())

    status="FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "contract":name,
        "contract_version":str(load_schema_registry(path).get("version","")),
        "source_name":source_name,
        "status":status,
        "fingerprint":fingerprint,
        "fingerprint_state":fingerprint_state,
        "header_count":len(raw_headers),
        "resolved_fields":resolved,
        "resolved_canonical_count":len(resolved),
        "missing_required_fields":missing_required,
        "missing_optional_fields":missing_optional,
        "unknown_columns":unknown,
        "duplicate_canonical_fields":duplicate_canonical_fields,
        "registry_alias_collisions":ambiguous_alias_definitions,
        "errors":errors,
        "warnings":warnings,
    }


def require_schema(
    name:str,
    headers:Sequence[Any],
    *,
    source_name:str="",
    path:str="",
)->Dict[str,Any]:
    audit=audit_schema(name,headers,source_name=source_name,path=path)
    if audit["status"]=="FAIL":
        raise SchemaContractError(
            f"Schema drift blocked {source_name or name}: "
            f"missing_required={audit['missing_required_fields']} "
            f"duplicate_canonical={audit['duplicate_canonical_fields']} "
            f"registry_collisions={audit['registry_alias_collisions']}",
            audit=audit,
        )
    return audit


def summarize_schema_audits(audits:Iterable[Mapping[str,Any]])->Dict[str,Any]:
    rows=[dict(x) for x in audits]
    status_counts={"PASS":0,"WARN":0,"FAIL":0}
    new_fingerprints=[]
    unknown_columns=[]
    failures=[]
    for row in rows:
        status=str(row.get("status") or "")
        if status in status_counts:
            status_counts[status]+=1
        if str(row.get("fingerprint_state")) in {"NEW","UNBASELINED"}:
            new_fingerprints.append({
                "contract":row.get("contract"),
                "source_name":row.get("source_name"),
                "fingerprint":row.get("fingerprint"),
                "state":row.get("fingerprint_state"),
            })
        if row.get("unknown_columns"):
            unknown_columns.append({
                "contract":row.get("contract"),
                "source_name":row.get("source_name"),
                "columns":row.get("unknown_columns"),
            })
        if status=="FAIL":
            failures.append({
                "contract":row.get("contract"),
                "source_name":row.get("source_name"),
                "errors":row.get("errors"),
                "missing_required_fields":row.get("missing_required_fields"),
            })
    overall="FAIL" if status_counts["FAIL"] else ("WARN" if status_counts["WARN"] else "PASS")
    return {
        "status":overall,
        "audit_count":len(rows),
        "status_counts":status_counts,
        "new_or_unbaselined_fingerprints":new_fingerprints,
        "unknown_columns":unknown_columns,
        "failures":failures,
    }
