import unittest

from modules.product_short_name import RULE_VERSION, resolve_short_product_name


class ProductShortNameTest(unittest.TestCase):
    def test_rule_version(self):
        self.assertEqual(RULE_VERSION, "product-short-name-v1")

    def test_glove_air_s2(self):
        r = resolve_short_product_name(
            "Găng tay chống nắng chống tia UV 99% UPF 50+ Unipalm Air S2 cho nữ chạy xe hở đầu ngón tay cảm ứng",
            "GL002",
            "1",
        )
        self.assertEqual(r["shortName"], "Găng tay Air S2")
        self.assertEqual(r["confidence"], "HIGH")

    def test_mask_cool_s2(self):
        r = resolve_short_product_name(
            "Khẩu trang chống tia UV Unipalm Cool S2 , chống nắng UPF 50+ Vải lụa băng mềm, có gọng 2 lớp",
            "MS001",
            "2",
        )
        self.assertEqual(r["shortName"], "Khẩu trang Cool S2")

    def test_sleeve_air_f2(self):
        r = resolve_short_product_name(
            "Ống tay chống nắng chống tia UV găng tay dáng dài cho nữ Unipalm Air F2 vải su mát không đường may",
            "GL009",
            "3",
        )
        self.assertEqual(r["shortName"], "Ống tay Air F2")

    def test_pair_infers_mask_family_for_bare_s3(self):
        r = resolve_short_product_name(
            "Cặp Đôi Hiện Đại Khẩu trang chống tia UV che kín mặt S3 UPF 50+ & Găng tay chống nắng Air S4 Unipalm",
            "CB004",
            "4",
        )
        self.assertEqual(r["shortName"], "Cặp đôi Cool S3 + Air S4")

    def test_combo_keeps_quantity(self):
        r = resolve_short_product_name(
            "[Hỏa Tốc] Combo 2 Khẩu trang che kín mặt Unipalm Cool S3 UPF 50+ chống tia UV Vải lụa băng mềm mại",
            "MS003-CB2",
            "5",
        )
        self.assertEqual(r["shortName"], "Combo 2 Khẩu trang Cool S3")

    def test_plus_model(self):
        r = resolve_short_product_name(
            "[Mới] Găng tay chống nắng chống tia UV Unipalm Air S1 Plus cho nữ chạy xe vải lụa băng thoáng khí",
            "GL032",
            "6",
        )
        self.assertEqual(r["shortName"], "Găng tay Air S1 Plus")

    def test_male_variant(self):
        r = resolve_short_product_name(
            "Khẩu trang chống tia UV Unipalm Cool S2 cho nam, UPF 50+ vải lụa băng mềm, có gọng 2 lớp",
            "MS002-MEN",
            "7",
        )
        self.assertEqual(r["shortName"], "Khẩu trang Cool S2 · Nam")

    def test_deleted_product_uses_sku(self):
        r = resolve_short_product_name(
            "Không thể lấy thông tin sản phẩm do bị xóa",
            "CB020",
            "8",
        )
        self.assertEqual(r["shortName"], "Sản phẩm đã xóa · CB020")

    def test_unknown_structure_falls_back_to_full_title(self):
        full = "Một sản phẩm mới chưa có taxonomy chính thức"
        r = resolve_short_product_name(full, "ZZ001", "9")
        self.assertEqual(r["shortName"], full)
        self.assertEqual(r["confidence"], "FALLBACK")


if __name__ == "__main__":
    unittest.main()
