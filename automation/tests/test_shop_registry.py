import json
import tempfile
import unittest
from pathlib import Path

from modules.shop_registry import enabled_shops, get_shop, load_shop_registry, select_shops


def shop(key, sid, platform_id):
    return {
        "shop_key":key,
        "shop_id":sid,
        "shopee_shop_id":platform_id,
        "display_name":key.upper(),
        "platform":"shopee",
        "enabled":True,
        "raw_root_candidates":[
            {"type":"folder_id","folder_id":f"folder-{key}","priority":100}
        ],
    }


class ShopRegistryTest(unittest.TestCase):
    def write_registry(self,payload):
        tmp=tempfile.NamedTemporaryFile("w",encoding="utf-8",suffix=".json",delete=False)
        with tmp:
            json.dump(payload,tmp)
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return tmp.name

    def test_registry_has_no_fixed_shop_count(self):
        payload={"version":"2.0","shops":[
            shop("one","SHOP_1","1001"),
            shop("two","SHOP_2","1002"),
            shop("three","SHOP_3","1003"),
        ]}
        registry=load_shop_registry(self.write_registry(payload))
        self.assertEqual(len(enabled_shops(registry)),3)
        self.assertEqual([x["shop_key"] for x in select_shops(registry,["all"])],["one","two","three"])
        self.assertEqual(get_shop(registry,"three")["shop_id"],"SHOP_3")

    def test_disabled_shop_is_not_selected_by_all(self):
        a=shop("one","SHOP_1","1001")
        b=shop("two","SHOP_2","1002"); b["enabled"]=False
        registry=load_shop_registry(self.write_registry({"version":"2.0","shops":[a,b]}))
        self.assertEqual([x["shop_key"] for x in enabled_shops(registry)],["one"])
        with self.assertRaises(ValueError):
            select_shops(registry,["two"])

    def test_duplicate_identity_is_rejected(self):
        a=shop("one","SHOP_1","1001")
        b=shop("two","SHOP_1","1002")
        with self.assertRaises(ValueError):
            load_shop_registry(self.write_registry({"version":"2.0","shops":[a,b]}))

    def test_child_folder_root_is_generic_not_shop_specific(self):
        a=shop("one","SHOP_1","1001")
        a["raw_root_candidates"]=[
            {"type":"child_folder","parent_folder_id":"root","folder_name":"brand_shop_one","priority":100},
            {"type":"folder_id","folder_id":"legacy-root","priority":10},
        ]
        registry=load_shop_registry(self.write_registry({"version":"2.0","shops":[a]}))
        roots=registry["shops"][0]["raw_root_candidates"]
        self.assertEqual(roots[0]["type"],"child_folder")
        self.assertEqual(roots[1]["type"],"folder_id")


if __name__=="__main__":
    unittest.main()
