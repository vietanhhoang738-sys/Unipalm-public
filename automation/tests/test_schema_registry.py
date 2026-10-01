import unittest

from modules.schema_registry import (
    SchemaContractError,
    audit_schema,
    header_fingerprint,
    require_schema,
)


class SchemaRegistryTest(unittest.TestCase):
    def test_known_aliases_resolve(self):
        audit=audit_schema(
            "ads_rows",
            ["Thứ tự","Tên Dịch vụ Hiển thị","Mã sản phẩm","Số lượt xem","Số lượt click","Doanh số","Chi phí"],
            source_name="ads_vi.csv",
        )
        self.assertEqual(audit["missing_required_fields"],[])
        self.assertEqual(audit["resolved_fields"]["gmv"],"Doanh số")
        self.assertEqual(audit["resolved_fields"]["expense"],"Chi phí")

    def test_added_unknown_column_warns_but_does_not_fail(self):
        audit=audit_schema(
            "ads_rows",
            ["Sequence","Ad Name","Product ID","Impression","Clicks","GMV","Expense","Campaign Objective"],
            source_name="ads_new.csv",
        )
        self.assertEqual(audit["status"],"WARN")
        self.assertIn("Campaign Objective",audit["unknown_columns"])
        self.assertEqual(audit["missing_required_fields"],[])

    def test_unknown_rename_of_required_field_blocks(self):
        with self.assertRaises(SchemaContractError) as ctx:
            require_schema(
                "ads_rows",
                ["Sequence","Ad Name","Product ID","Impression","Clicks","Revenue","Expense"],
                source_name="ads_changed.csv",
            )
        self.assertIn("gmv",ctx.exception.audit["missing_required_fields"])
        self.assertIn("Revenue",ctx.exception.audit["unknown_columns"])

    def test_column_order_does_not_change_fingerprint(self):
        a=["Sequence","Ad Name","Product ID","Impression","Clicks","GMV","Expense"]
        b=list(reversed(a))
        self.assertEqual(header_fingerprint(a),header_fingerprint(b))

    def test_whitespace_is_normalized_but_case_change_is_observable(self):
        a=header_fingerprint(["GMV","Expense"])
        b=header_fingerprint(["  GMV ","Expense"])
        c=header_fingerprint(["gmv","Expense"])
        self.assertEqual(a,b)
        self.assertNotEqual(a,c)

    def test_orders_exact_case_disambiguates_two_different_payment_fields(self):
        audit=audit_schema(
            "orders",
            [
                "Mã đơn hàng","Ngày đặt hàng","Trạng Thái Đơn Hàng","Số lượng",
                "Tổng số tiền Người mua thanh toán","Tổng giá trị đơn hàng (VND)",
                "Tổng số tiền người mua thanh toán","Phí cố định","Phí Dịch Vụ",
                "Phí xử lý giao dịch",
            ],
            source_name="orders.xlsx",
        )
        self.assertEqual(audit["missing_required_fields"],[])
        self.assertEqual(
            audit["resolved_fields"]["item_buyer_payment"],
            "Tổng số tiền Người mua thanh toán",
        )
        self.assertEqual(
            audit["resolved_fields"]["buyer_total_payment"],
            "Tổng số tiền người mua thanh toán",
        )

    def test_no_fuzzy_semantic_guess(self):
        audit=audit_schema(
            "ads_rows",
            ["Sequence","Ad Name","Product ID","Impression","Clicks","Doanh thu","Expense"],
            source_name="ads_semantic_unknown.csv",
        )
        self.assertIn("gmv",audit["missing_required_fields"])
        self.assertIn("Doanh thu",audit["unknown_columns"])


if __name__=="__main__":
    unittest.main()
