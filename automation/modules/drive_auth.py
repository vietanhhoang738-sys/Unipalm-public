"""Authentication helpers for the pre-production Drive writer.

Current My Drive storage requires delegated user OAuth because Google service
accounts do not have storage quota in My Drive.

Runtime secret format (GOOGLE_DRIVE_OAUTH_JSON):
{
  "client_id": "...apps.googleusercontent.com",
  "client_secret": "...",
  "refresh_token": "...",
  "token_uri": "https://oauth2.googleapis.com/token"
}
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials


DRIVE_SCOPE="https://www.googleapis.com/auth/drive"


class DriveAuthError(RuntimeError):
    pass


def _load_json_env(name:str)->Dict[str,Any]:
    raw=os.environ.get(name,"").strip()
    if not raw:
        return {}
    try:
        data=json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DriveAuthError(f"{name} is not valid JSON") from exc
    if not isinstance(data,dict):
        raise DriveAuthError(f"{name} must contain a JSON object")
    return data


def user_oauth_credentials_from_info(info:Dict[str,Any]) -> UserCredentials:
    required=("client_id","client_secret","refresh_token")
    missing=[x for x in required if not str(info.get(x) or "").strip()]
    if missing:
        raise DriveAuthError(f"OAuth credential missing fields: {missing}")
    token_uri=str(info.get("token_uri") or "https://oauth2.googleapis.com/token")
    return UserCredentials(
        token=None,
        refresh_token=str(info["refresh_token"]),
        token_uri=token_uri,
        client_id=str(info["client_id"]),
        client_secret=str(info["client_secret"]),
        scopes=[DRIVE_SCOPE],
        quota_project_id=info.get("quota_project_id"),
    )


def resolve_drive_credentials(*,auth_mode:str):
    mode=str(auth_mode or "").strip()
    if mode=="user_oauth":
        info=_load_json_env("GOOGLE_DRIVE_OAUTH_JSON")
        if not info:
            raise DriveAuthError(
                "GOOGLE_DRIVE_OAUTH_JSON is required for processed_v2 My Drive writes. "
                "Create a user OAuth refresh token and store it as a GitHub Actions secret."
            )
        return user_oauth_credentials_from_info(info),"user_oauth"

    if mode=="service_account":
        info=_load_json_env("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not info:
            raise DriveAuthError("GOOGLE_SERVICE_ACCOUNT_JSON is required")
        return ServiceAccountCredentials.from_service_account_info(
            info,scopes=[DRIVE_SCOPE]
        ),"service_account"

    raise DriveAuthError(f"unsupported Drive writer auth_mode: {mode!r}")
