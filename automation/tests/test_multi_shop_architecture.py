import re
import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
RUNTIME_PATHS=[
    ROOT/"automation"/"modules"/"ads_product_mart.py",
    ROOT/"automation"/"modules"/"catalog_resolver.py",
    ROOT/"automation"/"modules"/"multi_shop_staging.py",
    ROOT/"automation"/"modules"/"pipeline_state.py",
    ROOT/"automation"/"modules"/"processed_layer.py",
    ROOT/"automation"/"modules"/"drive_partition_writer.py",
    ROOT/"automation"/"modules"/"drive_auth.py",
    ROOT/"automation"/"modules"/"semantic_mart.py",
    ROOT/"automation"/"modules"/"semantic_drive_writer.py",
    ROOT/"automation"/"modules"/"semantic_payload.py",
    ROOT/"automation"/"modules"/"ui_v2_compat.py",
    ROOT/"automation"/"modules"/"ui_v2_native.py",
    ROOT/"automation"/"modules"/"schema_registry.py",
    ROOT/"automation"/"modules"/"shop_registry.py",
    ROOT/"automation"/"multi_shop_staging_runner.py",
    ROOT/"automation"/"multi_shop_processed_runner.py",
    ROOT/"automation"/"multi_shop_drive_writer.py",
    ROOT/"automation"/"multi_shop_semantic_runner.py",
    ROOT/"automation"/"multi_shop_semantic_drive_writer.py",
    ROOT/"automation"/"multi_shop_payload_runner.py",
    ROOT/"automation"/"multi_shop_native_v2_runner.py",
    ROOT/"automation"/"bootstrap_drive_oauth.py",
    ROOT/"automation"/"source_processor.py",
    ROOT/"automation"/"run_pipeline.py",
    ROOT/"automation"/"backfill_product_ads.py",
]
WORKFLOW_PATHS=list((ROOT/".github"/"workflows").glob("*.yml"))
CONCRETE_PLATFORM_IDS=("1000000001","1000000002")
CONCRETE_INTERNAL_IDS=("SHP_VN_1000000001","SHP_VN_1000000002")


class MultiShopArchitectureGuardTest(unittest.TestCase):
    def test_runtime_code_does_not_embed_concrete_shop_identity(self):
        violations=[]
        for path in RUNTIME_PATHS:
            text=path.read_text(encoding="utf-8")
            for token in (*CONCRETE_PLATFORM_IDS,*CONCRETE_INTERNAL_IDS):
                if token in text:
                    violations.append(f"{path.relative_to(ROOT)} embeds {token}")
        self.assertEqual(violations,[], "\n".join(violations))

    def test_runtime_shop_id_arguments_have_no_concrete_default(self):
        violations=[]
        pat=re.compile(r"shop_id\s*:\s*str\s*=\s*[\"']SHP_")
        for path in RUNTIME_PATHS:
            text=path.read_text(encoding="utf-8")
            if pat.search(text):
                violations.append(str(path.relative_to(ROOT)))
        self.assertEqual(violations,[],f"Concrete shop_id defaults: {violations}")

    def test_multi_shop_workflow_does_not_default_to_one_named_shop(self):
        path=ROOT/".github"/"workflows"/"multi-shop-staging.yml"
        text=path.read_text(encoding="utf-8")
        self.assertNotRegex(text,r'default:\s*["\'](?:mall|syt_plus)["\']')
        self.assertNotIn("SHP_VN_1000000001",text)
        self.assertNotIn("SHP_VN_1000000002",text)

    def test_processed_storage_registry_is_shop_neutral(self):
        path=ROOT/"config"/"storage_registry.json"
        text=path.read_text(encoding="utf-8")
        self.assertNotIn('"syt_plus"',text)
        self.assertNotIn('"mall"',text)
        self.assertNotIn("SHP_VN_1000000001",text)
        self.assertNotIn("SHP_VN_1000000002",text)


if __name__=="__main__":
    unittest.main()
