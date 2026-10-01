import unittest
from modules.multi_shop_staging import (
    normalize_product_performance, normalize_bi_shop_daily, normalize_bi_traffic, normalize_orders,
    parse_ads_csv, build_listing_records, run_catalog_resolver, qa_staging,
    normalize_listing_sales_info_export, audit_listing_catalog_snapshot,
)

SHOP="SHOP_2"

class MultiShopStagingTest(unittest.TestCase):
    def test_listing_sales_info_export_propagates_parent_and_validates_shop(self):
        rows=[
            ["et_title_product_id","et_title_product_name","et_title_variation_id","et_title_variation_name",
             "et_title_parent_sku","et_title_variation_sku","et_title_variation_price","ps_gtin_code","et_title_variation_stock"],
            ["sales_info","hash","0","1000000002","{}","","","",""],
            ["Product ID","Product Name","Variation ID","Variation Name","Parent SKU","SKU","Price","GTIN","Stock"],
            ["1","1","1","1","1","1","Mandatory","1","Mandatory"],
            ["1","1","1","1","1","1","1","1","1"],
            ["1","1","1","1","1","1","instruction","1","1"],
            ["50562805590","Yeu Kieu","400000000001","Pink","CB019","CB019-PIN-2L3D","432000","","12"],
            ["50562805590","Yeu Kieu","400000000002","Black","","CB019-BLA-2L3D","432000","","8"],
        ]
        products,variations,meta=normalize_listing_sales_info_export(
            rows,expected_shopee_shop_id="1000000002",shop_id=SHOP,
            snapshot_at="2026-09-23T10:23:05+07:00",source_name="mass_update_sales_info.xlsx")
        self.assertEqual(len(products),1)
        self.assertEqual(products[0]["observed_parent_sku"],"CB019")
        self.assertEqual({x["parent_sku"] for x in variations},{"CB019"})
        self.assertEqual({x["variation_sku"] for x in variations},{"CB019-PIN-2L3D","CB019-BLA-2L3D"})
        self.assertEqual(meta["parent_present_products"],1)
        self.assertEqual(audit_listing_catalog_snapshot(products,variations)["status"],"PASS")

    def test_listing_sales_info_export_rejects_wrong_shop(self):
        rows=[
            ["et_title_product_id","et_title_product_name","et_title_variation_id","et_title_variation_name",
             "et_title_parent_sku","et_title_variation_sku","et_title_variation_price","et_title_variation_stock"],
            ["sales_info","hash","0","1000000001","{}","","",""],
        ]
        with self.assertRaises(ValueError):
            normalize_listing_sales_info_export(
                rows,expected_shopee_shop_id="1000000002",shop_id=SHOP,snapshot_at="2026-09-23")

    def test_product_summary_and_variations_are_separated(self):
        rows=[
            ["Item ID","Product","Current Item Status","Variation ID","Variation Name","Current Variation Status","SKU","Parent SKU",
             "Sales (Placed Order) (VND)","Sales (Confirmed Order) (VND)","Product Impression","Product Clicks","CTR","Placed Order","Confirmed Order"],
            ["P1","Air S6","Normal","-","-","-","-","-","1.000.000","900.000",100,10,"10,00%",5,4],
            ["P1","Air S6","Normal","V1","Đen","Normal","GL027-BLA","",600000,500000,"-","-","-","-","-"],
        ]
        products,variations=normalize_product_performance(rows,shop_id=SHOP,data_month="2026-09")
        self.assertEqual(len(products),1); self.assertEqual(len(variations),1)
        self.assertEqual(products[0]["shop_id"],SHOP)
        self.assertEqual(products[0]["product_sku"],"")
        self.assertEqual(products[0]["placed_gmv_vnd"],1000000)
        self.assertEqual(products[0]["confirmed_gmv_vnd"],900000)
        self.assertEqual(variations[0]["variation_sku"],"GL027-BLA")

    def test_product_performance_vietnamese_headers_are_normalized(self):
        h=["Mã sản phẩm","Sản phẩm","Tình trạng sản phẩm hiện tại","Mã phân loại hàng",
           "Tên Phân Loại","Trạng thái phân loại sản phẩm hiện tại","SKU phân loại","SKU sản phẩm",
           "Doanh số (Đơn đã đặt) (VND)","Doanh số (Đơn đã xác nhận) (VND)",
           "Lượt xem sản phẩm","Lượt nhấp vào sản phẩm","CTR","Tỷ lệ chuyển đổi đơn (Đơn đã đặt)",
           "Tỷ lệ chuyển đổi đơn (Đơn đã xác nhận)","Đơn hàng đã đặt","Đơn đã xác nhận",
           "Sản phẩm (Đơn đã đặt)","Sản phẩm (Đơn đã xác nhận)","Người mua đã đặt hàng",
           "Người mua có đơn đã xác nhận","Tỷ lệ chuyển đổi (Đơn đã đặt)",
           "Tỷ lệ chuyển đổi (Đơn đã xác nhận)","Doanh thu trên mỗi đơn (Đơn đã đặt) (VND)",
           "Doanh thu trên mỗi đơn (Đơn đã xác nhận) (VND)"]
        rows=[
            h,
            ["P1","Air S4","Đang hoạt động","-","-","-","-","GL004","1.000.000","900.000",
             "100","10","10%","5%","4%","5","4","6","5","5","4","10%","8%","200.000","225.000"],
            ["P1","Air S4","Đang hoạt động","V1","Đen","Đang hoạt động","GL004-BLA","GL004",
             "600.000","500.000","-","-","-","-","-","-","-","3","2","3","2","-","-","-","-"],
        ]
        products,variations=normalize_product_performance(rows,shop_id=SHOP,data_month="2026-09")
        self.assertEqual(len(products),1)
        self.assertEqual(len(variations),1)
        self.assertEqual(products[0]["product_sku"],"GL004")
        self.assertEqual(products[0]["placed_gmv_vnd"],1000000)
        self.assertEqual(variations[0]["variation_sku"],"GL004-BLA")
        self.assertEqual(variations[0]["parent_sku"],"GL004")

    def test_bi_three_stage_daily(self):
        def sheet(sales,orders):
            return [
                ["","Date","Sales (VND)","Orders","Product Clicks","Visitors","Order Conversion Rate"],
                [0,"01-09-2026-02-09-2026",sales,orders,10,10,"10%"],
                [1,"",None,None,None,None,None],
                [2,"Date","Sales (VND)","Orders","Product Clicks","Visitors","Order Conversion Rate"],
                [3,"01-09-2026",sales/2,orders/2,5,5,"10%"],
                [4,"02-09-2026",sales/2,orders/2,5,5,"10%"],
            ]
        out=normalize_bi_shop_daily([sheet(1000,2),sheet(900,2),sheet(800,2)],shop_id=SHOP)
        self.assertEqual(len(out),6)
        self.assertEqual({x["order_stage"] for x in out},{"placed","confirmed","paid"})

    def test_bi_vietnamese_daily_headers_normalize_to_same_schema(self):
        header=["Ngày","Tổng doanh số (VND)","Doanh số không bao gồm trợ giá bởi Shopee",
                "Tổng số đơn hàng","Doanh số trên mỗi đơn hàng","Lượt nhấp vào sản phẩm",
                "Số lượt truy cập","Tỷ lệ chuyển đổi đơn hàng","Đơn đã hủy","Doanh số đơn hủy",
                "Đơn đã hoàn trả / hoàn tiền","Doanh số các đơn Trả hàng/Hoàn tiền",
                "số người mua","số người mua mới","số người mua hiện tại",
                "số người mua tiềm năng","Tỉ lệ quay lại của người mua"]
        def sheet(sales):
            return [
                header,
                ["01-09-2026-02-09-2026",str(sales*2),str(sales*1.5),"4","500","10","20","20%","0","0","0","0","4","3","1","2","25%"],
                [None]*len(header),
                header,
                ["01-09-2026",str(sales),"750","2","500","5","10","20%","0","0","0","0","2","1","1","1","25%"],
                ["02-09-2026",str(sales),"750","2","500","5","10","20%","0","0","0","0","2","1","1","1","25%"],
            ]
        out=normalize_bi_shop_daily([sheet(1000),sheet(900),sheet(800)],shop_id=SHOP)
        self.assertEqual(len(out),6)
        placed=[x for x in out if x["order_stage"]=="placed"]
        self.assertEqual(placed[0]["data_date"],"2026-09-01")
        self.assertEqual(placed[0]["gross_sales"],1000)
        self.assertEqual(placed[0]["order_count"],2)
        self.assertEqual(placed[0]["repeat_purchase_rate"],0.25)

    def test_bi_vietnamese_traffic_headers_are_supported(self):
        summary=[
            ["Ngày","Loại Đơn Hàng"],
            ["01-09-2026-02-09-2026","Đơn hàng đã đặt"],
            [None,None],
            ["Thẻ sản phẩm"],
            ["Nguồn lưu lượng","Tỷ lệ doanh số","Doanh số (VND)","Lượt hiển thị sản phẩm",
             "Lượt nhấp vào sản phẩm","Tổng số đơn hàng","Sản phẩm","CTR",
             "Tỷ lệ chuyển đổi đơn hàng","Doanh số trên mỗi đơn hàng","Người mua",
             "Lượt hiển thị sản phẩm duy nhất","Lượt nhấp sản phẩm duy nhất"],
            ["Tìm kiếm","50%","1000","100","10","2","3","10%","20%","500","2","80","8"],
        ]
        daily=[
            [None]*13,
            ["Thẻ sản phẩm"]+[None]*12,
            ["Nguồn lưu lượng","Tỷ lệ doanh số","Doanh số (VND)","Lượt hiển thị sản phẩm",
             "Lượt nhấp vào sản phẩm","Tổng số đơn hàng","Sản phẩm","CTR",
             "Tỷ lệ chuyển đổi đơn hàng","Doanh số trên mỗi đơn hàng","Người mua",
             "Lượt hiển thị sản phẩm duy nhất","Lượt nhấp sản phẩm duy nhất"],
            ["Thẻ sản phẩm","100%","1000","100","10","2","3","10%","20%","500","2","80","8"],
            ["01-09-2026","100%","500","50","5","1","2","10%","20%","500","1","40","4"],
        ]
        sheets=[[],[],[],summary,daily,[],summary,daily,[],summary,daily]
        d,m=normalize_bi_traffic(sheets,shop_id=SHOP,data_month="2026-09")
        self.assertEqual(len(d),3)
        self.assertEqual(len(m),3)
        self.assertTrue(all(x["shop_id"]==SHOP for x in d+m))
        self.assertEqual(d[0]["data_date"],"2026-09-01")
        self.assertEqual(m[0]["traffic_source"],"Search")

    def test_bi_traffic_preserves_channel_and_source_grain(self):
        header_product=["Nguồn lưu lượng","Tỷ lệ doanh số","Doanh số (VND)","Lượt hiển thị sản phẩm",
            "Lượt nhấp vào sản phẩm","Tổng số đơn hàng","Sản phẩm","CTR",
            "Tỷ lệ chuyển đổi đơn hàng","Doanh số trên mỗi đơn hàng","Người mua",
            "Lượt hiển thị sản phẩm duy nhất","Lượt nhấp sản phẩm duy nhất"]
        header_live=["Nguồn lưu lượng","Tỷ lệ doanh số","Doanh số (VND)","Lượt xem Livestream",
            "Lượt nhấp vào sản phẩm","Tổng số đơn hàng","Sản phẩm","CTR",
            "Tỷ lệ chuyển đổi đơn hàng","Doanh số trên mỗi đơn hàng","Người mua",
            "Người xem Livestream","Lượt nhấp sản phẩm duy nhất"]
        daily=[
            ["Thẻ sản phẩm"]+[None]*12,
            header_product,
            ["Thẻ sản phẩm","100%","1000","100","10","2","3","10%","20%","500","2","80","8"],
            ["01-09-2026","100%","500","50","5","1","2","10%","20%","500","1","40","4"],
            ["Tìm kiếm","50%","500","60","6","1","1","10%","16.67%","500","1","50","5"],
            ["01-09-2026","50%","250","30","3","0.5","1","10%","16.67%","500","1","25","2"],
            ["Live"]+[None]*12,
            header_live,
            ["Live","100%","300","20","8","1","2","40%","12.5%","300","1","10","5"],
            ["01-09-2026","100%","300","20","8","1","2","40%","12.5%","300","1","10","5"],
        ]
        summary=[
            ["Thẻ sản phẩm"]+[None]*12,
            header_product,
            ["Thẻ sản phẩm","100%","1000","100","10","2","3","10%","20%","500","2","80","8"],
            ["Tìm kiếm","50%","500","60","6","1","1","10%","16.67%","500","1","50","5"],
            ["Live"]+[None]*12,
            header_live,
            ["Live","100%","300","20","8","1","2","40%","12.5%","300","1","10","5"],
        ]
        sheets=[[],[],[],summary,daily,[],summary,daily,[],summary,daily]
        d,m=normalize_bi_traffic(sheets,shop_id=SHOP,data_month="2026-09")
        placed=[x for x in d if x["order_stage"]=="placed"]
        keys={(x["data_date"],x["channel_group"],x["traffic_source"]) for x in placed}
        self.assertEqual(len(keys),3)
        self.assertIn(("2026-09-01","Product Card","Product Card"),keys)
        self.assertIn(("2026-09-01","Product Card","Search"),keys)
        self.assertIn(("2026-09-01","Seller Live","Seller Live"),keys)
        self.assertTrue(any(x["traffic_source_raw"]=="Tìm kiếm" and x["traffic_source"]=="Search" for x in placed))
        self.assertTrue(any(x["exposure_metric"]=="live_views" for x in placed))
        monthly_keys={(x["channel_group"],x["traffic_source"]) for x in m if x["order_stage"]=="placed"}
        self.assertIn(("Product Card","Search"),monthly_keys)
        self.assertIn(("Seller Live","Seller Live"),monthly_keys)

    def test_orders_do_not_sum_repeated_order_fields(self):
        h=["Mã đơn hàng","Ngày đặt hàng","Trạng Thái Đơn Hàng","SKU sản phẩm","Tên sản phẩm","SKU phân loại hàng",
           "Tên phân loại hàng","Số lượng","Số lượng sản phẩm được hoàn trả","Tổng số tiền Người mua thanh toán",
           "Tổng giá trị đơn hàng (VND)","Mã giảm giá của Shop","Mã giảm giá của Shopee",
           "Tổng số tiền người mua thanh toán","Phí cố định","Phí Dịch Vụ","Phí xử lý giao dịch","Người Mua","Tỉnh/Thành phố"]
        rows=[h,
          ["O1","2026-09-01 10:00","Hoàn thành","P","Prod","V1","Black",1,0,100,180,20,0,160,10,5,3,"buyer","HCM"],
          ["O1","2026-09-01 10:00","Hoàn thành","P","Prod","V2","Pink",1,0,100,180,20,0,160,10,5,3,"buyer","HCM"]]
        orders,items=normalize_orders(rows,shop_id=SHOP,loaded_at="2026-09-22")
        self.assertEqual(len(orders),1); self.assertEqual(len(items),2)
        self.assertEqual(orders[0]["order_total_value"],180)

    def test_orders_capture_shopee_funded_subsidy(self):
        h=["Mã đơn hàng","Ngày đặt hàng","Trạng Thái Đơn Hàng","SKU sản phẩm","Tên sản phẩm","SKU phân loại hàng",
           "Tên phân loại hàng","Số lượng","Số lượng sản phẩm được hoàn trả","Tổng số tiền Người mua thanh toán",
           "Được Shopee trợ giá","Tổng giá trị đơn hàng (VND)","Mã giảm giá của Shop","Mã giảm giá của Shopee",
           "Tổng số tiền người mua thanh toán","Phí cố định","Phí Dịch Vụ","Phí xử lý giao dịch","Người Mua","Tỉnh/Thành phố"]
        rows=[h,["O1","2026-07-01 10:00","Hoàn thành","P","Prod","V1","Black",1,0,100,50,150,0,0,100,0,0,0,"buyer","HCM"]]
        orders,items=normalize_orders(rows,shop_id=SHOP,loaded_at="2026-09-25")
        self.assertEqual(len(orders),1)
        self.assertEqual(items[0]["shopee_subsidy"],50)

    def test_ads_all_campaign_rows_keep_product_scope(self):
        raw='''All CPC Ads Report - Shopee Vietnam
User Name,mall
Shop Name,Mall
Shop ID,1000000002
Report Creation Time,22/09/2026 15:51
Date Period,20/08/2026 - 20/08/2026

Sequence,Ad Name,Status,Ads Type,Product ID,Creative,Bidding Method,Placement,Start Date,End Date,Impression,Clicks,CTR,Add to Cart,Add to Cart Rate,Conversions,Direct Conversions,Conversion Rate,Direct Conversion Rate,Cost per Conversion,Cost per Direct Conversion,Items Sold,Direct Items Sold,GMV,Direct GMV,Expense,ROAS,Direct ROAS,ACOS,Direct ACOS,Product Impressions,Product Clicks,Product CTR,Voucher Amount,Vouchered Sales
1,A,Ongoing,Product Ad,P1,-,GMV Max,All,,,100,10,10%,1,10%,2,1,20%,10%,0,0,2,1,200,100,20,10,5,10%,20%,-,-,-,0,0
2,B,Ongoing,Product Ad,P1,-,GMV Max,All,,,50,5,10%,0,0%,1,0,20%,0%,0,0,1,0,100,0,10,10,0,10%,0%,-,-,-,0,0
3,Shop GMV Max,Ongoing,,-,-,Shop,All,,,40,4,10%,0,0%,0,0,0%,0%,0,0,0,0,0,0,5,0,0,0%,0%,-,-,-,0,0
'''
        rows,meta=parse_ads_csv(raw,expected_shopee_shop_id="1000000002",shop_id=SHOP)
        self.assertEqual(meta["data_date"],"2026-08-20")
        self.assertEqual(sum(1 for x in rows if x["ad_scope"]=="product"),2)
        self.assertEqual(sum(1 for x in rows if x["ad_scope"]=="shop"),1)

    def test_ads_vietnamese_export_is_normalized_and_product_scoped_by_product_id(self):
        raw='''Báo cáo Dịch vụ Hiển thị trả theo CPC - Shopee Việt Nam
Tên đăng nhập,unipalm
Tên gian hàng,Unipalm
Mã Người bán,1000000001
Thời gian tạo báo cáo,18/09/2026 11:14
Khoảng thời gian,01/09/2026 - 01/09/2026

Thứ tự,Tên Dịch vụ Hiển thị,Trạng thái,Loại Dịch vụ Hiển thị,Mã sản phẩm,Nội dung Dịch vụ Hiển thị,Phương thức đấu thầu,Vị trí,Ngày bắt đầu,Ngày kết thúc,Số lượt xem,Số lượt click,Tỷ Lệ Click,Thêm vào giỏ hàng,Tỷ lệ Thêm vào giỏ hàng,Lượt chuyển đổi,Lượt chuyển đổi trực tiếp,Tỷ lệ chuyển đổi,Tỷ lệ chuyển đổi trực tiếp,Chi phí cho mỗi lượt chuyển đổi,Chi phí cho mỗi lượt chuyển đổi trực tiếp,Sản phẩm đã bán,Sản phẩm đã bán trực tiếp,Doanh số,Doanh số trực tiếp,Chi phí,ROAS,ROAS trực tiếp,ACOS,ACOS trực tiếp,Lượt xem Sản phẩm,Lượt clicks Sản phẩm,Tỷ lệ Click Sản phẩm,Voucher Amount,Vouchered Sales
1,Shop GMV Max,Đã dừng,,-,-,GMV Max Auto Bidding (Shop),Tất cả,,,100,10,10%,0,0%,0,0,0%,0%,0,0,0,0,0,0,5000,0,0,0%,0%,-,-,-,0,0
2,Air S6,Đang diễn ra,Dịch vụ Hiển thị Sản phẩm,44616073433,-,Tối đa Doanh thu,Tất cả,,,200,20,10%,3,15%,2,1,10%,5%,1000,2000,2,1,200000,100000,20000,10,5,10%,20%,-,-,-,0,0
'''
        rows,meta=parse_ads_csv(raw,expected_shopee_shop_id="1000000001",shop_id="SHOP_VN")
        self.assertEqual(meta["shop_id"],"1000000001")
        self.assertEqual(meta["data_date"],"2026-09-01")
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["ad_scope"],"shop")
        self.assertEqual(rows[1]["ad_scope"],"product")
        self.assertEqual(rows[1]["product_id"],"44616073433")
        self.assertEqual(rows[1]["ad_spend"],20000)
        self.assertEqual(rows[1]["attributed_sales"],200000)

    def test_catalog_direct_parent_and_unmatched_are_observable(self):
        products=[{"shop_id":SHOP,"product_id":"P1","product_name":"Known","product_sku":"GL004"},
                  {"shop_id":SHOP,"product_id":"P2","product_name":"Missing","product_sku":""}]
        variations=[{"shop_id":SHOP,"product_id":"P1","variation_sku":"GL004-BLA","parent_sku":"GL004"},
                    {"shop_id":SHOP,"product_id":"P2","variation_sku":"X-1","parent_sku":""}]
        out=run_catalog_resolver(build_listing_records(products,variations))
        by={x["product_id"]:x for x in out}
        self.assertEqual(by["P1"]["status"],"DIRECT_PARENT")
        self.assertEqual(by["P2"]["status"],"UNMATCHED")

    def test_qa_reconciles_orders_and_bi_on_common_reliable_window(self):
        bi=[]
        for stage in ("placed","confirmed","paid"):
            bi.extend([
                {"shop_id":SHOP,"data_date":"2026-09-01","order_stage":stage,"gross_sales":100,"order_count":1},
                {"shop_id":SHOP,"data_date":"2026-09-02","order_stage":stage,"gross_sales":100,"order_count":1},
            ])
        orders=[
            {"shop_id":SHOP,"order_id":"O1","order_created_at":"2026-09-01 10:00:00","order_status":"Hoàn thành",
             "shop_voucher":0,"fixed_fee":0,"service_fee":0,"transaction_fee":0},
            {"shop_id":SHOP,"order_id":"O2","order_created_at":"2026-09-02 10:00:00","order_status":"Hoàn thành",
             "shop_voucher":0,"fixed_fee":0,"service_fee":0,"transaction_fee":0},
            {"shop_id":SHOP,"order_id":"O3","order_created_at":"2026-09-03 10:00:00","order_status":"Hoàn thành",
             "shop_voucher":0,"fixed_fee":0,"service_fee":0,"transaction_fee":0},
        ]
        items=[
            {"shop_id":SHOP,"order_id":"O1","order_item_seq":1,"item_buyer_payment":100},
            {"shop_id":SHOP,"order_id":"O2","order_item_seq":1,"item_buyer_payment":100},
            {"shop_id":SHOP,"order_id":"O3","order_item_seq":1,"item_buyer_payment":999},
        ]
        products=[{"shop_id":SHOP,"data_month":"2026-09","product_id":"P1"}]
        ads=[{"shop_id":SHOP,"data_date":"2026-09-01","ad_scope":"shop","ad_service_daily_key":"k1",
              "product_id":"","ad_spend":0,"attributed_sales":0}]
        qa=qa_staging(shop_id=SHOP,target_month="2026-09",orders=orders,order_items=items,
            products=products,variations=[],bi_shop=bi,ads=ads,
            ads_files=[{"data_date":"2026-09-01"}],catalog_resolutions=[])
        by={x["name"]:x for x in qa["checks"]}
        self.assertEqual(by["placed_orders_gmv_reconciliation"]["status"],"PASS")
        detail=by["placed_orders_gmv_reconciliation"]["detail"]
        self.assertEqual(detail["common_reliable_end"],"2026-09-02")
        self.assertEqual(detail["orders_distinct"],2)
        self.assertEqual(detail["bi_orders"],2)

    def _minimal_qa_inputs(self, *, bi_gmv, order_status="Hoàn thành", item_payment=100,
                           shopee_subsidy=0, order_total_value=100, shop_voucher=0):
        bi=[{"shop_id":SHOP,"data_date":"2026-07-01","order_stage":stage,
             "gross_sales":bi_gmv,"order_count":1}
            for stage in ("placed","confirmed","paid")]
        orders=[{"shop_id":SHOP,"order_id":"O1","order_created_at":"2026-07-01 10:00:00",
                 "order_status":order_status,"order_total_value":order_total_value,
                 "shop_voucher":shop_voucher,"fixed_fee":0,"service_fee":0,"transaction_fee":0}]
        items=[{"shop_id":SHOP,"order_id":"O1","order_item_seq":1,
                "item_buyer_payment":item_payment,"shopee_subsidy":shopee_subsidy}]
        products=[{"shop_id":SHOP,"data_month":"2026-07","product_id":"P1"}]
        ads=[{"shop_id":SHOP,"data_date":"2026-07-01","ad_scope":"shop",
              "ad_service_daily_key":"k1","product_id":"","ad_spend":0,"attributed_sales":0}]
        return dict(
            shop_id=SHOP,target_month="2026-07",orders=orders,order_items=items,
            products=products,variations=[],bi_shop=bi,ads=ads,
            ads_files=[{"data_date":"2026-07-01"}],catalog_resolutions=[]
        )

    def test_qa_reconciles_shopee_funded_subsidy(self):
        qa=qa_staging(**self._minimal_qa_inputs(
            bi_gmv=150,item_payment=100,shopee_subsidy=50,order_total_value=100))
        check={x["name"]:x for x in qa["checks"]}["placed_orders_gmv_reconciliation"]
        self.assertEqual(check["status"],"PASS")
        self.assertEqual(
            check["detail"]["selected_proxy_mode"],
            "ITEM_PAYMENT_PLUS_SHOPEE_SUBSIDY_MINUS_SHOP_VOUCHER")
        self.assertEqual(check["detail"]["shopee_subsidy_total"],50)

    def test_qa_reconciles_cancelled_order_total_value_candidate(self):
        qa=qa_staging(**self._minimal_qa_inputs(
            bi_gmv=270,order_status="Đã hủy",item_payment=290,
            order_total_value=270,shopee_subsidy=0))
        check={x["name"]:x for x in qa["checks"]}["placed_orders_gmv_reconciliation"]
        self.assertEqual(check["status"],"PASS")
        self.assertEqual(
            check["detail"]["selected_proxy_mode"],
            "CANCELLED_ORDER_TOTAL_VALUE_FALLBACK")
        self.assertEqual(check["detail"]["cancellation_fallback_orders"],1)

    def test_qa_still_blocks_unexplained_gmv_gap(self):
        qa=qa_staging(**self._minimal_qa_inputs(
            bi_gmv=200,item_payment=100,shopee_subsidy=0,order_total_value=100))
        check={x["name"]:x for x in qa["checks"]}["placed_orders_gmv_reconciliation"]
        self.assertEqual(check["status"],"FAIL")
        self.assertFalse(qa["production_write_allowed"])

    def test_qa_blocks_zero_product_performance_rows(self):
        bi=[{"shop_id":SHOP,"data_date":"2026-09-01","order_stage":stage,"gross_sales":100,"order_count":1}
            for stage in ("placed","confirmed","paid")]
        orders=[{"shop_id":SHOP,"order_id":"O1","order_created_at":"2026-09-01 10:00:00",
                 "order_status":"Hoàn thành","shop_voucher":0,"fixed_fee":0,"service_fee":0,"transaction_fee":0}]
        items=[{"shop_id":SHOP,"order_id":"O1","order_item_seq":1,"item_buyer_payment":100}]
        ads=[{"shop_id":SHOP,"data_date":"2026-09-01","ad_scope":"shop","ad_service_daily_key":"k1",
              "product_id":"","ad_spend":0,"attributed_sales":0}]
        qa=qa_staging(shop_id=SHOP,target_month="2026-09",orders=orders,order_items=items,
            products=[],variations=[],bi_shop=bi,ads=ads,
            ads_files=[{"data_date":"2026-09-01"}],catalog_resolutions=[])
        failed=[x["name"] for x in qa["checks"] if x["status"]=="FAIL"]
        self.assertIn("product_performance_target_month_present",failed)

    def test_qa_blocks_when_target_month_ads_are_absent(self):
        bi=[{"shop_id":SHOP,"data_date":"2026-09-01","order_stage":stage,"gross_sales":100,"order_count":1}
            for stage in ("placed","confirmed","paid")]
        orders=[{"shop_id":SHOP,"order_id":"O1","order_created_at":"2026-09-01 10:00:00",
                 "order_status":"Hoàn thành","shop_voucher":0,"fixed_fee":0,"service_fee":0,"transaction_fee":0}]
        items=[{"shop_id":SHOP,"order_id":"O1","order_item_seq":1,"item_buyer_payment":100}]
        qa=qa_staging(shop_id=SHOP,target_month="2026-09",orders=orders,order_items=items,
            products=[],variations=[],bi_shop=bi,ads=[],ads_files=[],catalog_resolutions=[])
        self.assertEqual(qa["status"],"FAIL")
        self.assertFalse(qa["production_write_allowed"])
        self.assertIn("ads_target_month_present",[x["name"] for x in qa["checks"] if x["status"]=="FAIL"])

if __name__=="__main__":
    unittest.main()
