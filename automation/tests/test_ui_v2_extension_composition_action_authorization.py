import unittest

from modules import ui_v2_extension_composition_action_authorization as action
from modules import ui_v2_extension_composition_alerts as previous


class NativeExtensionCompositionActionAuthorizationTest(unittest.TestCase):
    def test_v13_is_strict_additive_extension_of_v12(self):
        self.assertEqual(action.NATIVE_EXTENSION_COMPOSITION_VERSION, "native-v2-extension-composition-v1.3")
        self.assertEqual(action.EXTENSION_ORDER[:-1], previous.EXTENSION_ORDER)
        self.assertEqual(action.EXTENSION_ORDER[-1], "ads_action_authorization")
        self.assertEqual(len(action.EXTENSION_ORDER), 13)
        self.assertEqual(len(set(action.EXTENSION_ORDER)), 13)
        self.assertEqual(action.BASE_COMPATIBILITY_BRIDGE_COUNT, 1)

    def test_v12_lineage_is_preserved_before_action_authorization_ui(self):
        markers = action.lineage_markers()
        self.assertEqual(markers[0], "native-v2-extension-composition-v1.3")
        self.assertEqual(markers[1:-1], previous.lineage_markers())
        self.assertEqual(markers[-1], "ads-action-authorization-ui-v1")
        self.assertEqual(len(markers), len(set(markers)))

    def test_style_and_runtime_are_additive_and_read_only(self):
        style = action.compose_effective_style()
        runtime = action.compose_effective_runtime({})
        self.assertIn("ads-smart-issue-alert-policy-ui-v1", style)
        self.assertIn("ads-action-authorization-ui-v1", style)
        self.assertIn("native-v2-extension-composition-v1.3", runtime)
        self.assertIn("native-v2-extension-composition-v1.2", runtime)
        self.assertIn("smartIssueAlertPolicy", runtime)
        self.assertIn("smartIssueActionAuthorization", runtime)
        for token in ("fetch(", "XMLHttpRequest", "--apply", "executeAction(", "runAction(", "const rawSignals=snap.signals||[]"):
            self.assertNotIn(token, runtime)


if __name__ == "__main__":
    unittest.main()
