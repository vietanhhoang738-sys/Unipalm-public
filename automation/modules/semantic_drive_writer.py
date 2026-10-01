"""Atomic Drive publisher for portfolio-level semantic v2 partitions."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .drive_partition_writer import (
    _create_folder,
    _ensure_nested_folder,
    _folders_named,
    _trash,
    _update_folder,
    _upload_file_verified,
    md5_file,
    sha256_file,
    upload_control_file,
)


def _s(v:Any)->str:
    return "" if v is None else str(v).strip()


def load_semantic_storage_registry(path:str|Path)->Dict[str,Any]:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    cfg=data.get("semantic_v2") or {}
    if cfg.get("status")!="PREPRODUCTION":
        raise ValueError("semantic_v2 storage must be PREPRODUCTION")
    root=_s(cfg.get("drive_root_id"))
    if not root:
        raise ValueError("semantic_v2 drive_root_id is required")
    forbidden={_s(x) for x in cfg.get("forbidden_drive_root_ids") or [] if _s(x)}
    if root in forbidden:
        raise ValueError("semantic_v2 drive root is explicitly forbidden")
    policy=cfg.get("writer_policy") or {}
    for key in ("write_legacy_data_mart","write_production_data_mart","write_ui"):
        if bool(policy.get(key)):
            raise ValueError(f"unsafe semantic_v2 writer policy: {key}=true")
    if _s(policy.get("publish_mode"))!="atomic_partition_swap":
        raise ValueError("semantic_v2 writer requires atomic_partition_swap mode")
    return data


def validate_local_semantic_partition(
    semantic_dir:str|Path,
    *,
    expected_period:str,
    expected_shop_ids:set[str],
)->Dict[str,Any]:
    semantic_dir=Path(semantic_dir)
    manifest_path=semantic_dir/"manifest.json"
    qa_path=semantic_dir/"semantic_qa_report.json"
    if not manifest_path.exists() or not qa_path.exists():
        raise FileNotFoundError("semantic partition missing manifest.json or semantic_qa_report.json")

    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    qa=json.loads(qa_path.read_text(encoding="utf-8"))
    if _s(manifest.get("period"))!=expected_period or _s(qa.get("period"))!=expected_period:
        raise ValueError("semantic period mismatch")
    if qa.get("status")!="PASS" or not bool(qa.get("semantic_mart_ready")):
        raise ValueError("semantic QA is not PASS/ready")
    fingerprint=_s(manifest.get("semantic_build_fingerprint"))
    if not fingerprint or fingerprint!=_s(qa.get("semantic_build_fingerprint")):
        raise ValueError("semantic fingerprint mismatch")

    safety=manifest.get("safety") or {}
    if any(bool(safety.get(x)) for x in (
        "legacy_data_mart_written","production_data_mart_written","ui_modified"
    )):
        raise ValueError("semantic safety boundary violated")

    qa_shop_ids={_s(x) for x in qa.get("selected_shop_ids") or [] if _s(x)}
    source_shop_ids={
        _s(x.get("shop_id")) for x in manifest.get("source_partitions") or []
        if _s(x.get("shop_id"))
    }
    if qa_shop_ids!=expected_shop_ids or source_shop_ids!=expected_shop_ids:
        raise ValueError(
            f"semantic portfolio scope mismatch qa={sorted(qa_shop_ids)} "
            f"sources={sorted(source_shop_ids)} expected={sorted(expected_shop_ids)}"
        )
    if int(qa.get("selected_shop_count") or 0)!=len(expected_shop_ids):
        raise ValueError("semantic selected_shop_count mismatch")

    listed={}
    for item in manifest.get("files") or []:
        rel=_s(item.get("file"))
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            raise ValueError(f"unsafe semantic file path: {rel!r}")
        p=semantic_dir/rel
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"semantic mart missing: {rel}")
        actual=sha256_file(p)
        if actual!=_s(item.get("sha256")):
            raise ValueError(f"semantic mart sha256 mismatch: {rel}")
        listed[rel]=actual

    all_files=[]
    for p in sorted(semantic_dir.rglob("*")):
        if p.is_symlink():
            raise ValueError(f"symlink is not allowed in semantic partition: {p}")
        if p.is_file():
            all_files.append({
                "relative_path":p.relative_to(semantic_dir).as_posix(),
                "path":p,
                "size":p.stat().st_size,
                "md5":md5_file(p),
                "sha256":sha256_file(p),
            })
    if not all_files:
        raise ValueError("semantic partition has no files")

    return {
        "period":expected_period,
        "semantic_build_fingerprint":fingerprint,
        "selected_shop_ids":sorted(expected_shop_ids),
        "selected_shop_count":len(expected_shop_ids),
        "manifest":manifest,
        "qa":qa,
        "files":all_files,
        "mart_file_count":len(listed),
    }


def _is_managed_semantic_partition(folder:Mapping[str,Any],period:str)->bool:
    props=folder.get("appProperties") or {}
    return (
        _s(props.get("layer"))=="semantic_v2"
        and _s(props.get("kind"))=="portfolio_partition"
        and _s(props.get("period"))==period
    )


def publish_semantic_partition_atomic(
    drive,
    *,
    storage_cfg:Mapping[str,Any],
    semantic_dir:str|Path,
    period:str,
    expected_shop_ids:set[str],
    run_id:str,
)->Dict[str,Any]:
    local=validate_local_semantic_partition(
        semantic_dir,expected_period=period,expected_shop_ids=expected_shop_ids)
    cfg=storage_cfg.get("semantic_v2") or {}
    root_id=_s(cfg.get("drive_root_id"))
    forbidden={_s(x) for x in cfg.get("forbidden_drive_root_ids") or []}
    if not root_id or root_id in forbidden:
        raise ValueError("unsafe semantic_v2 root")

    existing=_folders_named(drive,root_id,period)
    if len(existing)>1:
        raise ValueError(f"semantic/{period}: multiple active partitions found")
    current=existing[0] if existing else None
    if current:
        if not _is_managed_semantic_partition(current,period):
            raise ValueError(f"semantic/{period}: existing partition is unmanaged")
        current_fp=_s((current.get("appProperties") or {}).get("buildFingerprint"))
        if current_fp==local["semantic_build_fingerprint"]:
            return {
                "status":"NOOP",
                "period":period,
                "semantic_build_fingerprint":local["semantic_build_fingerprint"],
                "drive_folder_id":current["id"],
                "uploaded_file_count":0,
                "reason":"same_build_fingerprint",
            }

    temp=_create_folder(
        drive,
        parent_id=root_id,
        name=f".tmp_{period}_{run_id}_{uuid.uuid4().hex[:8]}",
        app_properties={
            "layer":"semantic_v2",
            "kind":"portfolio_partition",
            "period":period,
            "buildFingerprint":local["semantic_build_fingerprint"],
            "writerRunId":run_id,
            "status":"UPLOADING",
            "shopCount":str(local["selected_shop_count"]),
        },
    )
    temp_id=temp["id"]
    backup=None
    uploaded=[]
    try:
        cache={}
        for item in local["files"]:
            rel=Path(item["relative_path"])
            parent=_ensure_nested_folder(
                drive,root_folder_id=temp_id,relative_parent=rel.parent,cache=cache)
            remote=_upload_file_verified(
                drive,
                local_path=item["path"],
                parent_id=parent,
                file_name=rel.name,
                expected_md5=item["md5"],
                expected_size=item["size"],
                build_fingerprint=local["semantic_build_fingerprint"],
            )
            uploaded.append({
                "relative_path":item["relative_path"],
                "drive_file_id":remote["id"],
                "size":item["size"],
                "md5":item["md5"],
            })

        ready_props={
            "layer":"semantic_v2",
            "kind":"portfolio_partition",
            "period":period,
            "buildFingerprint":local["semantic_build_fingerprint"],
            "writerRunId":run_id,
            "status":"READY",
            "fileCount":str(len(uploaded)),
            "shopCount":str(local["selected_shop_count"]),
        }
        _update_folder(drive,temp_id,app_properties=ready_props)

        if current:
            backup=_update_folder(
                drive,current["id"],
                name=f".backup_{period}_{run_id}_{uuid.uuid4().hex[:8]}",
                app_properties={
                    **(current.get("appProperties") or {}),
                    "status":"SUPERSEDED_PENDING_SWAP",
                    "supersededBy":local["semantic_build_fingerprint"],
                },
            )
        try:
            activated=_update_folder(drive,temp_id,name=period,app_properties=ready_props)
        except Exception:
            if backup:
                _update_folder(
                    drive,backup["id"],name=period,
                    app_properties={**(current.get("appProperties") or {}),"status":"READY"},
                )
            raise

        if backup:
            _trash(drive,backup["id"])

        return {
            "status":"PUBLISHED",
            "period":period,
            "semantic_build_fingerprint":local["semantic_build_fingerprint"],
            "drive_folder_id":activated["id"],
            "uploaded_file_count":len(uploaded),
            "uploaded_files":uploaded,
            "previous_partition_replaced":bool(current),
            "selected_shop_count":local["selected_shop_count"],
        }
    except Exception:
        try:
            state=drive.files().get(
                fileId=temp_id,fields="id,name,trashed",supportsAllDrives=True).execute()
            if not state.get("trashed") and state.get("name")!=period:
                _trash(drive,temp_id)
        except Exception:
            pass
        raise
