import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modules import ui_v2_native_review
from modules import ui_v2_operator_copy_review


class UiV2OperatorCopyReviewTest(unittest.TestCase):
    def test_operator_copy_removes_backend_wording_from_visible_runtime(self):
        polished = ui_v2_operator_copy_review._polish_runtime(
            ui_v2_native_review.INTELLIGENCE_FIRST_RUNTIME
        )
        self.assertIn("Chưa đủ bằng chứng", polished)
        self.assertIn("Chưa có bước kiểm tra được đề xuất", polished)
        self.assertIn(
            "Đọc diễn biến và yếu tố tác động trước khi xem số liệu chi tiết.",
            polished,
        )
        self.assertIn("không thay đổi dữ liệu trên sàn", polished)
        self.assertNotIn('badge:"Evidence gate đang chặn"', polished)
        self.assertNotIn('title:"Chưa phát sinh hành động cần review"', polished)
        self.assertNotIn("Intelligence giữ fail-closed", polished)
        self.assertNotIn("platform mutation", polished)

    def test_semantic_artifact_validation_accepts_machine_safety_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = " ".join(
                list(ui_v2_operator_copy_review._STRUCTURAL_ARTIFACT_TOKENS)
                + list(ui_v2_operator_copy_review._SEMANTIC_SAFETY_TOKENS)
            )
            Path(tmp, "command_center_v2_multi_shop_native_template.html").write_text(
                html,
                encoding="utf-8",
            )
            ui_v2_operator_copy_review._validate_semantic_artifact(tmp)

    def test_semantic_artifact_validation_rejects_missing_no_mutation_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            tokens = list(ui_v2_operator_copy_review._STRUCTURAL_ARTIFACT_TOKENS)
            tokens += [
                x
                for x in ui_v2_operator_copy_review._SEMANTIC_SAFETY_TOKENS
                if x != '"platformMutationAllowed":false'
            ]
            Path(tmp, "command_center_v2_multi_shop_native_template.html").write_text(
                " ".join(tokens),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "semantic safety checks missing"):
                ui_v2_operator_copy_review._validate_semantic_artifact(tmp)

    def test_v32_wrapper_uses_semantic_gate_and_restores_native_state(self):
        native = ui_v2_native_review._native
        original_style = native.NATIVE_STYLE
        original_runtime = native.NATIVE_RUNTIME
        original_version = native.NATIVE_PATCH_VERSION

        def fake_build(**kwargs):
            self.assertIn(".intel-brief{", native.NATIVE_STYLE)
            self.assertIn("intelligenceBrief", native.NATIVE_RUNTIME)
            self.assertIn("Chưa đủ bằng chứng", native.NATIVE_RUNTIME)
            self.assertNotIn("Intelligence giữ fail-closed", native.NATIVE_RUNTIME)
            self.assertEqual(
                native.NATIVE_PATCH_VERSION,
                ui_v2_operator_copy_review.OPERATOR_COPY_PATCH_VERSION,
            )
            out = Path(kwargs["output_dir"])
            out.mkdir(parents=True, exist_ok=True)
            html = " ".join(
                list(ui_v2_operator_copy_review._STRUCTURAL_ARTIFACT_TOKENS)
                + list(ui_v2_operator_copy_review._SEMANTIC_SAFETY_TOKENS)
            )
            (out / "command_center_v2_multi_shop_native_template.html").write_text(
                html,
                encoding="utf-8",
            )
            return {"nativePatchVersion": native.NATIVE_PATCH_VERSION}

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(native, "build_native_v2_multi_shop", side_effect=fake_build):
                result = ui_v2_operator_copy_review.build_native_v2_multi_shop(
                    payload_dir="payload",
                    v2_template_path="template",
                    output_dir=tmp,
                )

        self.assertEqual(
            result["nativePatchVersion"],
            "native-production-shadow-mode-v32",
        )
        self.assertEqual(native.NATIVE_STYLE, original_style)
        self.assertEqual(native.NATIVE_RUNTIME, original_runtime)
        self.assertEqual(native.NATIVE_PATCH_VERSION, original_version)


if __name__ == "__main__":
    unittest.main()
