import tempfile
import unittest
from pathlib import Path

from modules.dashboard_access_key_rotation import (
    _decrypt_html,
    _parse_wrapper,
    rotate_wrapper_text,
    validate_next_key,
)
from modules.ui_artifact import build_dual_ui_wrapper


class DashboardAccessKeyRotationTests(unittest.TestCase):
    def _build_wrapper(self, root: Path, key: str) -> str:
        v2 = root / "v2.html"
        v1 = root / "v1.html"
        out = root / "index.html"
        v2.write_text("<html><body>V2/*__UNIPALM_DATA__*/</body></html>", encoding="utf-8")
        v1.write_text("<html><body>V1/*__UNIPALM_DATA__*/</body></html>", encoding="utf-8")
        build_dual_ui_wrapper(
            payload={"shop":"test","orders":123},
            v2_template_path=v2,
            v1_template_path=v1,
            output_path=out,
            access_key=key,
            build_id="rotation-test-build",
        )
        return out.read_text(encoding="utf-8")

    def test_rotation_preserves_plaintext_and_rejects_old_key(self):
        current = "legacy-test-key"
        next_key = "N3xt-Key-For-Public-Ciphertext-2026-ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        with tempfile.TemporaryDirectory() as tmp:
            wrapper = self._build_wrapper(Path(tmp), current)
            before_meta, before_payloads = _parse_wrapper(wrapper)
            before_plaintext = {
                ui: _decrypt_html(before_payloads[ui], before_meta[ui], current)
                for ui in ("v2", "v1")
            }

            rotated, audit = rotate_wrapper_text(
                wrapper, current_key=current, next_key=next_key
            )
            after_meta, after_payloads = _parse_wrapper(rotated)
            after_plaintext = {
                ui: _decrypt_html(after_payloads[ui], after_meta[ui], next_key)
                for ui in ("v2", "v1")
            }

            self.assertEqual(before_plaintext, after_plaintext)
            self.assertEqual(audit["status"], "PASS")
            self.assertTrue(audit["plaintextPreserved"])
            self.assertTrue(audit["currentKeyRejectedAfterRotation"])
            for ui in ("v2", "v1"):
                with self.assertRaises(Exception):
                    _decrypt_html(after_payloads[ui], after_meta[ui], current)

    def test_next_key_gate_is_fail_closed(self):
        with self.assertRaises(ValueError):
            validate_next_key("short-key")
        with self.assertRaises(ValueError):
            validate_next_key("A" * 64)
        validate_next_key(
            "Random-Looking-Next-Key-2026-abcdefghijklmnopqrstuvwxyz-0123456789"
        )

    def test_rotation_refuses_same_key(self):
        key = "Same-Key-But-Strong-Enough-ABCDEFGHIJKLMNOPQRSTUVWXYZ-0123456789"
        with tempfile.TemporaryDirectory() as tmp:
            wrapper = self._build_wrapper(Path(tmp), key)
            with self.assertRaises(ValueError):
                rotate_wrapper_text(wrapper, current_key=key, next_key=key)


if __name__ == "__main__":
    unittest.main()
