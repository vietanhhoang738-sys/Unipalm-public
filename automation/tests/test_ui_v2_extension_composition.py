import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules import ui_v2_native as native
from modules import ui_v2_extension_composition as composition


class NativeV2ExtensionCompositionTest(unittest.TestCase):
    def test_plan_is_explicit_ordered_and_single_bridge(self):
        self.assertEqual(composition.NATIVE_EXTENSION_COMPOSITION_VERSION, "native-v2-extension-composition-v1")
        self.assertEqual(composition.PLAN.compatibility_bridge_count, 1)
        self.assertEqual(len(composition.EXTENSION_ORDER), len(set(composition.EXTENSION_ORDER)))
        self.assertEqual(composition.EXTENSION_ORDER[0], "intelligence_first_operator_copy")
        self.assertEqual(composition.EXTENSION_ORDER[-1], "ads_smart_issue_registry")
        self.assertEqual(composition.PLAN.native_patch_version, "native-ads-financial-v38")

    def test_bundle_bridge_uses_immutable_base_reference(self):
        payload = {"destinations": {"product": {"p": 1}, "ads": {"a": 2}}}
        with patch.object(composition, "_BASE_BUNDLE_FROM_PAYLOAD", return_value={"base": True}) as base:
            with patch.object(native, "_bundle_from_payload", side_effect=AssertionError("must not recurse")):
                bundle = composition._bundle_with_extensions(payload)
        base.assert_called_once_with(payload)
        self.assertTrue(bundle["base"])
        self.assertEqual(bundle["productDestination"], {"p": 1})
        self.assertEqual(bundle["adsDestination"], {"a": 2})

    def test_integrated_desk_preserves_all_locked_gates_without_raw_signals(self):
        runtime = composition.compose_integrated_financial_runtime({})
        self.assertIn("snap.dynamicDiagnosis||{}", runtime)
        self.assertIn("diag.items||[]", runtime)
        self.assertNotIn("const rawSignals=snap.signals||[]", runtime)
        self.assertIn("Chẩn đoán chỉ xuất hiện khi hai kỳ có bối cảnh bán hàng tương đồng.", runtime)
        self.assertIn("Độ bền chỉ được xác nhận bằng các cửa sổ độc lập cùng scope và cùng bối cảnh.", runtime)
        self.assertIn("Ứng viên Smart Issue chỉ được đánh dấu", runtime)
        self.assertIn("Smart Issue chỉ được mở hoặc đổi trạng thái sau một review event rõ ràng của operator", runtime)
        self.assertIn("supportWindowCount", runtime)
        self.assertIn("smartIssueCandidate", runtime)
        self.assertIn("humanReview", runtime)
        self.assertIn("Chi tiêu Ads", runtime)
        self.assertIn("THAM KHẢO", runtime)

    def test_integrated_card_is_structured_once_not_nested_transform_chain(self):
        card = composition._integrated_signal_card()
        self.assertEqual(card.count("signals.map("), 1)
        self.assertEqual(card.count("ads-desk-persistence"), 1)
        self.assertEqual(card.count("ads-desk-smart-candidate"), 1)
        self.assertEqual(card.count("ads-desk-review-state"), 1)
        self.assertIn("LINKED_ISSUE", card)
        self.assertIn("REOPEN_REVIEW_REQUIRED", card)
        self.assertIn("DEFERRED", card)
        self.assertIn("DISMISSED", card)

    def test_style_composition_keeps_extension_order_and_does_not_mutate_base(self):
        before_style = native.NATIVE_STYLE
        style = composition.compose_effective_style()
        self.assertIs(native.NATIVE_STYLE, before_style)
        self.assertLess(style.index(".product-destination{"), style.index(".ads-destination{"))
        self.assertLess(style.index(".ads-fin-kpis{"), style.index(".ads-desk-gate{"))
        self.assertLess(style.index(".ads-desk-gate{"), style.index(".ads-desk-persistence{"))
        self.assertLess(style.index(".ads-desk-persistence{"), style.index(".ads-desk-smart-candidate{"))
        self.assertLess(style.index(".ads-desk-smart-candidate{"), style.index(".ads-desk-review-state{"))

    def test_canonical_builder_calls_base_native_once_and_restores_globals(self):
        with tempfile.TemporaryDirectory() as td:
            payload_dir = Path(td) / "payload"
            payload_dir.mkdir()
            (payload_dir / "ui_payload.json").write_text("{}", encoding="utf-8")

            original_bundle = native._bundle_from_payload
            original_style = native.NATIVE_STYLE
            original_runtime = native.NATIVE_RUNTIME
            original_version = native.NATIVE_PATCH_VERSION
            fake_result = {
                "nativePatchVersion": composition.PLAN.native_patch_version,
                "sourcePayloadBuildFingerprint": "p",
                "sourceSemanticFingerprint": "s",
                "sourceV2TemplateSha256": "v",
                "v2CompatibilityPatchVersion": "c",
                "nativeBuildFingerprint": "b",
                "selectedShopCount": 0,
                "comparePairCount": 0,
                "safety": {},
            }
            validators = [
                (composition._operator, "_validate_semantic_artifact"),
                (composition._product, "_validate_product_artifact"),
                (composition._short, "_validate_v36_artifact"),
                (composition._ads, "_validate_ads_artifact"),
                (composition._polish, "_validate_polished_artifact"),
                (composition._diagnosis, "_validate_dynamic_diagnosis_artifact"),
                (composition._persistence, "_validate_persistence_artifact"),
                (composition._candidate, "_validate_smart_issue_candidate_artifact"),
                (composition._registry, "_validate_registry_artifact"),
                (composition, "_validate_composition_artifact"),
            ]
            stack = []
            try:
                stack.extend([
                    patch.object(composition._product, "_validate_product_payload"),
                    patch.object(composition._ads, "_validate_ads_payload"),
                    patch.object(composition, "compose_effective_style", return_value="STYLE"),
                    patch.object(composition, "compose_effective_runtime", return_value="RUNTIME"),
                    patch.object(composition._short, "build_short_name_map", return_value={}),
                    patch.object(composition._ads, "build_ads_short_name_map", return_value={}),
                    patch.object(native, "build_native_v2_multi_shop", return_value=fake_result),
                ])
                for owner, attr in validators:
                    stack.append(patch.object(owner, attr))
                mocks = [p.start() for p in stack]
                base_mock = mocks[6]
                result = composition.build_native_v2_multi_shop(
                    payload_dir=payload_dir,
                    v2_template_path=Path(td) / "template.html",
                    output_dir=Path(td) / "out",
                )
                base_mock.assert_called_once()
                self.assertTrue(result["nativeExtensionCompositionReady"])
                self.assertFalse(result["legacyNestedWrapperBuildPathUsed"])
            finally:
                for p in reversed(stack):
                    p.stop()

            self.assertIs(native._bundle_from_payload, original_bundle)
            self.assertEqual(native.NATIVE_STYLE, original_style)
            self.assertEqual(native.NATIVE_RUNTIME, original_runtime)
            self.assertEqual(native.NATIVE_PATCH_VERSION, original_version)

    def test_primary_builder_source_does_not_call_nested_wrapper_builders(self):
        source = inspect.getsource(composition.build_native_v2_multi_shop)
        self.assertIn("_native.build_native_v2_multi_shop", source)
        self.assertNotIn("_registry.build_native_v2_multi_shop", source)
        self.assertNotIn("_candidate.build_native_v2_multi_shop", source)
        self.assertNotIn("_persistence.build_native_v2_multi_shop", source)
        self.assertNotIn("_diagnosis.build_native_v2_multi_shop", source)


if __name__ == "__main__":
    unittest.main()
