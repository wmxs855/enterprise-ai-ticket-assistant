"""检查工单基础规则是否符合预期。"""

import unittest

from src.ticket_basics import classify_priority, create_ticket


class TicketBasicsTest(unittest.TestCase):
    """工单基础功能的自动测试。"""

    def test_login_failure_is_urgent(self):
        """包含“无法登录”的问题应该被判断为紧急。"""

        result = classify_priority("员工无法登录内部系统")
        self.assertEqual(result, "紧急")

    def test_general_question_is_normal(self):
        """普通制度咨询不应该被判断为紧急。"""

        result = classify_priority("请问报销制度在哪里查看")
        self.assertEqual(result, "普通")

    def test_created_ticket_contains_required_fields(self):
        """新工单应该包含后续处理需要的基础字段。"""

        ticket = create_ticket(10, "支付问题", "客户支付失败", "测试用户")

        self.assertEqual(ticket["id"], 10)
        self.assertEqual(ticket["priority"], "紧急")
        self.assertFalse(ticket["is_closed"])


if __name__ == "__main__":
    unittest.main()

