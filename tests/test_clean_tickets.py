"""检查工单数据清洗规则。"""

import unittest

from src.clean_tickets import RAW_DATA_PATH, clean_tickets, load_tickets


class CleanTicketsTest(unittest.TestCase):
    """工单清洗流程的自动测试。"""

    @classmethod
    def setUpClass(cls):
        raw_data = load_tickets(RAW_DATA_PATH)
        cls.clean_data, cls.metrics = clean_tickets(raw_data)

    def test_expected_row_count(self):
        """清洗后应该剩余九条有效记录。"""

        self.assertEqual(len(self.clean_data), 9)

    def test_ticket_id_is_unique(self):
        """工单编号必须唯一。"""

        self.assertTrue(self.clean_data["ticket_id"].is_unique)

    def test_required_fields_have_no_missing_values(self):
        """关键字段不应该存在缺失值。"""

        required_columns = [
            "ticket_id",
            "title",
            "description",
            "creator",
            "category",
            "priority",
            "created_at",
        ]
        missing_count = int(self.clean_data[required_columns].isna().sum().sum())
        self.assertEqual(missing_count, 0)

    def test_category_names_are_standardized(self):
        """简称“账号”应该统一为“账号问题”。"""

        categories = set(self.clean_data["category"])
        self.assertNotIn("账号", categories)
        self.assertIn("账号问题", categories)

    def test_quality_metrics_are_recorded(self):
        """删除和填充的数据数量应该被记录。"""

        self.assertEqual(self.metrics["exact_duplicates_removed"], 1)
        self.assertEqual(self.metrics["duplicate_ids_removed"], 1)
        self.assertEqual(self.metrics["missing_descriptions_removed"], 1)
        self.assertEqual(self.metrics["invalid_dates_removed"], 1)


if __name__ == "__main__":
    unittest.main()

