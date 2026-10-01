"""Atomic Google Drive writer for pre-production processed v2 partitions.

This writer only targets the configured PREPRODUCTION processed_v2 root.
It never writes legacy processed storage, production Data Mart, or UI.

Write algorithm for one shop/month:
1. validate local processed candidate + manifest hashes;
2. detect existing managed partition;
3. same build_fingerprint => NOOP;
4. upload entire candidate into a temporary Drive folder;
5. verify each uploaded file by size + md5Checksum;
6. mark temporary folder READY;
7. rename current managed partition to backup;
8. rename temporary folder to the canonical period name;
9. trash backup only after the new partition is active.

A failure before step 8 leaves the current partition untouched. A failure during
swap attempts to restore the previous partition.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from googleapiclient.http import MediaFileUpload


FOLDER_MIME="application/vnd.google-apps.folder"


def _s(v:Any)->str:
    return "" if v is None else str(v).strip()


def load_storage_registry(path:str|Path)->Dict[str,Any]:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    cfg=data.get("processed_v2") or {}
    if cfg.get("status")!="PREPRODUCTION":
        raise ValueError("processed_v2 storage must be PREPRODUCTION for this writer")
    root=_s(cfg.get("drive_root_id"))
    if not root:
        raise ValueError("processed_v2 drive_root_id is required")
    forbidden={_s(x) for x in cfg.get("forbidden_drive_root_ids") or [] if _s(x)}
    if root in forbidden:
        raise ValueError("processed_v2 drive root is explicitly forbidden")
    policy=cfg.get("writer_policy") or {}
    for key in ("write_legacy_processed","write_production_data_mart","write_ui"):
        if bool(policy.get(key)):
            raise ValueError(f"unsafe processed_v2 writer policy: {key}=true")
    if _s(policy.get("publish_mode"))!="atomic_partition_swap":
        raise ValueError("processed_v2 writer requires atomic_partition_swap mode")
    return data


def retry_idempotent_drive_operation(
    operation,
    *,
    attempts:int=3,
    base_delay_seconds:float=1.0,
):
    """Retry an idempotent/atomic Drive operation after transient client errors.

    The caller must supply an operation that is safe to rerun. Processed and
    Semantic publishers satisfy this because an activated fingerprint becomes
    a NOOP on the next attempt, while pre-activation failures keep the previous
    canonical partition intact.
    """
    attempts=max(1,int(attempts))
    last_exc=None
    for attempt in range(1,attempts+1):
        try:
            return operation()
        except Exception as exc:
            last_exc=exc
            if attempt>=attempts:
                raise
            if base_delay_seconds>0:
                time.sleep(base_delay_seconds*attempt)
    raise last_exc  # pragma: no cover


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path:Path)->str:
    h=hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def validate_local_partition(
    partition_dir:str|Path,
    *,
    expected_shop_key:str,
    expected_period:str,
)->Dict[str,Any]:
    """Validate processed candidate before any Drive mutation."""
    partition_dir=Path(partition_dir)
    manifest_path=partition_dir/"manifest.json"
    qa_path=partition_dir/"processed_qa_report.json"
    state_path=partition_dir/"control"/"pipeline_state.jsonl"
    for p in (manifest_path,qa_path,state_path):
        if not p.exists():
            raise FileNotFoundError(f"processed partition missing {p.relative_to(partition_dir)}")

    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    qa=json.loads(qa_path.read_text(encoding="utf-8"))
    if _s(manifest.get("shop_key"))!=expected_shop_key:
        raise ValueError("processed manifest shop_key mismatch")
    if _s(manifest.get("period"))!=expected_period:
        raise ValueError("processed manifest period mismatch")
    if qa.get("status")!="PASS" or not bool(qa.get("processed_partition_ready")):
        raise ValueError("processed QA is not PASS/ready")
    if _s(qa.get("shop_key"))!=expected_shop_key or _s(qa.get("period"))!=expected_period:
        raise ValueError("processed QA scope mismatch")
    fingerprint=_s(manifest.get("build_fingerprint"))
    if not fingerprint or fingerprint!=_s(qa.get("build_fingerprint")):
        raise ValueError("processed build_fingerprint mismatch")
    safety=manifest.get("safety") or {}
    if any(bool(safety.get(x)) for x in (
        "legacy_processed_written","production_data_mart_written","ui_modified"
    )):
        raise ValueError("processed manifest safety boundary violated")

    listed={}
    for item in manifest.get("files") or []:
        rel=_s(item.get("target"))
        if not rel:
            raise ValueError("manifest file target is blank")
        if rel.startswith("/") or ".." in Path(rel).parts:
            raise ValueError(f"unsafe manifest relative path: {rel}")
        p=partition_dir/rel
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"manifest file missing: {rel}")
        actual_sha=sha256_file(p)
        expected_sha=_s(item.get("sha256"))
        if not expected_sha or actual_sha!=expected_sha:
            raise ValueError(f"manifest sha256 mismatch: {rel}")
        listed[rel]=actual_sha

    state_rows=[]
    for line_no,line in enumerate(state_path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip():
            continue
        row=json.loads(line)
        if _s(row.get("shop_id"))!=_s(manifest.get("shop_id")):
            raise ValueError(f"control state line {line_no}: shop_id mismatch")
        if _s(row.get("period"))!=expected_period:
            raise ValueError(f"control state line {line_no}: period mismatch")
        if bool(row.get("production_updated")):
            raise ValueError(f"control state line {line_no}: production_updated must remain false")
        state_rows.append(row)
    if not state_rows:
        raise ValueError("processed partition has no control state rows")

    all_files=[]
    for p in sorted(partition_dir.rglob("*")):
        if p.is_symlink():
            raise ValueError(f"symlink is not allowed in processed partition: {p}")
        if p.is_file():
            rel=p.relative_to(partition_dir).as_posix()
            all_files.append({
                "relative_path":rel,
                "path":p,
                "size":p.stat().st_size,
                "sha256":sha256_file(p),
                "md5":md5_file(p),
            })

    return {
        "shop_key":expected_shop_key,
        "shop_id":_s(manifest.get("shop_id")),
        "period":expected_period,
        "build_fingerprint":fingerprint,
        "manifest":manifest,
        "qa":qa,
        "manifest_business_files":listed,
        "control_state_count":len(state_rows),
        "files":all_files,
    }


def _list_children(drive,parent_id:str,name:str="")->List[Dict[str,Any]]:
    q=f"'{parent_id}' in parents and trashed=false"
    if name:
        safe=name.replace("'","\\'")
        q+=f" and name='{safe}'"
    out=[]; token=None
    while True:
        res=drive.files().list(
            q=q,
            fields="nextPageToken,files(id,name,mimeType,size,md5Checksum,appProperties,createdTime,modifiedTime)",
            pageSize=1000,
            pageToken=token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        out.extend(res.get("files") or [])
        token=res.get("nextPageToken")
        if not token:
            return out


def _folders_named(drive,parent_id:str,name:str)->List[Dict[str,Any]]:
    return [x for x in _list_children(drive,parent_id,name)
            if x.get("mimeType")==FOLDER_MIME]


def _create_folder(
    drive,
    *,
    parent_id:str,
    name:str,
    app_properties:Optional[Mapping[str,str]]=None,
)->Dict[str,Any]:
    body={
        "name":name,
        "mimeType":FOLDER_MIME,
        "parents":[parent_id],
    }
    if app_properties:
        body["appProperties"]={str(k):str(v) for k,v in app_properties.items()}
    return drive.files().create(
        body=body,
        fields="id,name,mimeType,appProperties",
        supportsAllDrives=True,
    ).execute()


def ensure_managed_shop_folder(drive,root_id:str,shop_key:str)->Dict[str,Any]:
    matches=_folders_named(drive,root_id,shop_key)
    if len(matches)>1:
        raise ValueError(f"{shop_key}: multiple Drive shop folders found")
    if matches:
        return matches[0]
    return _create_folder(
        drive,parent_id=root_id,name=shop_key,
        app_properties={"layer":"processed_v2","shopKey":shop_key,"kind":"shop"},
    )


def _trash(drive,file_id:str)->None:
    drive.files().update(
        fileId=file_id,
        body={"trashed":True},
        fields="id,trashed",
        supportsAllDrives=True,
    ).execute()


def _update_folder(drive,file_id:str,*,name:str="",app_properties:Optional[Mapping[str,str]]=None)->Dict[str,Any]:
    body={}
    if name:
        body["name"]=name
    if app_properties is not None:
        body["appProperties"]={str(k):str(v) for k,v in app_properties.items()}
    return drive.files().update(
        fileId=file_id,
        body=body,
        fields="id,name,appProperties",
        supportsAllDrives=True,
    ).execute()


def _ensure_nested_folder(
    drive,
    *,
    root_folder_id:str,
    relative_parent:Path,
    cache:Dict[str,str],
)->str:
    current=root_folder_id
    built=[]
    for part in relative_parent.parts:
        if part in ("","."):
            continue
        built.append(part)
        key="/".join(built)
        if key in cache:
            current=cache[key]
            continue
        matches=_folders_named(drive,current,part)
        if len(matches)>1:
            raise ValueError(f"multiple folders found while publishing: {key}")
        folder=matches[0] if matches else _create_folder(
            drive,parent_id=current,name=part,
            app_properties={"layer":"processed_v2","kind":"directory"},
        )
        current=folder["id"]
        cache[key]=current
    return current


def _upload_file_verified(
    drive,
    *,
    local_path:Path,
    parent_id:str,
    file_name:str,
    expected_md5:str,
    expected_size:int,
    build_fingerprint:str,
)->Dict[str,Any]:
    mime=mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    media=MediaFileUpload(str(local_path),mimetype=mime,resumable=False)
    created=drive.files().create(
        body={
            "name":file_name,
            "parents":[parent_id],
            "appProperties":{
                "layer":"processed_v2",
                "buildFingerprint":build_fingerprint,
                "sha256":sha256_file(local_path),
            },
        },
        media_body=media,
        fields="id,name,size,md5Checksum,appProperties",
        supportsAllDrives=True,
    ).execute()
    remote_size=int(created.get("size") or -1)
    remote_md5=_s(created.get("md5Checksum"))
    if remote_size!=int(expected_size) or remote_md5!=expected_md5:
        try:
            _trash(drive,created["id"])
        finally:
            raise RuntimeError(
                f"Drive upload verification failed for {file_name}: "
                f"size {remote_size}!={expected_size} or md5 {remote_md5}!={expected_md5}"
            )
    return created


def _is_managed_partition(folder:Mapping[str,Any],*,shop_key:str,period:str)->bool:
    props=folder.get("appProperties") or {}
    return (
        _s(props.get("layer"))=="processed_v2"
        and _s(props.get("kind"))=="partition"
        and _s(props.get("shopKey"))==shop_key
        and _s(props.get("period"))==period
    )


def publish_partition_atomic(
    drive,
    *,
    storage_cfg:Mapping[str,Any],
    partition_dir:str|Path,
    shop_key:str,
    period:str,
    run_id:str,
)->Dict[str,Any]:
    local=validate_local_partition(
        partition_dir,expected_shop_key=shop_key,expected_period=period)
    processed_cfg=storage_cfg.get("processed_v2") or {}
    root_id=_s(processed_cfg.get("drive_root_id"))
    forbidden={_s(x) for x in processed_cfg.get("forbidden_drive_root_ids") or []}
    if not root_id or root_id in forbidden:
        raise ValueError("unsafe processed_v2 root")

    shop_folder=ensure_managed_shop_folder(drive,root_id,shop_key)
    existing=_folders_named(drive,shop_folder["id"],period)
    if len(existing)>1:
        raise ValueError(f"{shop_key}/{period}: multiple active partition folders")
    current=existing[0] if existing else None
    if current:
        if not _is_managed_partition(current,shop_key=shop_key,period=period):
            raise ValueError(
                f"{shop_key}/{period}: existing partition is unmanaged; refusing overwrite")
        current_fp=_s((current.get("appProperties") or {}).get("buildFingerprint"))
        if current_fp==local["build_fingerprint"]:
            return {
                "status":"NOOP",
                "shop_key":shop_key,
                "shop_id":local["shop_id"],
                "period":period,
                "build_fingerprint":local["build_fingerprint"],
                "drive_folder_id":current["id"],
                "uploaded_file_count":0,
                "reason":"same_build_fingerprint",
            }

    temp_name=f".tmp_{period}_{run_id}_{uuid.uuid4().hex[:8]}"
    temp=_create_folder(
        drive,
        parent_id=shop_folder["id"],
        name=temp_name,
        app_properties={
            "layer":"processed_v2",
            "kind":"partition",
            "shopKey":shop_key,
            "period":period,
            "buildFingerprint":local["build_fingerprint"],
            "writerRunId":run_id,
            "status":"UPLOADING",
        },
    )
    temp_id=temp["id"]
    uploaded=[]
    backup=None
    try:
        cache={}
        for item in local["files"]:
            rel=Path(item["relative_path"])
            parent=_ensure_nested_folder(
                drive,
                root_folder_id=temp_id,
                relative_parent=rel.parent,
                cache=cache,
            )
            remote=_upload_file_verified(
                drive,
                local_path=item["path"],
                parent_id=parent,
                file_name=rel.name,
                expected_md5=item["md5"],
                expected_size=item["size"],
                build_fingerprint=local["build_fingerprint"],
            )
            uploaded.append({
                "relative_path":item["relative_path"],
                "drive_file_id":remote["id"],
                "size":item["size"],
                "md5":item["md5"],
            })

        _update_folder(
            drive,temp_id,
            app_properties={
                "layer":"processed_v2",
                "kind":"partition",
                "shopKey":shop_key,
                "period":period,
                "buildFingerprint":local["build_fingerprint"],
                "writerRunId":run_id,
                "status":"READY",
                "fileCount":str(len(uploaded)),
            },
        )

        if current:
            backup_name=f".backup_{period}_{run_id}_{uuid.uuid4().hex[:8]}"
            backup=_update_folder(
                drive,current["id"],name=backup_name,
                app_properties={
                    **(current.get("appProperties") or {}),
                    "status":"SUPERSEDED_PENDING_SWAP",
                    "supersededBy":local["build_fingerprint"],
                },
            )

        try:
            activated=_update_folder(
                drive,temp_id,name=period,
                app_properties={
                    "layer":"processed_v2",
                    "kind":"partition",
                    "shopKey":shop_key,
                    "period":period,
                    "buildFingerprint":local["build_fingerprint"],
                    "writerRunId":run_id,
                    "status":"READY",
                    "fileCount":str(len(uploaded)),
                },
            )
        except Exception:
            if backup:
                _update_folder(
                    drive,backup["id"],name=period,
                    app_properties={
                        **(current.get("appProperties") or {}),
                        "status":"READY",
                    },
                )
            raise

        if backup:
            _trash(drive,backup["id"])

        return {
            "status":"PUBLISHED",
            "shop_key":shop_key,
            "shop_id":local["shop_id"],
            "period":period,
            "build_fingerprint":local["build_fingerprint"],
            "drive_folder_id":activated["id"],
            "uploaded_file_count":len(uploaded),
            "uploaded_files":uploaded,
            "previous_partition_replaced":bool(current),
        }
    except Exception:
        # Only trash temp if it was not already activated as canonical period.
        try:
            current_name=drive.files().get(
                fileId=temp_id,
                fields="id,name,trashed",
                supportsAllDrives=True,
            ).execute()
            if not current_name.get("trashed") and current_name.get("name")!=period:
                _trash(drive,temp_id)
        except Exception:
            pass
        raise


def ensure_control_run_folder(drive,control_root_id:str,run_id:str)->Dict[str,Any]:
    runs=_folders_named(drive,control_root_id,"runs")
    if len(runs)>1:
        raise ValueError("multiple _control/runs folders found")
    runs_folder=runs[0] if runs else _create_folder(
        drive,parent_id=control_root_id,name="runs",
        app_properties={"layer":"processed_v2","kind":"runs"},
    )
    matches=_folders_named(drive,runs_folder["id"],run_id)
    if len(matches)>1:
        raise ValueError(f"multiple run audit folders found for {run_id}")
    return matches[0] if matches else _create_folder(
        drive,parent_id=runs_folder["id"],name=run_id,
        app_properties={"layer":"processed_v2","kind":"run_audit","writerRunId":run_id},
    )


def upload_control_file(
    drive,
    *,
    control_root_id:str,
    run_id:str,
    local_path:Path,
    file_name:str,
    attempts:int=3,
    base_delay_seconds:float=1.0,
)->Dict[str,Any]:
    """Upload writer audit evidence with bounded retry.

    Partition activation is already atomic and may complete before a transient
    Drive read/upload response times out. Retrying the whole control-file write
    is safe because each attempt re-lists and trashes any same-name audit file
    created by an earlier ambiguous attempt.
    """
    attempts=max(1,int(attempts))
    last_exc=None
    for attempt in range(1,attempts+1):
        try:
            run_folder=ensure_control_run_folder(drive,control_root_id,run_id)
            existing=[x for x in _list_children(drive,run_folder["id"],file_name)
                      if x.get("mimeType")!=FOLDER_MIME]
            for old in existing:
                _trash(drive,old["id"])
            return _upload_file_verified(
                drive,
                local_path=local_path,
                parent_id=run_folder["id"],
                file_name=file_name,
                expected_md5=md5_file(local_path),
                expected_size=local_path.stat().st_size,
                build_fingerprint=run_id,
            )
        except Exception as exc:
            last_exc=exc
            if attempt>=attempts:
                raise
            if base_delay_seconds>0:
                time.sleep(base_delay_seconds*attempt)
    raise last_exc  # pragma: no cover
