import unittest
from modules.catalog_resolver import ListingRecord, infer_family_from_master, resolve_listing


class CatalogResolverTest(unittest.TestCase):
    def test_direct_parent_is_authoritative(self):
        target=ListingRecord("SHOP_2","1","Cool S3","MS003",{"MS003-BLA","MS003-PIN"})
        r=resolve_listing(target,[])
        self.assertEqual(r.status,"DIRECT_PARENT")
        self.assertEqual(r.resolved_parent_sku,"MS003")

    def test_reference_parent_requires_variation_evidence(self):
        ref=ListingRecord("SHOP_1","10","Cool S3 UV","MS003",{"MS003-BLA","MS003-PIN","MS003-LGR"})
        target=ListingRecord("SHOP_2","20","Unipalm Cool S3 UV","",{"MS003-BLA","MS003-PIN","MS003-LGR"})
        r=resolve_listing(target,[ref])
        self.assertEqual(r.status,"AUTO_REFERENCE_PARENT")
        self.assertEqual(r.resolved_parent_sku,"MS003")

    def test_multiple_reference_shops_support_same_parent_instead_of_reducing_margin(self):
        refs=[
            ListingRecord("SHOP_1","10","Cool S3 UV","MS003",{"MS003-BLA","MS003-PIN","MS003-LGR"}),
            ListingRecord("SHOP_3","30","Unipalm Cool S3","MS003",{"MS003-BLA","MS003-PIN","MS003-LGR"}),
        ]
        target=ListingRecord("SHOP_2","20","Unipalm Cool S3 UV","",{"MS003-BLA","MS003-PIN","MS003-LGR"})
        r=resolve_listing(target,refs)
        self.assertEqual(r.status,"AUTO_REFERENCE_PARENT")
        self.assertEqual(r.resolved_parent_sku,"MS003")
        self.assertEqual(r.evidence["reference_support_shop_count"],2)

    def test_same_shop_listing_is_not_reference_evidence(self):
        ref=ListingRecord("SHOP_2","99","Cool S3 UV","MS003",{"MS003-BLA","MS003-PIN","MS003-LGR"})
        target=ListingRecord("SHOP_2","20","Cool S3 UV","",{"MS003-BLA","MS003-PIN","MS003-LGR"})
        r=resolve_listing(target,[ref])
        self.assertEqual(r.status,"UNMATCHED")

    def test_title_only_never_auto_writes_parent(self):
        ref=ListingRecord("SHOP_1","10","Cặp Đôi Yêu Kiều Cool S2 Air S4","CB019",set())
        target=ListingRecord("SHOP_2","20","Cặp Đôi Yêu Kiều Cool S2 Air S4","",set())
        r=resolve_listing(target,[ref])
        self.assertEqual(r.status,"REVIEW_REFERENCE")
        self.assertEqual(r.resolved_parent_sku,"")

    def test_master_family_uses_exact_variation_lookup_not_prefix(self):
        target=ListingRecord("SHOP_2","20","Air S6","",{"GL027-BLA","GL027-DGR","GL028-BLA","GL029-BLD"})
        family_map={"GL027-BLA":"GL027","GL027-DGR":"GL027"}
        r=resolve_listing(target,[],family_by_sellable_sku=family_map)
        self.assertEqual(r.status,"FAMILY_ONLY")
        self.assertEqual(r.canonical_family_key,"GL027")
        self.assertEqual(r.resolved_parent_sku,"")

    def test_legacy_prefix_collision_does_not_create_false_family(self):
        fam,share,votes=infer_family_from_master(
            {"GL021-BLA","GL021-DGN"},
            {"GL021-BLA":"GL021","GL021-DGN":"AIR_F1_LEGACY"},
            min_votes=2,
        )
        self.assertEqual(fam,"")
        self.assertEqual(votes["GL021"],1)
        self.assertEqual(votes["AIR_F1_LEGACY"],1)

    def test_ambiguous_reference_stays_review(self):
        refs=[
            ListingRecord("SHOP_1","1","Cool S3","MS003",{"MS009-PIN","MS009-DGR"}),
            ListingRecord("SHOP_3","2","Combo 2 Cool S3","MS003-CB2",{"MS009-PIN","MS009-DGR"}),
        ]
        target=ListingRecord("SHOP_2","3","Cool S3","",{"MS009-PIN","MS009-DGR"})
        r=resolve_listing(target,refs)
        self.assertNotEqual(r.status,"AUTO_REFERENCE_PARENT")


if __name__=="__main__":
    unittest.main()
