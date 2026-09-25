"""把知识问答与工单工作流封装为可通过网络访问的后端服务。"""

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from src.ticket_database import (
    DEFAULT_DATABASE_PATH,
    PermissionDeniedError,
    TicketRepository,
)
from src.workflow import WorkflowEngine


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIRECTORY = PROJECT_ROOT / "web"


class StrictTextModel(BaseModel):
    """为需要非空文字的请求提供统一清理规则。"""

    @field_validator("*", mode="before")
    @classmethod
    def strip_text(cls, value):
        """移除用户不小心输入的首尾空格。"""

        return value.strip() if isinstance(value, str) else value


class AssistantMessageRequest(StrictTextModel):
    """通用助手消息的请求结构。"""

    message: str = Field(min_length=1, max_length=1000)
    user_id: str = Field(min_length=1, max_length=100)
    user_role: Literal["user", "admin"] = "user"
    approved: bool = False


class CreateTicketRequest(StrictTextModel):
    """创建工单的请求结构。"""

    description: str = Field(min_length=2, max_length=1000)
    user_id: str = Field(min_length=1, max_length=100)


class CloseTicketRequest(StrictTextModel):
    """关闭工单的请求结构。"""

    user_id: str = Field(min_length=1, max_length=100)
    user_role: Literal["user", "admin"] = "user"
    approved: bool = False


class TicketResponse(BaseModel):
    """返回给调用方的工单字段。"""

    id: int
    title: str
    description: str
    creator_id: str
    category: str
    priority: str
    status: str
    created_at: str
    updated_at: str


class SourceResponse(BaseModel):
    """知识答案使用的证据来源。"""

    file: str
    section: str
    score: float


class AssistantMessageResponse(BaseModel):
    """完整工作流的统一响应结构。"""

    intent: str
    message: str
    sources: list[SourceResponse] = Field(default_factory=list)
    requires_approval: bool
    trace: list[str]
    ticket: TicketResponse | None = None


class HealthResponse(BaseModel):
    """服务健康检查的响应结构。"""

    status: str
    version: str
    answer_mode: str


def create_app(database_path: str | Path = DEFAULT_DATABASE_PATH):
    """创建应用；允许测试传入独立数据库，避免污染演示数据。"""

    repository = TicketRepository(database_path)
    engine = WorkflowEngine(repository=repository)
    application = FastAPI(
        title="企业知识库与智能工单助手",
        description=(
            "提供知识问答、工单分类、创建、权限查询与人工审批关闭能力。"
            "这是面试演示项目，请勿当作生产身份认证系统。"
        ),
        version="0.7.0",
    )
    application.mount(
        "/static",
        StaticFiles(directory=WEB_DIRECTORY),
        name="static",
    )

    @application.get(
        "/",
        response_class=FileResponse,
        include_in_schema=False,
    )
    def demo_page():
        """返回供面试演示使用的单页界面。"""

        return WEB_DIRECTORY / "index.html"

    @application.get(
        "/health",
        response_model=HealthResponse,
        tags=["系统"],
        summary="检查服务是否正常运行",
    )
    def health_check():
        return {
            "status": "ok",
            "version": application.version,
            "answer_mode": "offline_evidence",
        }

    @application.post(
        "/v1/assistant/messages",
        response_model=AssistantMessageResponse,
        tags=["智能助手"],
        summary="执行完整智能工作流",
    )
    def handle_assistant_message(request: AssistantMessageRequest):
        return engine.handle(
            request.message,
            user_id=request.user_id,
            user_role=request.user_role,
            approved=request.approved,
        )

    @application.post(
        "/v1/tickets",
        response_model=TicketResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["工单"],
        summary="创建并自动分类工单",
    )
    def create_ticket(request: CreateTicketRequest):
        result = engine.handle(
            f"创建工单：{request.description}",
            user_id=request.user_id,
        )
        return result["ticket"]

    @application.get(
        "/v1/tickets/{ticket_id}",
        response_model=TicketResponse,
        tags=["工单"],
        summary="按权限查询工单",
    )
    def get_ticket(
        ticket_id: int,
        user_id: str = Query(min_length=1, max_length=100),
        user_role: Literal["user", "admin"] = "user",
    ):
        try:
            ticket = repository.get_ticket(ticket_id, user_id, user_role)
        except PermissionDeniedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到该工单。",
            )
        return ticket

    @application.post(
        "/v1/tickets/{ticket_id}/close",
        response_model=TicketResponse,
        tags=["工单"],
        summary="经人工确认后关闭工单",
    )
    def close_ticket(ticket_id: int, request: CloseTicketRequest):
        if not request.approved:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="关闭会修改数据，请把 approved 设置为 true 后重试。",
            )

        try:
            ticket = repository.close_ticket(
                ticket_id,
                requester_id=request.user_id,
                requester_role=request.user_role,
                approved=True,
            )
        except PermissionDeniedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到该工单。",
            )
        return ticket

    return application


app = create_app()
