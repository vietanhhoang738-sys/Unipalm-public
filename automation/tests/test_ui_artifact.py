import json
import tempfile
import unittest
from pathlib import Path

from modules.ui_artifact import DATA_MARKER, build_dual_ui_wrapper, inject_payload


class UiArtifactTest(unittest.TestCase):
    def test_payload_injection_is_exact_and_mock_free(self):
        html="<script>"+DATA_MARKER+"</script>"
        out=inject_payload(html,{"commandCenter":{"status":"READY"}})
        self.assertIn("window.UNIPALM_DATA=",out)
        self.assertNotIn(DATA_MARKER,out)

    def test_dual_wrapper_contains_v2_and_v1_runtime_switch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            v2=p/"v2.html"; v1=p/"v1.html"; out=p/"index.html"
            v2.write_text("<script>"+DATA_MARKER+"</script><h1>V2</h1>",encoding="utf-8")
            v1.write_text("<script>"+DATA_MARKER+"</script><h1>V1</h1>",encoding="utf-8")
            meta=build_dual_ui_wrapper(
                payload={"commandCenter":{"status":"READY"}},
                v2_template_path=v2,v1_template_path=v1,output_path=out,
                access_key="test-secret",build_id="test-build",
            )
            text=out.read_text(encoding="utf-8")
            self.assertEqual(meta["defaultUi"],"v2")
            self.assertEqual(meta["fallbackQuery"],"?ui=v1")
            self.assertIn('id="p-v2"',text)
            self.assertIn('id="p-v1"',text)
            self.assertIn("requested==='v1'?'v1':'v2'",text)
            self.assertIn('meta name="unipalm-ui-default" content="v2"',text)


if __name__=="__main__":
    unittest.main()
