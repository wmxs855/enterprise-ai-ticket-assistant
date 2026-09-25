"""运行后端接口场景，并生成可复现的评测报告。"""

from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient

from src.api import create_app


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "runtime" / "api_evaluation.db"
REPORT_PATH = PROJECT_ROOT / "reports" / "step07_api_evaluation.md"


def timed_request(request_function, *args, **kwargs):
    """发送一次请求，并返回响应与耗时毫秒数。"""

    started_at = perf_counter()
    response = request_function(*args, **kwargs)
    elapsed_ms = (perf_counter() - started_at) * 1000
    return response, elapsed_ms


def main():
    """执行健康、问答、创建、权限、审批和输入校验场景。"""

    DATABASE_PATH.unlink(missing_ok=True)
    client = TestClient(create_app(DATABASE_PATH))
    records = []

    def check(name, response, expected_status, condition):
        passed = response.status_code == expected_status and condition(response)
        records.append((name, response.status_code, expected_status, passed))

    response, health_time = timed_request(client.get, "/health")
    check("健康检查", response, 200, lambda item: item.json()["status"] == "ok")

    response, question_time = timed_request(
        client.post,
        "/v1/assistant/messages",
        json={"message": "一线城市住宿上限是多少", "user_id": "demo-user"},
    )
    check("知识问答含来源", response, 200, lambda item: bool(item.json()["sources"]))

    response, create_time = timed_request(
        client.post,
        "/v1/tickets",
        json={"description": "员工无法登录内部系统", "user_id": "demo-user"},
    )
    ticket_id = response.json()["id"]
    check("创建并分类工单", response, 201, lambda item: item.json()["category"] == "账号问题")

    response, permission_time = timed_request(
        client.get,
        f"/v1/tickets/{ticket_id}",
        params={"user_id": "other-user"},
    )
    check("拒绝越权查询", response, 403, lambda item: "无权" in item.json()["detail"])

    response, approval_time = timed_request(
        client.post,
        f"/v1/tickets/{ticket_id}/close",
        json={"user_id": "demo-user", "approved": False},
    )
    check("关闭需要确认", response, 409, lambda item: "approved" in item.json()["detail"])

    response, validation_time = timed_request(
        client.post,
        "/v1/tickets",
        json={"description": " ", "user_id": "demo-user"},
    )
    check("拒绝空描述", response, 422, lambda item: bool(item.json()["detail"]))
    client.close()

    passed_count = sum(record[3] for record in records)
    time_rows = [
        ("健康检查", health_time),
        ("知识问答", question_time),
        ("创建工单", create_time),
        ("权限拒绝", permission_time),
        ("审批阻断", approval_time),
        ("输入校验", validation_time),
    ]
    lines = [
        "# 第 7 步后端接口评测报告",
        "",
        f"- 通过场景：{passed_count}/{len(records)}",
        "- 运行方式：进程内测试客户端，不经过公网",
        "- 回答模式：离线证据回答",
        "",
        "## 功能结果",
        "",
        "| 场景 | 实际状态码 | 预期状态码 | 结果 |",
        "| --- | ---: | ---: | --- |",
    ]
    for name, actual, expected, passed in records:
        lines.append(f"| {name} | {actual} | {expected} | {'通过' if passed else '失败'} |")

    lines.extend(
        [
            "",
            "## 单次请求耗时",
            "",
            "这些数字只用于发现明显性能异常，不代表生产环境并发能力。",
            "",
            "| 场景 | 耗时（毫秒） |",
            "| --- | ---: |",
        ]
    )
    for name, elapsed_ms in time_rows:
        lines.append(f"| {name} | {elapsed_ms:.2f} |")

    lines.extend(
        [
            "",
            "## 限制",
            "",
            "- 当前用户编号和角色由请求方直接提交，只用于演示权限规则，不是真实身份认证。",
            "- 当前使用本地 SQLite 数据库，适合单机演示，不代表高并发生产部署能力。",
            "- 当前问答使用离线证据生成器，尚未验证用户自己的在线模型密钥。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"接口场景通过：{passed_count}/{len(records)}")
    print(f"评测报告：{REPORT_PATH}")


if __name__ == "__main__":
    main()
