import unittest

from engines.invoice_parser import InvoiceParser


class InvoiceParserTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = InvoiceParser()

    def test_parse_text_keeps_field_alignment(self) -> None:
        with open("D:/project/PyCharmMiscProject/demo/data/sample_invoice.txt", encoding="utf-8") as file:
            text = file.read()

        result = self.parser.parse_text(text)

        self.assertEqual(result["buyer_name"], "华东演示科技有限公司")
        self.assertEqual(result["buyer_tax_id"], "91310000123456789A")
        self.assertEqual(result["buyer_bank_account"], "中国银行上海张江支行 123456789012")
        self.assertEqual(result["seller_name"], "深圳万达凯旋科技有限公司")
        self.assertEqual(result["seller_tax_id"], "91420111565593675Y")

    def test_parse_text_extracts_line_items(self) -> None:
        with open("D:/project/PyCharmMiscProject/demo/data/sample_invoice.txt", encoding="utf-8") as file:
            text = file.read()

        result = self.parser.parse_text(text)

        self.assertEqual(result["line_item_count"], 2)
        self.assertEqual(result["line_items"][0]["item_name"], "*计算机配套产品*台式工作站")
        self.assertEqual(result["line_items"][1]["spec_model"], "27寸")
        self.assertEqual(result["tax_amount"], 1222.0)
        self.assertEqual(result["total_amount"], 10622.0)

    def test_parse_pdf_extracts_split_line_item(self) -> None:
        result = self.parser.parse_pdf("D:/project/PyCharmMiscProject/demo/example/增值税电子普票.pdf")

        self.assertEqual(result["buyer_name"], "中央财经大学")
        self.assertEqual(result["buyer_tax_id"], "121000004000018468")
        self.assertEqual(result["seller_name"], "深圳万达凯旋科技有限公司")
        self.assertEqual(result["seller_tax_id"], "91420111565593675Y")
        self.assertEqual(result["line_item_count"], 1)
        self.assertEqual(result["line_items"][0]["item_name"], "*计算机配套产品*电脑电源")
        self.assertEqual(result["line_items"][0]["spec_model"], "GX850")
        self.assertEqual(result["line_items"][0]["amount"], 715.43)
        self.assertEqual(result["tax_amount"], 93.01)
        self.assertEqual(result["total_amount"], 808.44)

    def test_parse_text_extracts_vertical_seller_block_fields(self) -> None:
        text = """增值税电子普通发票
发票号码：23990001
开票日期：2026年03月18日
购
买
方
信
息
名称：中央财经大学
统一社会信用代码/纳税人识别号：121000004000018468
地址、电话：北京市海淀区学院南路39号 010-62288332
开户行及账号：中国银行北京学院南路支行 123456789012
销
售
方
信
息
名称：深圳万达凯旋科技有限公司
统一社会信用代码/纳税人识别号：91420111565593675Y
地址、电话：深圳市南山区科创大道66号 0755-87654321
开户行及账号：招商银行深圳科技园支行 987654321098
项目名称 规格型号 单位 数量 单价 金额 税率 税额
*计算机配套产品*显示器 27寸 台 1 1200.00 1200.00 13% 156.00
合计 ¥1200.00 ¥156.00
价税合计（大写）壹仟叁佰伍拾陆圆整 （小写）¥1356.00
"""

        result = self.parser.parse_text(text)

        self.assertEqual(result["buyer_name"], "中央财经大学")
        self.assertEqual(result["buyer_tax_id"], "121000004000018468")
        self.assertEqual(result["seller_name"], "深圳万达凯旋科技有限公司")
        self.assertEqual(result["seller_tax_id"], "91420111565593675Y")
        self.assertEqual(result["seller_address_phone"], "深圳市南山区科创大道66号 0755-87654321")
        self.assertEqual(result["seller_bank_account"], "招商银行深圳科技园支行 987654321098")
        self.assertEqual(result["line_item_count"], 1)

    def test_parse_text_remark_does_not_swallow_issuer(self) -> None:
        text = """增值税专用发票
发票号码：12345678
备注：对应合同编号HT20260318001；三单匹配正常；设备已验收。
收款人：李会计
复核：王复核
开票人：赵开票
"""

        result = self.parser.parse_text(text)

        self.assertEqual(result["remarks"], "对应合同编号HT20260318001；三单匹配正常；设备已验收。")
        self.assertEqual(result["payee"], "李会计")
        self.assertEqual(result["reviewer"], "王复核")
        self.assertEqual(result["issuer"], "赵开票")

    def test_parse_text_vertical_remark_marker_does_not_swallow_issuer(self) -> None:
        text = """电子发票（普通发票）
发票号码：25952000000162424462
开票日期：2025年08月08日
备
注
开票人：黄宽育
黄宽育
"""

        result = self.parser.parse_text(text)

        self.assertEqual(result["remarks"], "")
        self.assertEqual(result["issuer"], "黄宽育")


if __name__ == "__main__":
    unittest.main()
