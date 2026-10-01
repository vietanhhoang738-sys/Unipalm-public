"""Atomic Drive writer for Product-history semantic partitions."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping

from googleapiclient.http import MediaFileUpload

from .drive_partition_writer import _create_folder, _folders_named, _trash, _update_folder


FOLDER_MIME = "application/vnd.google-apps.folder"
LAYER_NAME = "product_history_semantic_v1"


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_storage(path: str | Path) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg = data.get("product_history_semantic_v1") or {}
    if s(cfg.get("status")) != "PREPRODUCTION":
        raise ValueError("product_history_semantic_v1 storage must remain PREPRODUCTION")
    parent = s(cfg.get("parent_drive_root_id"))
    root_name = s(cfg.get("namespace_root_name"))
    if not parent or not root_name:
        raise ValueError("Product history storage parent/root name required")
    policy = cfg.get("writer_policy") or {}
    if s(policy.get("publish_mode")) != "atomic_partition_swap":
        raise ValueError("Product history writer requires atomic_partition_swap")
    if any(bool(policy.get(k)) for k in (
        "write_production_data_mart", "write_production_ui", "publish_canonical_portfolio_semantic"
    )):
        raise ValueError("unsafe Product history writer policy")
    return data


def _list_children(drive, parent_id: str):
    q = f"'{parent_id}' in parents and trashed=false"
    out = []; token = None
    while True:
        res = drive.files().list(
            q=q,
            fields="nextPageToken,files(id,name,mimeType,size,md5Checksum,appProperties)",
            pageSize=1000,
            pageToken=token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        out.extend(res.get("files") or [])
        token = res.get("nextPageToken")
        if not token:
            return out


def _child_folder(drive, parent_id: str, name: str):
    matches = [x for x in _list_children(drive, parent_id) if x.get("mimeType") == FOLDER_MIME and s(x.get("name")) == name]
    if len(matches) > 1:
        raise ValueError(f"multiple Product history folders named {name!r}")
    return matches[0] if matches else None


def _ensure_folder(drive, parent_id: str, name: str, props: Mapping[str, str]):
    existing = _child_folder(drive, parent_id, name)
    if existing:
        return existing
    return _create_folder(drive, parent_id=parent_id, name=name, app_properties=props)


def _upload_verified(drive, *, path: Path, parent_id: str, fingerprint: str):
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    media = MediaFileUpload(str(path), mimetype=mime, resumable=False)
    created = drive.files().create(
        body={
            "name": path.name,
            "parents": [parent_id],
            "appProperties": {
                "layer": LAYER_NAME,
                "buildFingerprint": fingerprint,
                "sha256": sha256_file(path),
            },
        },
        media_body=media,
        fields="id,name,size,md5Checksum,appProperties",
        supportsAllDrives=True,
    ).execute()
    if int(created.get("size") or -1) != path.stat().st_size or s(created.get("md5Checksum")) != md5_file(path):
        try:
            _trash(drive, created["id"])
        finally:
            raise RuntimeError(f"Product history Drive verification failed: {path.name}")
    return created


def validate_local_partition(partition_dir: str | Path, *, shop_key: str, period: str) -> Dict[str, Any]:
    root = Path(partition_dir)
    manifest_path = root / "manifest.json"
    qa_path = root / "product_history_qa_report.json"
    mart_path = root / "dm_product_monthly.jsonl"
    for path in (manifest_path, qa_path, mart_path):
        if not path.exists():
            raise FileNotFoundError(f"Product history partition missing {path.name}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    if s(manifest.get("layer")) != LAYER_NAME:
        raise ValueError("Product history layer mismatch")
    if s(manifest.get("shopKey")) != shop_key or s(manifest.get("period")) != period:
        raise ValueError("Product history manifest scope mismatch")
    if qa.get("status") != "PASS" or not bool(qa.get("productHistorySemanticReady")):
        raise ValueError("Product history QA is not PASS/ready")
    fp = s(manifest.get("productHistorySemanticFingerprint"))
    if not fp or fp != s(qa.get("productHistorySemanticFingerprint")):
        raise ValueError("Product history fingerprint mismatch")
    listed = manifest.get("files") or []
    if len(listed) != 1 or s(listed[0].get("file")) != "dm_product_monthly.jsonl":
        raise ValueError("Product history manifest file contract mismatch")
    if sha256_file(mart_path) != s(listed[0].get("sha256")):
        raise ValueError("Product history mart hash mismatch")
    safety = manifest.get("safety") or {}
    if any(bool(safety.get(k)) for k in (
        "fullShopProcessedPromotionPerformed", "canonicalPortfolioSemanticPublished",
        "productionDataMartWritten", "productionUiModified", "platformMutationAllowed",
    )):
        raise ValueError("Product history safety boundary violated")
    files = []
    for path in sorted(root.iterdir()):
        if path.is_file():
            files.append({"path": path, "name": path.name, "size": path.stat().st_size})
    return {
        "shopKey": shop_key,
        "shopId": s(manifest.get("shopId")),
        "period": period,
        "fingerprint": fp,
        "files": files,
        "manifest": manifest,
        "qa": qa,
    }


def publish_product_history_partition(
    drive,
    *,
    storage: Mapping[str, Any],
    partition_dir: str | Path,
    shop_key: str,
    period: str,
    run_id: str,
) -> Dict[str, Any]:
    local = validate_local_partition(partition_dir, shop_key=shop_key, period=period)
    cfg = storage.get("product_history_semantic_v1") or {}
    parent = s(cfg.get("parent_drive_root_id")); root_name = s(cfg.get("namespace_root_name"))
    namespace_root = _ensure_folder(
        drive, parent, root_name,
        {"layer": LAYER_NAME, "kind": "namespace_root", "status": "PREPRODUCTION"},
    )
    shop_root = _ensure_folder(
        drive, namespace_root["id"], shop_key,
        {"layer": LAYER_NAME, "kind": "shop", "shopKey": shop_key},
    )
    existing = _folders_named(drive, shop_root["id"], period)
    if len(existing) > 1:
        raise ValueError(f"{shop_key}/{period}: multiple Product history partitions")
    current = existing[0] if existing else None
    if current:
        props = current.get("appProperties") or {}
        managed = (
            s(props.get("layer")) == LAYER_NAME
            and s(props.get("kind")) == "partition"
            and s(props.get("shopKey")) == shop_key
            and s(props.get("period")) == period
        )
        if not managed:
            raise ValueError(f"{shop_key}/{period}: existing Product history partition unmanaged")
        if s(props.get("buildFingerprint")) == local["fingerprint"]:
            return {
                "status": "NOOP", "shopKey": shop_key, "shopId": local["shopId"],
                "period": period, "productHistorySemanticFingerprint": local["fingerprint"],
                "driveFolderId": current["id"], "uploadedFileCount": 0,
                "reason": "same_build_fingerprint",
            }

    temp = _create_folder(
        drive,
        parent_id=shop_root["id"],
        name=f".tmp_{period}_{run_id}_{uuid.uuid4().hex[:8]}",
        app_properties={
            "layer": LAYER_NAME, "kind": "partition", "shopKey": shop_key,
            "period": period, "buildFingerprint": local["fingerprint"],
            "writerRunId": run_id, "status": "UPLOADING",
        },
    )
    backup = None; uploaded = []
    try:
        for item in local["files"]:
            remote = _upload_verified(
                drive, path=item["path"], parent_id=temp["id"], fingerprint=local["fingerprint"]
            )
            uploaded.append({"file": item["name"], "driveFileId": remote["id"], "size": item["size"]})
        props = {
            "layer": LAYER_NAME, "kind": "partition", "shopKey": shop_key,
            "period": period, "buildFingerprint": local["fingerprint"],
            "writerRunId": run_id, "status": "READY", "fileCount": str(len(uploaded)),
        }
        _update_folder(drive, temp["id"], app_properties=props)
        if current:
            backup = _update_folder(
                drive, current["id"],
                name=f".backup_{period}_{run_id}_{uuid.uuid4().hex[:8]}",
                app_properties={**(current.get("appProperties") or {}), "status": "SUPERSEDED_PENDING_SWAP"},
            )
        try:
            activated = _update_folder(drive, temp["id"], name=period, app_properties=props)
        except Exception:
            if backup:
                _update_folder(
                    drive, backup["id"], name=period,
                    app_properties={**(current.get("appProperties") or {}), "status": "READY"},
                )
            raise
        if backup:
            _trash(drive, backup["id"])
        return {
            "status": "PUBLISHED", "shopKey": shop_key, "shopId": local["shopId"],
            "period": period, "productHistorySemanticFingerprint": local["fingerprint"],
            "driveFolderId": activated["id"], "uploadedFileCount": len(uploaded),
            "uploadedFiles": uploaded, "previousPartitionReplaced": bool(current),
        }
    except Exception:
        try:
            state = drive.files().get(
                fileId=temp["id"], fields="id,name,trashed", supportsAllDrives=True
            ).execute()
            if not state.get("trashed") and state.get("name") != period:
                _trash(drive, temp["id"])
        except Exception:
            pass
        raise
