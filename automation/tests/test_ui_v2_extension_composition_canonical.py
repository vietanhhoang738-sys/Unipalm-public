import inspect
import unittest

from modules import ui_v2_extension_composition as locked_v1
from modules import ui_v2_extension_composition_canonical as composition


class NativeV2CanonicalCompositionTest(unittest.TestCase):
    def test_locked_v1_is_preserved_and_canonical_is_additive_v11(self):
        self.assertEqual(locked_v1.NATIVE_EXTENSION_COMPOSITION_VERSION, "native-v2-extension-composition-v1")
        self.assertEqual(composition.NATIVE_EXTENSION_COMPOSITION_VERSION, "native-v2-extension-composition-v1.1")
        self.assertEqual(composition.EXTENSION_ORDER[:-1], locked_v1.EXTENSION_ORDER)
        self.assertEqual(composition.EXTENSION_ORDER[-1], "ads_smart_issue_review_console")

    def test_lineage_markers_preserve_locked_versions(self):
        markers = composition.lineage_markers()
        expected = {
            "native-v2-extension-composition-v1.1",
            "native-v2-extension-composition-v1",
            "native-product-intelligence-v36-short-names",
            "native-ads-intelligence-v37",
            "native-ads-financial-v38",
            "ads-diagnosis-persistence-ui-v1",
            "ads-smart-issue-candidate-ui-v1",
            "ads-smart-issue-registry-ui-v1",
            "ads-smart-issue-review-console-ui-v1",
        }
        self.assertTrue(expected.issubset(set(markers)))
        self.assertEqual(len(markers), len(set(markers)))

    def test_lineage_comment_is_deterministic_and_explicit(self):
        comment = composition.lineage_comment()
        self.assertIn("UNIPALM_NATIVE_EXTENSION_LINEAGE", comment)
        actual = [
            line[len(" * "):]
            for line in comment.splitlines()
            if line.startswith(" * ")
        ]
        self.assertEqual(actual, list(composition.lineage_markers()))

    def test_canonical_builder_uses_one_base_native_boundary(self):
        source = inspect.getsource(composition.build_native_v2_multi_shop)
        self.assertIn("native.build_native_v2_multi_shop", source)
        self.assertNotIn("_registry.build_native_v2_multi_shop", source)
        self.assertNotIn("_candidate.build_native_v2_multi_shop", source)
        self.assertNotIn("_persistence.build_native_v2_multi_shop", source)
        self.assertNotIn("_diagnosis.build_native_v2_multi_shop", source)
        self.assertEqual(composition.PLAN.compatibility_bridge_count, 1)

    def test_runtime_carries_console_and_lineage_without_raw_ads_signal_binding(self):
        runtime = composition.compose_effective_runtime({})
        self.assertIn("UNIPALM_NATIVE_EXTENSION_LINEAGE", runtime)
        self.assertIn("native-product-intelligence-v36-short-names", runtime)
        self.assertIn("native-ads-intelligence-v37", runtime)
        self.assertIn("ads-smart-issue-review-console-ui-v1", runtime)
        self.assertIn("Smart Issue Review Console", runtime)
        self.assertNotIn("const rawSignals=snap.signals||[]", runtime)


if __name__ == "__main__":
    unittest.main()
