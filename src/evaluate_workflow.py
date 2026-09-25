"""运行智能工单工作流的代表性场景并生成报告。"""

from pathlib import Path

from src.workflow import WorkflowEngine
from src.ticket_database import TicketRepository


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "runtime" / "workflow_evaluation.db"
REPORT_PATH = PROJECT_ROOT / "reports" / "step06_workflow_evaluation.md"


def run_evaluation():
    """执行咨询、创建、查询、越权和审批场景。"""

    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

    repository = TicketRepository(DATABASE_PATH)
    engine = WorkflowEngine(repository=repository)
    scenarios = []

    knowledge_result = engine.handle(
        "银行卡退款一般多久可以到账",
        user_id="user-a",
    )
    scenarios.append(
        (
            "知识咨询",
            "三个到七个工作日" in knowledge_result["message"]
            and bool(knowledge_result["sources"]),
            knowledge_result,
        )
    )

    unknown_result = engine.handle("公司食堂今天吃什么", user_id="user-a")
    scenarios.append(
        (
            "未知问题转人工提示",
            "创建工单" in unknown_result["message"],
            unknown_result,
        )
    )

    create_result = engine.handle(
        "创建工单：员工无法登录内部系统",
        user_id="user-a",
    )
    ticket_id = create_result["ticket"]["id"]
    scenarios.append(
        (
            "创建并自动分类工单",
            create_result["ticket"]["category"] == "账号问题"
            and create_result["ticket"]["priority"] == "紧急",
            create_result,
        )
    )

    query_result = engine.handle(
        f"查询工单 {ticket_id} 的进度",
        user_id="user-a",
    )
    scenarios.append(
        (
            "创建人查询自己的工单",
            "待处理" in query_result["message"],
            query_result,
        )
    )

    denied_result = engine.handle(
        f"查询工单 {ticket_id} 的进度",
        user_id="user-b",
    )
    scenarios.append(
        (
            "阻止普通用户越权查询",
            "无权查看" in denied_result["message"],
            denied_result,
        )
    )

    approval_result = engine.handle(
        f"关闭工单 {ticket_id}",
        user_id="user-a",
    )
    scenarios.append(
        (
            "关闭前要求人工确认",
            approval_result["requires_approval"],
            approval_result,
        )
    )

    close_result = engine.handle(
        f"关闭工单 {ticket_id}",
        user_id="user-a",
        approved=True,
    )
    scenarios.append(
        (
            "批准后关闭并记录审计",
            close_result["ticket"]["status"] == "已关闭"
            and len(repository.list_audit_logs()) == 2,
            close_result,
        )
    )

    return scenarios


def build_report(scenarios):
    """把场景结果转换成报告。"""

    passed_count = sum(passed for _, passed, _ in scenarios)
    rows = []
    for name, passed, result in scenarios:
        status = "通过" if passed else "失败"
        trace = " → ".join(result["trace"])
        rows.append(
            f"| {name} | {result['message']} | {trace} | {status} |"
        )

    return f"""# 第 6 步智能工单工作流评测报告

## 汇总

- 场景总数：{len(scenarios)}
- 通过场景：{passed_count}
- 数据库：SQLite 本地数据库，文件位于 D 盘项目目录
- 在线模型：未使用，知识问答采用离线原文模式

## 场景结果

| 场景 | 结果信息 | 执行轨迹 | 状态 |
|---|---|---|---|
{chr(10).join(rows)}

## 安全与工程设计

- 普通用户只能查看和关闭自己的工单。
- 管理员角色可以查询业务范围内的其他工单。
- 关闭操作必须先获得明确批准。
- 创建和关闭操作写入审计日志。
- 数据库使用参数化查询，用户文字不会被当作数据库命令执行。
- 数据库临时错误只进行有限次数重试。
- 知识库没有依据时不会自动创建工单，而是先征求用户意愿。
"""


def main():
    """执行场景评测并保存报告。"""

    scenarios = run_evaluation()
    report = build_report(scenarios)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    passed_count = sum(passed for _, passed, _ in scenarios)
    print("智能工单工作流评测完成")
    print(f"通过场景：{passed_count} / {len(scenarios)}")
    print(f"评测报告：{REPORT_PATH}")


if __name__ == "__main__":
    main()

