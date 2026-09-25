"""用一个小型工单程序学习 Python 基础语法。"""


# 列表：把多个同类数据按顺序保存在一起。
URGENT_KEYWORDS = ["无法登录", "数据丢失", "支付失败", "服务中断"]


def classify_priority(description):
    """根据问题描述中的关键词判断工单是否紧急。"""

    # 循环：依次取出列表中的每个紧急关键词。
    for keyword in URGENT_KEYWORDS:
        # 条件判断：检查关键词是否出现在问题描述中。
        if keyword in description:
            return "紧急"

    return "普通"


def create_ticket(ticket_id, title, description, creator):
    """创建并返回一张用字典表示的工单。"""

    priority = classify_priority(description)

    # 字典：使用名称和值组成的对应关系保存一张工单。
    ticket = {
        "id": ticket_id,
        "title": title,
        "description": description,
        "creator": creator,
        "priority": priority,
        "is_closed": False,
    }
    return ticket


def display_ticket(ticket):
    """把一张工单以便于阅读的格式打印到终端。"""

    if ticket["is_closed"]:
        status = "已关闭"
    else:
        status = "待处理"

    # 格式化字符串可以把变量的值放进一段文字中。
    print(f"工单编号：{ticket['id']}")
    print(f"标题：{ticket['title']}")
    print(f"提交人：{ticket['creator']}")
    print(f"优先级：{ticket['priority']}")
    print(f"状态：{status}")
    print("-" * 30)


def main():
    """创建示例工单，逐张显示并统计紧急工单数量。"""

    tickets = [
        create_ticket(1, "账号问题", "员工无法登录内部系统", "小林"),
        create_ticket(2, "资料咨询", "请问报销制度在哪里查看", "小周"),
        create_ticket(3, "支付问题", "客户付款时一直显示支付失败", "小陈"),
    ]

    urgent_count = 0

    for ticket in tickets:
        display_ticket(ticket)
        if ticket["priority"] == "紧急":
            urgent_count = urgent_count + 1

    print(f"工单总数：{len(tickets)}")
    print(f"紧急工单数：{urgent_count}")


# 只有直接运行本文件时才执行 main 函数。
if __name__ == "__main__":
    main()

