import unittest

from validate_architecture import validate_architecture


class SystemArchitectureRegistryTest(unittest.TestCase):
    def test_registry_is_structurally_valid(self):
        result = validate_architecture()
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["errorCount"], 0)
        self.assertGreaterEqual(result["moduleCount"], 15)

    def test_locked_modules_have_explicit_maintenance_boundaries(self):
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / "config/system_module_registry.json").read_text(encoding="utf-8"))
        for module in data["modules"]:
            if module["status"] != "LOCKED_V1":
                continue
            self.assertTrue(module["failure_boundary"], module["id"])
            self.assertTrue(module["change_entrypoints"], module["id"])
            self.assertTrue(module["doc_paths"], module["id"])
            self.assertTrue(module["test_paths"], module["id"])

    def test_operational_state_is_not_a_contract(self):
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / "config/system_module_registry.json").read_text(encoding="utf-8"))
        contract_paths = {
            path
            for module in data["modules"]
            for path in module.get("contract_paths", [])
        }
        for path in data["operational_state"]["paths"]:
            self.assertTrue(path.startswith("ops/"), path)
            self.assertNotIn(path, contract_paths)


if __name__ == "__main__":
    unittest.main()
