import json, os, sys

required = [
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "UNIPALM_DASHBOARD_ACCESS_KEY",
    "GOOGLE_DRIVE_SOURCE_FOLDER_ID",
]
missing = [k for k in required if not os.getenv(k)]
if missing:
    print("::error::Missing GitHub Actions secrets: " + ", ".join(missing))
    sys.exit(2)

try:
    creds = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    assert creds.get("client_email") and creds.get("private_key")
except Exception as exc:
    print(f"::error::GOOGLE_SERVICE_ACCOUNT_JSON is invalid: {exc}")
    sys.exit(2)

print("Configuration validation: PASS")
print("Google service account:", creds["client_email"])
