# Processed v2 Drive Writer — OAuth Setup

Date: 2026-09-23

## Why OAuth is required

The processed v2 writer targets a normal Google My Drive folder.

The existing GitHub service account can read the RAW tree and can create folders that were shared to it, but Google blocks file uploads from service accounts into My Drive because service accounts do not have personal storage quota.

Observed live failure:

`403 storageQuotaExceeded: Service Accounts do not have storage quota`

Therefore only the **Drive writer** changes authentication:

- RAW/staging readers may continue using `GOOGLE_SERVICE_ACCOUNT_JSON`.
- Processed v2 Drive publisher uses `GOOGLE_DRIVE_OAUTH_JSON`, owned by the Google user who owns the Drive storage.

The production Data Mart/UI remain unchanged.

## One-time manual setup

### 1. Create a Google OAuth Desktop client

Use the same Google account / Google Cloud project that you want to authorize for the Unipalm Drive writer.

In Google Cloud Console:

1. Enable Google Drive API for the project if it is not already enabled.
2. Configure the OAuth consent screen.
3. Create an OAuth Client ID with application type **Desktop app**.
4. Download the client JSON file.

Do not commit this downloaded file to GitHub.

The repository `.gitignore` already ignores `client_secret*.json`.

### 2. Generate the refresh token locally

From the repository on your own computer:

```bash
pip install -r automation/requirements.txt

python automation/bootstrap_drive_oauth.py \
  --client-secret /path/to/client_secret_xxx.json \
  --output drive_oauth_secret.json
```

A browser opens.

Sign in with the Google user that owns or has write access to:
`03_processed_data_v2`

Approve Google Drive access.

The helper writes:

`drive_oauth_secret.json`

Its shape is:

```json
{
  "client_id": "...apps.googleusercontent.com",
  "client_secret": "...",
  "refresh_token": "...",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

This file is sensitive because it contains a refresh token.

Do not send it in chat and do not commit it.

The repository `.gitignore` already ignores `drive_oauth_secret*.json`.

### 3. Add one GitHub Actions secret

Repository:

`vietanhhoang738-sys/Unipalm`

Add a repository Actions secret:

`GOOGLE_DRIVE_OAUTH_JSON`

Value:

the **entire JSON content** of `drive_oauth_secret.json`.

The workflow already injects this secret only into the staging/pre-production job.

## After the secret is added

No more manual Drive upload is needed.

The workflow will:

1. RAW ingestion;
2. staging + schema QA;
3. shop-scoped processed/control candidate;
4. processed QA;
5. OAuth-authenticated Drive writer;
6. atomic publish to:
   `03_processed_data_v2/<shop_key>/<YYYY-MM>/...`
7. write run evidence under:
   `03_processed_data_v2/_control/runs/<run_id>/...`

Expected first valid run:

`PUBLISHED`

Expected immediate rebuild with unchanged business facts:

`NOOP`

because the current partition has the same `build_fingerprint`.

## Safety rules already enforced

Writer configuration:
- storage status = `PREPRODUCTION`;
- auth mode = `user_oauth`;
- legacy `03_processed_data` root is forbidden;
- production Data Mart root is forbidden;
- production Data Mart writes = false;
- UI writes = false;
- overwrite scope = one shop + one period;
- existing unmanaged partition = FAIL;
- upload verification = MD5 + byte size;
- previous partition survives until the new partition is fully uploaded and marked READY;
- failed upload temp partition is discarded;
- identical fingerprint = NOOP.

## Current state before OAuth consent

All code and tests are ready.

The latest live writer attempt proved:
- staging PASS;
- processed/control PASS;
- service-account Drive access is visible;
- file upload is blocked only by service-account storage quota;
- no active `2026-09` partition was left behind;
- legacy processed/Data Mart/UI were not touched.

The service account already has writer access to the v2 root, but this does not solve the quota restriction. User OAuth is the intended solution for My Drive.


## Validation completed

OAuth setup has been completed and the GitHub secret `GOOGLE_DRIVE_OAUTH_JSON` is active.

Live results:
- run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`: both shop partitions PUBLISHED successfully;
- run `PUBLIC_SNAPSHOT_NOT_CONFIGURED`: both partitions NOOP on identical rebuild.

No additional manual OAuth setup is required for normal workflow runs unless the OAuth grant/refresh token is revoked or expires.

The writer now uses user OAuth for My Drive persistence while RAW/staging reads continue using the service account.
