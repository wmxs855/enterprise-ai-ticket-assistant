"""检查工单工作流的路由、权限、审批和审计行为。"""

from pathlib import Path
import shutil
import unittest

from src.ticket_database import TicketRepository
from src.workflow import WorkflowEngine


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIRECTORY = PROJECT_ROOT / "data" / "test_runtime"


class WorkflowTest(unittest.TestCase):
    """智能工单工作流自动测试。"""

    def setUp(self):
        TEST_DIRECTORY.mkdir(parents=True, exist_ok=True)
        self.database_path = TEST_DIRECTORY / f"{self._testMethodName}.db"
        if self.database_path.exists():
            self.database_path.unlink()
        self.repository = TicketRepository(self.database_path)
        self.engine = WorkflowEngine(repository=self.repository)

    def tearDown(self):
        if self.database_path.exists():
            self.database_path.unlink()
        if TEST_DIRECTORY.exists() and not any(TEST_DIRECTORY.iterdir()):
            TEST_DIRECTORY.rmdir()

    def create_account_ticket(self, user_id="user-a"):
        """创建一张用于后续测试的账号工单。"""

        return self.engine.handle(
            "创建工单：员工无法登录内部系统",
            user_id=user_id,
        )

    def test_knowledge_question_uses_knowledge_tool(self):
        result = self.engine.handle("一线城市住宿上限是多少", "user-a")

        self.assertEqual(result["intent"], "knowledge_question")
        self.assertIn("五百元", result["message"])
        self.assertTrue(result["sources"])

    def test_create_ticket_predicts_category_and_priority(self):
        result = self.create_account_ticket()

        self.assertEqual(result["ticket"]["category"], "账号问题")
        self.assertEqual(result["ticket"]["priority"], "紧急")
        self.assertEqual(result["ticket"]["status"], "待处理")

    def test_user_can_query_own_ticket(self):
        created = self.create_account_ticket()
        ticket_id = created["ticket"]["id"]

        result = self.engine.handle(
            f"查询工单 {ticket_id} 的状态",
            user_id="user-a",
        )
        self.assertIn("待处理", result["message"])

    def test_user_cannot_query_other_users_ticket(self):
        created = self.create_account_ticket(user_id="user-a")
        ticket_id = created["ticket"]["id"]

        result = self.engine.handle(
            f"查询工单 {ticket_id} 的状态",
            user_id="user-b",
        )
        self.assertIn("无权查看", result["message"])

    def test_close_requires_approval_and_writes_audit_log(self):
        created = self.create_account_ticket()
        ticket_id = created["ticket"]["id"]

        waiting = self.engine.handle(
            f"关闭工单 {ticket_id}",
            user_id="user-a",
        )
        self.assertTrue(waiting["requires_approval"])

        closed = self.engine.handle(
            f"关闭工单 {ticket_id}",
            user_id="user-a",
            approved=True,
        )
        self.assertEqual(closed["ticket"]["status"], "已关闭")
        self.assertEqual(len(self.repository.list_audit_logs()), 2)

    def test_unknown_question_does_not_create_ticket_automatically(self):
        result = self.engine.handle("公司食堂今天吃什么", "user-a")

        self.assertIn("创建工单", result["message"])
        self.assertEqual(self.repository.list_audit_logs(), [])


if __name__ == "__main__":
    unittest.main()

