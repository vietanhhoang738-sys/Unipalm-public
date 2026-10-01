import unittest

from modules.product_ranking import build_priority, rank_signals


class ProductRankingTest(unittest.TestCase):
    def test_material_product_can_outrank_tiny_extreme_drop(self):
        material=build_priority(
            recent_gmv=70_000_000,previous_gmv=110_000_000,recent_days=92,previous_days=92,
            recent_shop_gmv=700_000_000,gmv_delta=-.36,persistence_months=2,
            pace_delta=-.15,pace_support=1,confidence=.90,
        )
        tiny=build_priority(
            recent_gmv=1_000_000,previous_gmv=5_000_000,recent_days=92,previous_days=92,
            recent_shop_gmv=700_000_000,gmv_delta=-.80,persistence_months=2,
            pace_delta=-.50,pace_support=1,confidence=.95,
        )
        signals=[
            {"type":"Vấn đề","productId":"BIG","confidence":.90,**material},
            {"type":"Vấn đề","productId":"TINY","confidence":.95,**tiny},
        ]
        ranked=rank_signals(signals)["problems"]
        self.assertEqual(ranked[0]["productId"],"BIG")
        self.assertEqual(ranked[0]["rankWithinType"],1)

    def test_problem_and_opportunity_rank_separately(self):
        signals=[
            {"type":"Vấn đề","productId":"P","priorityScore":70,"structuralImpactValue":-10,"confidence":.8},
            {"type":"Cơ hội","productId":"O","priorityScore":90,"structuralImpactValue":20,"confidence":.9},
        ]
        r=rank_signals(signals)
        self.assertEqual(r["problems"][0]["rankWithinType"],1)
        self.assertEqual(r["opportunities"][0]["rankWithinType"],1)


if __name__=="__main__":
    unittest.main()
