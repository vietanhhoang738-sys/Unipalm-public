import json
import unittest
from pathlib import Path

from modules.shop_registry import CORE_STAGING_DOMAINS


ROOT=Path(__file__).resolve().parents[2]
INVENTORY=ROOT/"config"/"legacy_pipeline_dependencies.json"


class LegacyDependencyInventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(INVENTORY.read_text(encoding="utf-8"))

    def test_all_core_domains_are_classified(self):
        rows={x["source_domain"]:x for x in self.data["domains"]}
        self.assertTrue(set(CORE_STAGING_DOMAINS).issubset(rows))
        for domain in CORE_STAGING_DOMAINS:
            self.assertTrue(rows[domain]["dependency_status"])
            self.assertTrue(rows[domain]["move_status"])
            self.assertTrue(rows[domain]["raw_folder_id"])

    def test_unverified_dependency_cannot_be_move_ready(self):
        bad=[]
        for row in self.data["domains"]:
            if row["dependency_status"].startswith("UNVERIFIED") and row["move_status"]!="BLOCKED":
                bad.append(row["source_domain"])
        self.assertEqual(bad,[])

    def test_atomic_cutover_policy_is_explicit(self):
        self.assertEqual(self.data["policy"]["cutover_unit"],"all_core_raw_domains_together")
        self.assertTrue(self.data["legacy_shop_scope"]["migration_raw_root_id"])

    def test_orders_is_verified_but_not_moved_independently(self):
        row=next(x for x in self.data["domains"] if x["source_domain"]=="orders")
        self.assertEqual(row["dependency_status"],"VERIFIED_FOLDER_ID")
        self.assertEqual(row["move_status"],"WAIT_ATOMIC_CUTOVER")

    def test_active_pipeline_state_is_explicitly_protected(self):
        control=self.data["control_plane"]
        self.assertEqual(control["pipeline_state_status"],"ACTIVE_LEGACY_PRODUCTION_STATE")
        self.assertTrue(control["pipeline_state_sheet_id"])


if __name__=="__main__":
    unittest.main()
