import unittest

from modules import ui_v2_product_compact_signals as compact


class UiV2ProductCompactSignalsTest(unittest.TestCase):
    def test_patch_version(self):
        self.assertEqual(
            compact.PRODUCT_COMPACT_SIGNAL_PATCH_VERSION,
            "native-product-intelligence-v35-compact-signals",
        )

    def test_signal_layout_is_conditional_and_horizontal(self):
        style = compact.COMPACT_SIGNAL_STYLE
        self.assertIn(".product-hero:has(.product-signal)", style)
        self.assertIn('grid-template-areas:"summary state" "signals signals"', style)
        self.assertIn("grid-template-columns:repeat(4,minmax(0,1fr))", style)
        self.assertIn(".product-hero:has(.product-signal) .product-hero-side{display:contents}", style)
        self.assertIn("grid-column:1/-1", style)
        self.assertNotIn("font-family", style)

    def test_responsive_signal_layout(self):
        style = compact.COMPACT_SIGNAL_STYLE
        self.assertIn("@media(max-width:1180px)", style)
        self.assertIn("repeat(2,minmax(0,1fr))", style)
        self.assertIn("@media(max-width:680px)", style)
        self.assertIn("grid-template-columns:1fr", style)

    def test_status_title_matches_visible_signal_mix(self):
        runtime = compact.COMPACT_SIGNAL_RUNTIME
        self.assertIn('(intel.signals||[]).slice(0,4)', runtime)
        self.assertIn('x.type==="Vấn đề"', runtime)
        self.assertIn('x.type==="Cơ hội"', runtime)
        self.assertIn('" cần chú ý · "+opportunities+" cơ hội"', runtime)
        self.assertIn('if(intel.status!=="READY")return', runtime)


if __name__ == "__main__":
    unittest.main()
