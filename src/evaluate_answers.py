"""评测检索与答案生成组成的完整问答流程。"""

from pathlib import Path

import pandas as pd

from src.answer_generator import KnowledgeAssistant, OfflineEvidenceGenerator


PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUESTION_PATH = PROJECT_ROOT / "data" / "evaluation" / "answer_questions.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "step05_answer_evaluation.md"


def evaluate_answers(assistant, questions):
    """检查是否回答、必需事实和来源文件。"""

    details = []

    for row in questions.itertuples(index=False):
        result = assistant.ask(row.question)
        should_answer = row.should_answer == "是"
        required_terms = row.required_terms.split("|")

        found_correctly = result["found"] == should_answer
        terms_present = all(term in result["answer"] for term in required_terms)

        if should_answer:
            source_files = {source["file"] for source in result["sources"]}
            source_correct = row.expected_source in source_files
        else:
            source_correct = result["sources"] == []

        passed = found_correctly and terms_present and source_correct
        details.append(
            {
                "question": row.question,
                "answer": result["answer"],
                "expected_source": row.expected_source if should_answer else "应拒绝",
                "mode": result["generation_mode"],
                "passed": passed,
            }
        )

    return details


def build_report(details):
    """生成端到端问答评测报告。"""

    passed_count = sum(detail["passed"] for detail in details)
    rows = []
    for detail in details:
        status = "通过" if detail["passed"] else "失败"
        safe_answer = detail["answer"].replace("|", "｜").replace("\n", " ")
        rows.append(
            f"| {detail['question']} | {safe_answer} | "
            f"{detail['expected_source']} | {detail['mode']} | {status} |"
        )

    return f"""# 第 5 步端到端问答评测报告

## 当前验证状态

- 评测模式：离线原文模式
- 评测问题数：{len(details)}
- 通过数量：{passed_count}
- 在线大语言模型调用：未执行，原因是当前环境没有配置用户密钥与模型名称

## 检查内容

- 知识内问题必须返回答案。
- 答案必须保留规定的关键事实和数字。
- 来源必须包含预期文件。
- 知识库外问题必须拒绝，且不能附带虚假来源。

## 逐题结果

| 问题 | 回答 | 预期来源 | 生成模式 | 结果 |
|---|---|---|---|---|
{chr(10).join(rows)}

## 结论与限制

离线模式证明了检索、证据传递、来源附加、拒绝策略和评测流程可以运行。在线模型的语言整理效果、事实保持能力、延迟和调用成本尚未验证，在真实调用完成前不能写入简历成果。
"""


def main():
    """运行离线端到端评测并保存报告。"""

    questions = pd.read_csv(QUESTION_PATH)
    assistant = KnowledgeAssistant(OfflineEvidenceGenerator())
    details = evaluate_answers(assistant, questions)
    report = build_report(details)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    passed_count = sum(detail["passed"] for detail in details)
    print("端到端问答评测完成")
    print(f"通过数量：{passed_count} / {len(details)}")
    print("在线模型调用：未执行，当前未配置用户密钥与模型名称")
    print(f"评测报告：{REPORT_PATH}")


if __name__ == "__main__":
    main()

