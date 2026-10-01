import unittest
from unittest import mock

from modules import ui_v2_native
from modules import ui_v2_native_review


class UiV2NativeHumanVisualReviewTest(unittest.TestCase):
    def test_compare_finance_grid_is_stacked_full_width(self):
        source = ui_v2_native.NATIVE_STYLE
        patched = ui_v2_native_review._patched_style(source)
        self.assertIn(
            ".compare-finance-grid{grid-template-columns:1fr;align-items:start;margin-top:0}",
            patched,
        )
        self.assertNotIn(
            ".compare-finance-grid{align-items:start;margin-top:0}",
            patched,
        )
        self.assertIn(".compare-table-card .native-table{min-width:560px}", patched)

    def test_intelligence_first_style_modernizes_command_center_only(self):
        patched = ui_v2_native_review._patched_style(ui_v2_native.NATIVE_STYLE)
        self.assertIn(".intel-brief{", patched)
        self.assertIn(
            ".intelligence-first-command-center .pulse:not(.compare-pulse){display:none!important}",
            patched,
        )
        self.assertIn(
            ".intelligence-first-command-center .period-compare{display:block",
            patched,
        )
        self.assertIn(".intel-driver-track", patched)
        self.assertIn(".intel-side-block", patched)
        self.assertIn(".compare-pulse", patched)
        self.assertNotIn("font-family", ui_v2_native_review.INTELLIGENCE_FIRST_STYLE)

    def test_intelligence_first_runtime_is_evidence_bound(self):
        patched = ui_v2_native_review._patched_runtime(ui_v2_native.NATIVE_RUNTIME)
        for token in (
            "intelligenceBrief",
            "Tóm tắt vận hành",
            "Cần chú ý",
            "Nên kiểm tra",
            "anomalyEligibilityStatus",
            "reviewOptions",
            "Intelligence giữ fail-closed",
            "Hệ thống không tự đề xuất thay đổi",
            'if(S.scope==="compare")return;',
        ):
            self.assertIn(token, patched)
        self.assertNotIn("CHANGE_BID", ui_v2_native_review.INTELLIGENCE_FIRST_RUNTIME)
        self.assertNotIn("CHANGE_BUDGET", ui_v2_native_review.INTELLIGENCE_FIRST_RUNTIME)
        self.assertNotIn("CHANGE_PRICE", ui_v2_native_review.INTELLIGENCE_FIRST_RUNTIME)

    def test_review_wrapper_applies_v30_lineage_and_restores_module_state(self):
        original_style = ui_v2_native.NATIVE_STYLE
        original_runtime = ui_v2_native.NATIVE_RUNTIME
        original_version = ui_v2_native.NATIVE_PATCH_VERSION

        def fake_build(**kwargs):
            self.assertIn(
                ".compare-finance-grid{grid-template-columns:1fr;align-items:start;margin-top:0}",
                ui_v2_native.NATIVE_STYLE,
            )
            self.assertIn(".intel-brief{", ui_v2_native.NATIVE_STYLE)
            self.assertIn("intelligenceBrief", ui_v2_native.NATIVE_RUNTIME)
            self.assertEqual(
                ui_v2_native.NATIVE_PATCH_VERSION,
                ui_v2_native_review.INTELLIGENCE_FIRST_PATCH_VERSION,
            )
            from pathlib import Path
            out = Path(kwargs["output_dir"])
            out.mkdir(parents=True, exist_ok=True)
            (out / "command_center_v2_multi_shop_native_template.html").write_text(
                " ".join(
                    [
                        "intelligenceBrief",
                        "Tóm tắt vận hành",
                        "Cần chú ý",
                        "Nên kiểm tra",
                        "Intelligence giữ fail-closed",
                        "Chỉ số chính",
                        ".intel-brief{",
                        "intelligence-first-command-center",
                        "platform mutation",
                    ]
                ),
                encoding="utf-8",
            )
            return {"nativePatchVersion": ui_v2_native.NATIVE_PATCH_VERSION}

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                ui_v2_native, "build_native_v2_multi_shop", side_effect=fake_build
            ):
                result = ui_v2_native_review.build_native_v2_multi_shop(
                    payload_dir="payload",
                    v2_template_path="template",
                    output_dir=tmp,
                )

        self.assertEqual(
            result["nativePatchVersion"],
            ui_v2_native_review.INTELLIGENCE_FIRST_PATCH_VERSION,
        )
        self.assertEqual(
            ui_v2_native_review.INTELLIGENCE_FIRST_PATCH_VERSION,
            "native-production-shadow-mode-v30",
        )
        self.assertEqual(ui_v2_native.NATIVE_STYLE, original_style)
        self.assertEqual(ui_v2_native.NATIVE_RUNTIME, original_runtime)
        self.assertEqual(ui_v2_native.NATIVE_PATCH_VERSION, original_version)


if __name__ == "__main__":
    unittest.main()
