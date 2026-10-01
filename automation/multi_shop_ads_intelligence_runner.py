#!/usr/bin/env python3
"""Build Ads Intelligence V2 from trusted canonical Semantic history."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from googleapiclient.discovery import build

from modules.ads_alert_policy import bind_ads_alert_policy_artifact
from modules.ads_context_qualification import bind_ads_business_context_artifacts
from modules.ads_dynamic_diagnosis import bind_ads_dynamic_diagnosis_artifacts
from modules.ads_diagnosis_persistence import bind_ads_diagnosis_persistence_artifacts
from modules.ads_smart_issue_candidates import bind_ads_smart_issue_candidate_artifacts
from modules.ads_smart_issue_registry import bind_ads_smart_issue_registry_artifacts
from modules.ads_smart_issue_review_workflow import bind_ads_smart_issue_review_workflow_artifact
from modules.ads_intelligence import build_ads_intelligence
from modules.drive_auth import resolve_drive_credentials
from modules.shop_registry import enabled_shops, load_shop_registry
from multi_shop_staging_runner import children, download_bytes

FOLDER_MIME = "application/vnd.google-apps.folder"


def s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def child_file(items: Sequence[Mapping[str, Any]], name: str) -> Mapping[str, Any] | None:
    matches = [x for x in items if x.get("mimeType") != FOLDER_MIME and s(x.get("name")) == name]
    if len(matches) > 1:
        raise ValueError(f"duplicate file {name!r}")
    return matches[0] if matches else None


def json_file(drive, item: Mapping[str, Any]) -> Dict[str, Any]:
    return json.loads(download_bytes(drive, s(item.get("id"))).decode("utf-8"))


def jsonl_file(drive, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
    raw = download_bytes(drive, s(item.get("id"))).decode("utf-8")
    out = []
    for line_no, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{item.get('name')} line {line_no} is not an object")
        out.append(row)
    return out


def scan_trusted_ads_history(
    drive,
    *,
    semantic_root_id: str,
    expected_shop_ids: List[str],
    as_of_period: str,
):
    expected = set(expected_shop_ids)
    trusted = []
    ads_rows: List[Dict[str, Any]] = []
    product_rows: List[Dict[str, Any]] = []
    partitions = []
    lineage_by_shop: Dict[str, Dict[str, Any]] = {
        sid: {"canonicalSemanticMonths": [], "source": "CANONICAL_SEMANTIC_V2"}
        for sid in expected_shop_ids
    }

    for item in children(drive, semantic_root_id):
        month = s(item.get("name"))
        if item.get("mimeType") != FOLDER_MIME or not re.fullmatch(r"\d{4}-\d{2}", month) or month > as_of_period:
            continue
        files = children(drive, s(item.get("id")))
        manifest_item = child_file(files, "manifest.json")
        qa_item = child_file(files, "semantic_qa_report.json")
        ads_item = child_file(files, "dm_ads_daily.jsonl")
        product_item = child_file(files, "dm_ads_product_daily.jsonl")
        rec = {
            "month": month,
            "status": "NOT_TRUSTED",
            "reason": "MISSING_REQUIRED_ARTIFACT",
            "semanticFingerprint": "",
            "adsRowCount": 0,
            "adsProductRowCount": 0,
        }
        if manifest_item and qa_item and ads_item and product_item:
            manifest = json_file(drive, manifest_item)
            qa = json_file(drive, qa_item)
            fp = s(manifest.get("semantic_build_fingerprint"))
            selected = [s(x) for x in qa.get("selected_shop_ids") or []]
            trusted_ok = (
                qa.get("status") == "PASS"
                and bool(qa.get("semantic_mart_ready"))
                and bool(fp)
                and fp == s(qa.get("semantic_build_fingerprint"))
                and set(selected) == expected
            )
            rec["semanticFingerprint"] = fp
            rec["selectedShopIds"] = selected
            if trusted_ok:
                month_ads = jsonl_file(drive, ads_item)
                month_products = jsonl_file(drive, product_item)
                combined = month_ads + month_products
                foreign = sorted({s(r.get("shop_id")) for r in combined if s(r.get("shop_id")) not in expected})
                wrong = sorted({s(r.get("data_date"))[:7] for r in combined if s(r.get("data_date"))[:7] != month})
                duplicate_shop_keys = []
                seen = set()
                for row in month_ads:
                    key = (s(row.get("shop_id")), s(row.get("data_date"))[:10])
                    if key in seen:
                        duplicate_shop_keys.append(key)
                    seen.add(key)
                duplicate_product_keys = []
                seen_product = set()
                for row in month_products:
                    key = (s(row.get("shop_id")), s(row.get("data_date"))[:10], s(row.get("product_id")))
                    if key in seen_product:
                        duplicate_product_keys.append(key)
                    seen_product.add(key)
                if foreign:
                    rec["reason"] = f"FOREIGN_SHOP_IDS:{foreign}"
                elif wrong:
                    rec["reason"] = f"WRONG_DATA_MONTH:{wrong}"
                elif duplicate_shop_keys:
                    rec["reason"] = f"DUPLICATE_SHOP_DATE_KEYS:{duplicate_shop_keys[:10]}"
                elif duplicate_product_keys:
                    rec["reason"] = f"DUPLICATE_PRODUCT_DATE_KEYS:{duplicate_product_keys[:10]}"
                else:
                    ads_rows.extend(month_ads)
                    product_rows.extend(month_products)
                    trusted.append((month, fp))
                    rec.update({
                        "status": "TRUSTED",
                        "reason": "SEMANTIC_QA_PASS",
                        "adsRowCount": len(month_ads),
                        "adsProductRowCount": len(month_products),
                    })
                    for sid in expected_shop_ids:
                        if any(s(r.get("shop_id")) == sid for r in month_ads):
                            lineage_by_shop[sid]["canonicalSemanticMonths"].append(month)
            else:
                rec["reason"] = "SEMANTIC_QA_OR_SCOPE_NOT_TRUSTED"
        partitions.append(rec)

    trusted.sort()
    for sid in lineage_by_shop:
        lineage_by_shop[sid]["canonicalSemanticMonths"] = sorted(set(lineage_by_shop[sid]["canonicalSemanticMonths"]))
    inventory = {
        "policy": "PUBLISHED_SEMANTIC_QA_PASS_ALL_ENABLED_SHOPS_ONLY",
        "trustedMonths": [x[0] for x in trusted],
        "trustedFingerprints": [x[1] for x in trusted],
        "trustedMonthCount": len(trusted),
        "partitions": sorted(partitions, key=lambda x: x["month"]),
    }
    lineage = {
        "policy": "CANONICAL_SEMANTIC_V2_ONLY",
        "shops": lineage_by_shop,
    }
    return inventory, lineage, ads_rows, product_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--registry", default="config/shop_registry.json")
    ap.add_argument("--storage-registry", default="config/storage_registry.json")
    ap.add_argument("--contract", default="config/ads_intelligence_contract.json")
    ap.add_argument("--diagnosis-contract", default="config/ads_dynamic_diagnosis_contract.json")
    ap.add_argument("--persistence-contract", default="config/ads_diagnosis_persistence_contract.json")
    ap.add_argument("--smart-issue-contract", default="config/ads_smart_issue_candidate_contract.json")
    ap.add_argument("--smart-issue-registry-contract", default="config/ads_smart_issue_registry_contract.json")
    ap.add_argument("--smart-issue-review-events", default="ops/ads_smart_issue_review_events.json")
    ap.add_argument("--smart-issue-review-workflow-contract", default="config/ads_smart_issue_review_workflow_contract.json")
    ap.add_argument("--alert-policy-contract", default="config/ads_alert_policy_contract.json")
    ap.add_argument("--alert-delivery-events", default="ops/ads_alert_delivery_events.json")
    ap.add_argument("--alert-evaluation-at", default="")
    ap.add_argument("--context-dir", default="")
    ap.add_argument("--output-dir", default="ads_intelligence_artifacts")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        raise ValueError("--month must be YYYY-MM")

    registry = load_shop_registry(args.registry)
    shops = enabled_shops(registry)
    expected = [s(x.get("shop_id")) for x in shops]
    storage = read_json(args.storage_registry)
    semantic_root_id = s((storage.get("semantic_v2") or {}).get("drive_root_id"))
    if not semantic_root_id:
        raise ValueError("semantic_v2 Drive root is required")

    creds, auth_mode = resolve_drive_credentials(auth_mode="user_oauth")
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    inventory, lineage, ads_rows, product_rows = scan_trusted_ads_history(
        drive,
        semantic_root_id=semantic_root_id,
        expected_shop_ids=expected,
        as_of_period=args.month,
    )

    out = Path(args.output_dir) / args.month
    out.mkdir(parents=True, exist_ok=True)
    (out / "ads_history_inventory.json").write_text(
        json.dumps({"authMode": auth_mode, "inventory": inventory, "historyLineage": lineage}, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    base_result = build_ads_intelligence(
        ads_rows=ads_rows,
        ads_product_rows=product_rows,
        shops=shops,
        trusted_months=inventory["trustedMonths"],
        trusted_fingerprints=inventory["trustedFingerprints"],
        as_of_period=args.month,
        contract_path=args.contract,
        output_dir=out,
        history_lineage=lineage,
    )
    context_dir = Path(args.context_dir) if args.context_dir else Path("context_artifacts") / args.month
    context_result = bind_ads_business_context_artifacts(
        ads_output_dir=out,
        context_dir=context_dir,
        contract_path=args.contract,
    )
    diagnosis_result = bind_ads_dynamic_diagnosis_artifacts(
        ads_output_dir=out,
        contract_path=args.diagnosis_contract,
    )
    persistence_result = bind_ads_diagnosis_persistence_artifacts(
        ads_output_dir=out,
        contract_path=args.persistence_contract,
    )
    smart_issue_result = bind_ads_smart_issue_candidate_artifacts(
        ads_output_dir=out,
        contract_path=args.smart_issue_contract,
    )
    registry_result = bind_ads_smart_issue_registry_artifacts(
        ads_output_dir=out,
        contract_path=args.smart_issue_registry_contract,
        review_events_path=args.smart_issue_review_events,
    )
    review_workflow_result = bind_ads_smart_issue_review_workflow_artifact(
        ads_output_dir=out,
        contract_path=args.smart_issue_review_workflow_contract,
        review_events_path=args.smart_issue_review_events,
    )
    if review_workflow_result["adsIntelligenceFingerprint"] != registry_result["adsIntelligenceFingerprint"]:
        raise ValueError("operator review workflow must not modify the locked Smart Issue Registry fingerprint")

    alert_policy_result = bind_ads_alert_policy_artifact(
        ads_output_dir=out,
        contract_path=args.alert_policy_contract,
        delivery_events_path=args.alert_delivery_events,
        evaluation_at=args.alert_evaluation_at,
    )
    if alert_policy_result["adsIntelligenceFingerprint"] != registry_result["adsIntelligenceFingerprint"]:
        raise ValueError("Alert Policy must not modify the locked Smart Issue Registry / Ads fingerprint")

    result = {
        **base_result,
        "baseAdsIntelligenceFingerprint": context_result["baseAdsIntelligenceFingerprint"],
        "adsContextQualificationFingerprint": context_result["adsContextQualificationFingerprint"],
        "sourceBusinessContextFingerprint": context_result["sourceBusinessContextFingerprint"],
        "businessContextQualificationStatus": context_result["businessContextQualificationStatus"],
        "preDiagnosisAdsIntelligenceFingerprint": diagnosis_result["preDiagnosisAdsIntelligenceFingerprint"],
        "adsDynamicDiagnosisFingerprint": diagnosis_result["adsDynamicDiagnosisFingerprint"],
        "dynamicDiagnosisStatus": diagnosis_result["dynamicDiagnosisStatus"],
        "prePersistenceAdsIntelligenceFingerprint": persistence_result["prePersistenceAdsIntelligenceFingerprint"],
        "adsDiagnosisPersistenceFingerprint": persistence_result["adsDiagnosisPersistenceFingerprint"],
        "diagnosisPersistenceStatus": persistence_result["diagnosisPersistenceStatus"],
        "preSmartIssueAdsIntelligenceFingerprint": smart_issue_result["preSmartIssueAdsIntelligenceFingerprint"],
        "adsSmartIssueCandidateFingerprint": smart_issue_result["adsSmartIssueCandidateFingerprint"],
        "smartIssueCandidateStatus": smart_issue_result["smartIssueCandidateStatus"],
        "preSmartIssueRegistryAdsIntelligenceFingerprint": registry_result["preSmartIssueRegistryAdsIntelligenceFingerprint"],
        "adsSmartIssueReviewLedgerFingerprint": registry_result["adsSmartIssueReviewLedgerFingerprint"],
        "adsSmartIssueRegistryFingerprint": registry_result["adsSmartIssueRegistryFingerprint"],
        "adsIntelligenceFingerprint": registry_result["adsIntelligenceFingerprint"],
        "smartIssueRegistryStatus": registry_result["smartIssueRegistryStatus"],
        "adsSmartIssueOperatorReviewWorkflowFingerprint": review_workflow_result["adsSmartIssueOperatorReviewWorkflowFingerprint"],
        "smartIssueOperatorReviewWorkflowStatus": review_workflow_result["smartIssueOperatorReviewWorkflowStatus"],
        "smartIssueReviewQueueCount": review_workflow_result["reviewQueueCount"],
        "smartIssueReviewIssueCount": review_workflow_result["issueCount"],
        "adsSmartIssueAlertPolicyFingerprint": alert_policy_result["adsSmartIssueAlertPolicyFingerprint"],
        "smartIssueAlertPolicyStatus": alert_policy_result["smartIssueAlertPolicyStatus"],
        "smartIssueEligibleAlertCount": alert_policy_result["eligibleAlertCount"],
        "smartIssueAlertSuppressedIssueCount": alert_policy_result["suppressedIssueCount"],
        "smartIssueAlertDeliveryEnabled": alert_policy_result["deliveryEnabled"],
        "smartIssueAlertAutomaticDeliveryEnabled": alert_policy_result["automaticDeliveryEnabled"],
    }
    summary = {
        **result,
        "authMode": auth_mode,
        "trustedCanonicalAdsMonths": inventory["trustedMonths"],
        "adsDailyRowCount": len(ads_rows),
        "adsProductDailyRowCount": len(product_rows),
        "contextCandidatePreviewFile": str(out / "ads_context_candidate_preview.json"),
        "diagnosisCandidatePreviewFile": str(out / "ads_diagnosis_candidate_preview.json"),
        "persistenceCandidatePreviewFile": str(out / "ads_persistence_candidate_preview.json"),
        "smartIssueCandidatePreviewFile": str(out / "ads_smart_issue_candidate_preview.json"),
        "smartIssueRegistryFile": str(out / "ads_smart_issue_registry.json"),
        "smartIssueRegistryPreviewFile": str(out / "ads_smart_issue_registry_preview.json"),
        "smartIssueOperatorReviewWorkflowFile": str(out / "ads_smart_issue_review_workflow.json"),
        "smartIssueAlertPolicyFile": str(out / "ads_alert_policy.json"),
        "outputLocation": str(out),
    }
    root = Path(args.output_dir)
    (root / f"multi_shop_ads_intelligence_summary_{args.month}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
