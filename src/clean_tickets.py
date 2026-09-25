"""读取、检查并清洗原始工单表格。"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.ticket_basics import classify_priority


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "tickets.csv"
CLEAN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "tickets_clean.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "step03_data_quality_report.md"


def load_tickets(file_path):
    """从逗号分隔值文件读取工单表格。"""

    return pd.read_csv(file_path)


def clean_tickets(raw_tickets):
    """清洗工单，并同时返回数据质量统计。"""

    tickets = raw_tickets.copy()
    metrics = {"raw_rows": len(tickets)}

    text_columns = [
        "title",
        "description",
        "creator",
        "category",
        "priority",
        "created_at",
    ]

    # 删除文本两端无意义的空格。
    for column_name in text_columns:
        tickets[column_name] = tickets[column_name].str.strip()

    # 把空字符串统一转换为缺失值，便于后续统计和处理。
    tickets[text_columns] = tickets[text_columns].replace(r"^\s*$", np.nan, regex=True)

    before_exact_duplicates = len(tickets)
    tickets = tickets.drop_duplicates()
    metrics["exact_duplicates_removed"] = before_exact_duplicates - len(tickets)

    missing_description = tickets["description"].isna()
    metrics["missing_descriptions_removed"] = int(missing_description.sum())
    tickets = tickets.loc[~missing_description].copy()

    # errors="coerce" 会把无法解析的日期转换为缺失日期。
    tickets["created_at"] = pd.to_datetime(tickets["created_at"], errors="coerce")
    invalid_date = tickets["created_at"].isna()
    metrics["invalid_dates_removed"] = int(invalid_date.sum())
    tickets = tickets.loc[~invalid_date].copy()

    before_duplicate_ids = len(tickets)
    tickets = tickets.drop_duplicates(subset=["ticket_id"], keep="first")
    metrics["duplicate_ids_removed"] = before_duplicate_ids - len(tickets)

    metrics["missing_creators_filled"] = int(tickets["creator"].isna().sum())
    tickets["creator"] = tickets["creator"].fillna("未知用户")

    metrics["missing_categories_filled"] = int(tickets["category"].isna().sum())
    tickets["category"] = tickets["category"].fillna("待分类")

    category_mapping = {
        "账号": "账号问题",
        "支付": "支付问题",
        "技术": "技术问题",
    }
    tickets["category"] = tickets["category"].replace(category_mapping)

    missing_priority = tickets["priority"].isna()
    metrics["missing_priorities_filled"] = int(missing_priority.sum())
    tickets.loc[missing_priority, "priority"] = tickets.loc[
        missing_priority, "description"
    ].apply(classify_priority)

    # NumPy 数组适合执行批量数值计算。
    description_lengths = np.array(tickets["description"].str.len(), dtype=int)
    tickets["description_length"] = description_lengths
    metrics["average_description_length"] = round(
        float(np.mean(description_lengths)), 2
    )

    tickets = tickets.sort_values("ticket_id").reset_index(drop=True)
    tickets["created_at"] = tickets["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    metrics["clean_rows"] = len(tickets)

    return tickets, metrics


def build_quality_report(metrics):
    """根据清洗统计生成可以直接阅读的数据质量报告。"""

    return f"""# 第 3 步数据质量报告

## 清洗结果

- 原始记录数：{metrics['raw_rows']}
- 删除完全重复记录：{metrics['exact_duplicates_removed']}
- 删除重复工单编号：{metrics['duplicate_ids_removed']}
- 删除缺少问题描述的记录：{metrics['missing_descriptions_removed']}
- 删除日期无效的记录：{metrics['invalid_dates_removed']}
- 补全缺失提交人：{metrics['missing_creators_filled']}
- 补全缺失类别：{metrics['missing_categories_filled']}
- 根据规则补全缺失优先级：{metrics['missing_priorities_filled']}
- 清洗后记录数：{metrics['clean_rows']}
- 平均问题描述长度：{metrics['average_description_length']} 个字符

## 处理原则

原始数据保持不变，清洗结果写入单独文件。删除记录必须有明确原因，填充值必须能够解释，所有处理数量都写入报告。
"""


def main():
    """执行完整的数据读取、清洗、保存和报告生成流程。"""

    raw_tickets = load_tickets(RAW_DATA_PATH)
    clean_data, metrics = clean_tickets(raw_tickets)

    CLEAN_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # utf-8-sig 让常见表格软件更容易正确识别中文。
    clean_data.to_csv(CLEAN_DATA_PATH, index=False, encoding="utf-8-sig")
    REPORT_PATH.write_text(build_quality_report(metrics), encoding="utf-8")

    print("数据清洗完成")
    print(f"原始记录数：{metrics['raw_rows']}")
    print(f"清洗后记录数：{metrics['clean_rows']}")
    print(f"清洗结果：{CLEAN_DATA_PATH}")
    print(f"质量报告：{REPORT_PATH}")


if __name__ == "__main__":
    main()

