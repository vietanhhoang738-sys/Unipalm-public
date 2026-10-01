import io
import unittest
import zipfile

from openpyxl import Workbook

from multi_shop_staging_runner import (
    select_orders_source_folder,
    xlsx_first_sheet_rows_tolerant,
)


class TolerantXlsxReaderTest(unittest.TestCase):
    def _broken_dimension_sheet2_xlsx(self):
        wb=Workbook()
        ws=wb.active
        ws.title="orders"
        ws.append(["Mã đơn hàng","Ngày đặt hàng","Trạng Thái Đơn Hàng"])
        ws.append(["260901ABC","2026-09-01 10:00","Hoàn thành"])
        buf=io.BytesIO()
        wb.save(buf)
        wb.close()

        src=zipfile.ZipFile(io.BytesIO(buf.getvalue()),"r")
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                name=info.filename
                data=src.read(name)
                if name=="xl/worksheets/sheet1.xml":
                    text=data.decode("utf-8")
                    text=text.replace('dimension ref="A1:C2"','dimension ref="A1"')
                    dst.writestr("xl/worksheets/sheet2.xml",text.encode("utf-8"))
                elif name=="xl/_rels/workbook.xml.rels":
                    text=data.decode("utf-8")
                    text=text.replace("worksheets/sheet1.xml","worksheets/sheet2.xml")
                    dst.writestr(info,text.encode("utf-8"))
                else:
                    dst.writestr(info,data)
        src.close()
        return out.getvalue()

    def test_resolves_first_sheet_by_relationship_and_ignores_bad_dimension(self):
        rows=xlsx_first_sheet_rows_tolerant(self._broken_dimension_sheet2_xlsx())
        self.assertEqual(rows[0][:3],["Mã đơn hàng","Ngày đặt hàng","Trạng Thái Đơn Hàng"])
        self.assertEqual(rows[1][:3],["260901ABC","2026-09-01 10:00","Hoàn thành"])

    def test_orders_source_prefers_snapshot_then_legacy_final(self):
        class FakeDrive:
            pass

        mapping={
            "MONTH":[
                {"id":"FINAL","name":"final","mimeType":"application/vnd.google-apps.folder"},
                {"id":"SNAP1","name":"snapshot_2026-08-05","mimeType":"application/vnd.google-apps.folder"},
                {"id":"SNAP2","name":"snapshot_2026-08-28","mimeType":"application/vnd.google-apps.folder"},
            ],
            "OLD":[
                {"id":"FINAL2","name":"final","mimeType":"application/vnd.google-apps.folder"},
            ],
        }
        import multi_shop_staging_runner as runner
        original=runner.children
        try:
            runner.children=lambda drive,folder_id:mapping.get(folder_id,[])
            self.assertEqual(
                select_orders_source_folder(FakeDrive(),"MONTH","2026-08")["id"],
                "SNAP2",
            )
            self.assertEqual(
                select_orders_source_folder(FakeDrive(),"OLD","2026-01")["id"],
                "FINAL2",
            )
        finally:
            runner.children=original


if __name__=="__main__":
    unittest.main()
