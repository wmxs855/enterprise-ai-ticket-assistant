"""根据用户意图选择知识问答或工单工具。"""

import argparse
from pathlib import Path
import re

import joblib

from src.answer_generator import KnowledgeAssistant, OfflineEvidenceGenerator
from src.ticket_basics import classify_priority
from src.ticket_database import (
    DEFAULT_DATABASE_PATH,
    PermissionDeniedError,
    TicketRepository,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "ticket_category_model.joblib"


class TicketCategoryPredictor:
    """加载已经训练的模型并预测工单类别。"""

    def __init__(self, model_path=MODEL_PATH):
        if not Path(model_path).exists():
            raise FileNotFoundError(
                "没有找到工单分类模型，请先运行 src.train_classifier。"
            )
        artifact = joblib.load(model_path)
        self.model = artifact["model"]

    def predict(self, description):
        """返回一条工单描述的预测类别。"""

        return self.model.predict([description])[0]


def determine_intent(message):
    """根据明确关键词判断用户希望执行的任务。"""

    if "关闭工单" in message:
        return "close_ticket"

    has_ticket_word = "工单" in message
    has_query_word = any(word in message for word in ["查询", "查看", "状态", "进度"])
    if has_ticket_word and has_query_word:
        return "query_ticket"

    if any(word in message for word in ["创建工单", "提交工单", "人工报修"]):
        return "create_ticket"

    return "knowledge_question"


def extract_ticket_id(message):
    """从文字中提取第一个连续数字作为工单编号。"""

    match = re.search(r"\d+", message)
    return int(match.group()) if match else None


def extract_description(message):
    """移除创建指令，留下真实问题描述。"""

    description = message
    for prefix in ["创建工单", "提交工单", "人工报修"]:
        description = description.replace(prefix, "", 1)
    return description.lstrip("：:，, ").strip()


class WorkflowEngine:
    """执行意图判断、工具调用、权限控制和结果组织。"""

    def __init__(
        self,
        repository=None,
        knowledge_assistant=None,
        category_predictor=None,
    ):
        self.repository = repository or TicketRepository()
        self.knowledge_assistant = knowledge_assistant or KnowledgeAssistant(
            OfflineEvidenceGenerator()
        )
        self.category_predictor = category_predictor or TicketCategoryPredictor()

    def handle(self, message, user_id, user_role="user", approved=False):
        """处理一条用户消息并返回可解释的执行结果。"""

        intent = determine_intent(message)
        trace = [f"识别意图：{intent}"]

        if intent == "knowledge_question":
            trace.append("调用工具：知识库问答")
            answer_result = self.knowledge_assistant.ask(message)

            if answer_result["found"]:
                return {
                    "intent": intent,
                    "message": answer_result["answer"],
                    "sources": answer_result["sources"],
                    "requires_approval": False,
                    "trace": trace,
                }

            return {
                "intent": intent,
                "message": (
                    f"{answer_result['answer']} 如果需要人工处理，请回复："
                    "创建工单：加上你的问题描述。"
                ),
                "sources": [],
                "requires_approval": False,
                "trace": trace,
            }

        if intent == "create_ticket":
            description = extract_description(message)
            if not description:
                return {
                    "intent": intent,
                    "message": "请补充需要处理的问题描述。",
                    "sources": [],
                    "requires_approval": False,
                    "trace": trace,
                }

            category = self.category_predictor.predict(description)
            priority = classify_priority(description)
            title = description[:20]

            trace.extend(
                [
                    "调用工具：工单类别预测",
                    "调用工具：优先级规则",
                    "调用工具：创建工单",
                ]
            )
            ticket = self.repository.create_ticket(
                title=title,
                description=description,
                creator_id=user_id,
                category=category,
                priority=priority,
            )
            return {
                "intent": intent,
                "message": (
                    f"工单创建成功，编号 {ticket['id']}，类别为"
                    f"{ticket['category']}，优先级为{ticket['priority']}。"
                ),
                "ticket": ticket,
                "sources": [],
                "requires_approval": False,
                "trace": trace,
            }

        ticket_id = extract_ticket_id(message)
        if ticket_id is None:
            return {
                "intent": intent,
                "message": "请提供工单编号。",
                "sources": [],
                "requires_approval": False,
                "trace": trace,
            }

        if intent == "query_ticket":
            trace.append("调用工具：查询工单")
            try:
                ticket = self.repository.get_ticket(
                    ticket_id,
                    requester_id=user_id,
                    requester_role=user_role,
                )
            except PermissionDeniedError as error:
                return {
                    "intent": intent,
                    "message": str(error),
                    "sources": [],
                    "requires_approval": False,
                    "trace": trace,
                }

            if ticket is None:
                message_text = f"没有找到编号为 {ticket_id} 的工单。"
            else:
                message_text = (
                    f"工单 {ticket_id} 当前状态为{ticket['status']}，"
                    f"类别为{ticket['category']}，优先级为{ticket['priority']}。"
                )

            return {
                "intent": intent,
                "message": message_text,
                "ticket": ticket,
                "sources": [],
                "requires_approval": False,
                "trace": trace,
            }

        if not approved:
            trace.append("暂停执行：等待人工确认")
            return {
                "intent": intent,
                "message": (
                    f"关闭工单 {ticket_id} 会修改数据，请确认后使用批准参数重试。"
                ),
                "sources": [],
                "requires_approval": True,
                "trace": trace,
            }

        trace.append("调用工具：关闭工单")
        try:
            ticket = self.repository.close_ticket(
                ticket_id,
                requester_id=user_id,
                requester_role=user_role,
                approved=True,
            )
        except PermissionDeniedError as error:
            return {
                "intent": intent,
                "message": str(error),
                "sources": [],
                "requires_approval": False,
                "trace": trace,
            }

        if ticket is None:
            message_text = f"没有找到编号为 {ticket_id} 的工单。"
        else:
            message_text = f"工单 {ticket_id} 已关闭，并已写入审计日志。"

        return {
            "intent": intent,
            "message": message_text,
            "ticket": ticket,
            "sources": [],
            "requires_approval": False,
            "trace": trace,
        }


def main():
    """从命令行运行一条工作流消息。"""

    parser = argparse.ArgumentParser(description="智能工单工作流")
    parser.add_argument("message", help="用户消息")
    parser.add_argument("--user-id", default="demo-user", help="当前用户编号")
    parser.add_argument(
        "--role",
        choices=["user", "admin"],
        default="user",
        help="当前用户角色",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="明确批准关闭工单等写操作",
    )
    parser.add_argument(
        "--database",
        default=str(DEFAULT_DATABASE_PATH),
        help="数据库文件位置",
    )
    arguments = parser.parse_args()

    repository = TicketRepository(arguments.database)
    engine = WorkflowEngine(repository=repository)
    result = engine.handle(
        arguments.message,
        user_id=arguments.user_id,
        user_role=arguments.role,
        approved=arguments.approve,
    )

    print(f"结果：{result['message']}")
    print("执行轨迹：")
    for step in result["trace"]:
        print(f"- {step}")

    if result["sources"]:
        print("来源：")
        for source in result["sources"]:
            print(f"- {source['file']} / {source['section']}")


if __name__ == "__main__":
    main()

