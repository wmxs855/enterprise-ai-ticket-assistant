"""使用 SQLite 数据库保存工单和审计记录。"""

from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
import sqlite3
import time


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "runtime" / "tickets.db"


class PermissionDeniedError(Exception):
    """用户没有执行当前操作的权限。"""


def current_time_text():
    """返回带时区的当前时间文本。"""

    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def execute_with_retry(operation, attempts=2, wait_seconds=0.1):
    """数据库临时不可用时进行有限次数重试。"""

    last_error = None
    for attempt_number in range(1, attempts + 1):
        try:
            return operation()
        except sqlite3.OperationalError as error:
            last_error = error
            if attempt_number < attempts:
                time.sleep(wait_seconds)

    raise last_error


class TicketRepository:
    """封装工单数据库的创建、查询和关闭操作。"""

    def __init__(self, database_path=DEFAULT_DATABASE_PATH):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        """创建数据库连接，并让查询结果可以通过字段名读取。"""

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def connection_scope(self):
        """提交或回滚事务，并保证数据库连接最终被关闭。"""

        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        """创建工单表与审计日志表。"""

        def operation():
            with self.connection_scope() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        creator_id TEXT NOT NULL,
                        category TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT NOT NULL,
                        ticket_id INTEGER,
                        actor_id TEXT NOT NULL,
                        detail TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )

        execute_with_retry(operation)

    def add_audit_log(self, connection, action, ticket_id, actor_id, detail):
        """在同一数据库事务中记录重要操作。"""

        connection.execute(
            """
            INSERT INTO audit_logs (action, ticket_id, actor_id, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (action, ticket_id, actor_id, detail, current_time_text()),
        )

    def create_ticket(self, title, description, creator_id, category, priority):
        """创建工单并返回完整记录。"""

        def operation():
            now = current_time_text()
            with self.connection_scope() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO tickets (
                        title, description, creator_id, category,
                        priority, status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title,
                        description,
                        creator_id,
                        category,
                        priority,
                        "待处理",
                        now,
                        now,
                    ),
                )
                ticket_id = cursor.lastrowid
                self.add_audit_log(
                    connection,
                    "创建工单",
                    ticket_id,
                    creator_id,
                    f"类别={category}; 优先级={priority}",
                )
                row = connection.execute(
                    "SELECT * FROM tickets WHERE id = ?",
                    (ticket_id,),
                ).fetchone()
                return dict(row)

        return execute_with_retry(operation)

    def get_ticket(self, ticket_id, requester_id, requester_role="user"):
        """按权限查询工单；普通用户只能查看自己的工单。"""

        def operation():
            with self.connection_scope() as connection:
                row = connection.execute(
                    "SELECT * FROM tickets WHERE id = ?",
                    (ticket_id,),
                ).fetchone()

                if row is None:
                    return None

                if requester_role != "admin" and row["creator_id"] != requester_id:
                    raise PermissionDeniedError("无权查看其他用户的工单。")

                return dict(row)

        return execute_with_retry(operation)

    def close_ticket(
        self,
        ticket_id,
        requester_id,
        requester_role="user",
        approved=False,
    ):
        """经过明确批准后关闭有权限操作的工单。"""

        if not approved:
            raise PermissionDeniedError("关闭工单需要人工确认。")

        def operation():
            with self.connection_scope() as connection:
                row = connection.execute(
                    "SELECT * FROM tickets WHERE id = ?",
                    (ticket_id,),
                ).fetchone()

                if row is None:
                    return None

                if requester_role != "admin" and row["creator_id"] != requester_id:
                    raise PermissionDeniedError("无权关闭其他用户的工单。")

                now = current_time_text()
                connection.execute(
                    """
                    UPDATE tickets
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    ("已关闭", now, ticket_id),
                )
                self.add_audit_log(
                    connection,
                    "关闭工单",
                    ticket_id,
                    requester_id,
                    "已获得人工确认",
                )
                updated_row = connection.execute(
                    "SELECT * FROM tickets WHERE id = ?",
                    (ticket_id,),
                ).fetchone()
                return dict(updated_row)

        return execute_with_retry(operation)

    def list_audit_logs(self):
        """返回全部审计记录，供测试和管理员检查。"""

        with self.connection_scope() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_logs ORDER BY id"
            ).fetchall()
            return [dict(row) for row in rows]
