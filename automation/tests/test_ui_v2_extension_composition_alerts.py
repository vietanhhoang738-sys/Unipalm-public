import unittest

from modules import ui_v2_extension_composition_alerts as alerts
from modules import ui_v2_extension_composition_canonical as previous


class NativeExtensionCompositionAlertsTest(unittest.TestCase):
    def test_v12_is_strict_additive_extension_of_v11(self):
        self.assertEqual(alerts.NATIVE_EXTENSION_COMPOSITION_VERSION, "native-v2-extension-composition-v1.2")
        self.assertEqual(alerts.EXTENSION_ORDER[:-1], previous.EXTENSION_ORDER)
        self.assertEqual(alerts.EXTENSION_ORDER[-1], "ads_smart_issue_alert_policy")
        self.assertEqual(len(alerts.EXTENSION_ORDER), 12)
        self.assertEqual(len(set(alerts.EXTENSION_ORDER)), 12)
        self.assertEqual(alerts.BASE_COMPATIBILITY_BRIDGE_COUNT, 1)

    def test_v11_lineage_is_preserved_before_alert_ui(self):
        markers = alerts.lineage_markers()
        self.assertEqual(markers[0], "native-v2-extension-composition-v1.2")
        self.assertEqual(markers[1:-1], previous.lineage_markers())
        self.assertEqual(markers[-1], "ads-smart-issue-alert-policy-ui-v1")
        self.assertEqual(len(markers), len(set(markers)))

    def test_style_and_runtime_are_additive(self):
        style = alerts.compose_effective_style()
        runtime = alerts.compose_effective_runtime({})
        self.assertIn("ads-smart-issue-review-console-ui-v1", style)
        self.assertIn("ads-smart-issue-alert-policy-ui-v1", style)
        self.assertIn("native-v2-extension-composition-v1.2", runtime)
        self.assertIn("native-v2-extension-composition-v1.1", runtime)
        self.assertIn("smartIssueReviewWorkflow", runtime)
        self.assertIn("smartIssueAlertPolicy", runtime)
        for token in ("fetch(", "XMLHttpRequest", "const rawSignals=snap.signals||[]"):
            self.assertNotIn(token, runtime)


if __name__ == "__main__":
    unittest.main()
