"""通过真实网络请求结构检查后端服务的输入、输出和状态码。"""

from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from src.api import create_app


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIRECTORY = PROJECT_ROOT / "data" / "test_api_runtime"


class ApiTest(unittest.TestCase):
    """后端服务自动测试。"""

    def setUp(self):
        TEST_DIRECTORY.mkdir(parents=True, exist_ok=True)
        self.database_path = TEST_DIRECTORY / f"{self._testMethodName}.db"
        self.database_path.unlink(missing_ok=True)
        self.client = TestClient(create_app(self.database_path))

    def tearDown(self):
        self.client.close()
        self.database_path.unlink(missing_ok=True)
        if TEST_DIRECTORY.exists() and not any(TEST_DIRECTORY.iterdir()):
            TEST_DIRECTORY.rmdir()

    def create_ticket(self, user_id="user-a"):
        return self.client.post(
            "/v1/tickets",
            json={"description": "员工无法登录内部系统", "user_id": user_id},
        )

    def test_health_check(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_demo_page_is_available(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("企业知识库与智能工单助手", response.text)
        self.assertIn("/static/app.js", response.text)

    def test_demo_assets_are_available(self):
        stylesheet = self.client.get("/static/styles.css")
        script = self.client.get("/static/app.js")

        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("--teal", stylesheet.text)
        self.assertEqual(script.status_code, 200)
        self.assertIn("/v1/assistant/messages", script.text)

    def test_knowledge_question_returns_source(self):
        response = self.client.post(
            "/v1/assistant/messages",
            json={"message": "一线城市住宿上限是多少", "user_id": "user-a"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "knowledge_question")
        self.assertTrue(response.json()["sources"])

    def test_create_and_query_own_ticket(self):
        created = self.create_ticket()

        self.assertEqual(created.status_code, 201)
        ticket = created.json()
        self.assertEqual(ticket["category"], "账号问题")
        response = self.client.get(
            f"/v1/tickets/{ticket['id']}",
            params={"user_id": "user-a"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "待处理")

    def test_other_user_is_forbidden(self):
        ticket_id = self.create_ticket("user-a").json()["id"]

        response = self.client.get(
            f"/v1/tickets/{ticket_id}",
            params={"user_id": "user-b"},
        )
        self.assertEqual(response.status_code, 403)

    def test_close_requires_approval(self):
        ticket_id = self.create_ticket().json()["id"]

        waiting = self.client.post(
            f"/v1/tickets/{ticket_id}/close",
            json={"user_id": "user-a", "approved": False},
        )
        self.assertEqual(waiting.status_code, 409)

        closed = self.client.post(
            f"/v1/tickets/{ticket_id}/close",
            json={"user_id": "user-a", "approved": True},
        )
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.json()["status"], "已关闭")

    def test_blank_description_is_rejected(self):
        response = self.client.post(
            "/v1/tickets",
            json={"description": "   ", "user_id": "user-a"},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
