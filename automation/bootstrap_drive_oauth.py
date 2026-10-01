#!/usr/bin/env python3
"""One-time helper to generate GOOGLE_DRIVE_OAUTH_JSON for GitHub Actions.

Run locally on a trusted machine after creating a Google OAuth Desktop client:

  python automation/bootstrap_drive_oauth.py \
    --client-secret client_secret_xxx.json \
    --output drive_oauth_secret.json

A browser opens for Google consent. The resulting file contains a refresh token.
Never commit or upload that file to the repository.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from modules.drive_auth import DRIVE_SCOPE


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--client-secret",required=True)
    ap.add_argument("--output",default="drive_oauth_secret.json")
    args=ap.parse_args()

    client_secret=Path(args.client_secret)
    if not client_secret.exists():
        raise FileNotFoundError(client_secret)

    flow=InstalledAppFlow.from_client_secrets_file(
        str(client_secret),
        scopes=[DRIVE_SCOPE],
    )
    creds=flow.run_local_server(
        host="localhost",
        port=0,
        authorization_prompt_message="Open this URL in your browser:\n{url}",
        success_message="OAuth complete. You can close this window.",
        open_browser=True,
        access_type="offline",
        prompt="consent",
    )
    if not creds.refresh_token:
        raise RuntimeError(
            "Google did not return a refresh token. Revoke the app grant and rerun with consent."
        )

    payload={
        "client_id":creds.client_id,
        "client_secret":creds.client_secret,
        "refresh_token":creds.refresh_token,
        "token_uri":creds.token_uri,
    }
    out=Path(args.output)
    out.write_text(
        json.dumps(payload,ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8",
    )
    print(f"Wrote OAuth secret JSON to: {out}")
    print("Next: add the entire JSON file content as GitHub Actions secret GOOGLE_DRIVE_OAUTH_JSON.")
    print("Do not commit this file.")


if __name__=="__main__":
    main()
