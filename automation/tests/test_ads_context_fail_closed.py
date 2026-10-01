import unittest

from modules.ads_context_qualification import qualify_context_pair


class AdsContextFailClosedTest(unittest.TestCase):
    def test_comparison_not_ready_is_context_unknown_and_never_diagnostic(self):
        current = {
            "dateCount": 1,
            "matchingSignature": ["PLATFORM|shopee|PAYDAY|1|1"],
        }
        reference = {
            "dateCount": 0,
            "matchingSignature": [],
        }
        result = qualify_context_pair(
            current,
            reference,
            comparison_status="INSUFFICIENT_COMPARISON_HISTORY",
        )
        self.assertEqual(result["status"], "CONTEXT_UNKNOWN")
        self.assertEqual(result["reason"], "COMPARISON_NOT_READY")
        self.assertFalse(result["strongDirectionalDiagnosisEligible"])
        self.assertFalse(result["causalClaimEligible"])
        self.assertFalse(result["automaticAlertEligible"])
        self.assertFalse(result["automaticActionEligible"])


if __name__ == "__main__":
    unittest.main()
