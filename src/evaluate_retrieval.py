"""使用固定问题集评测知识库检索效果。"""

from pathlib import Path

import pandas as pd

from src.knowledge_base import DEFAULT_MINIMUM_SCORE, KnowledgeBase


PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUESTION_PATH = PROJECT_ROOT / "data" / "evaluation" / "knowledge_questions.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "step05_retrieval_evaluation.md"


def evaluate(knowledge_base, questions):
    """计算第一条命中、前三条命中和未知问题拒绝效果。"""

    known_total = 0
    first_result_hits = 0
    first_three_hits = 0
    unknown_total = 0
    unknown_rejections = 0
    details = []

    for row in questions.itertuples(index=False):
        should_find = row.should_find == "是"
        search_results = knowledge_base.search(row.question, result_count=3)
        answer_result = knowledge_base.answer(row.question)

        if should_find:
            known_total += 1
            first_hit = search_results[0]["source"] == row.expected_source
            first_three_hit = row.expected_source in {
                result["source"] for result in search_results
            }
            first_result_hits += int(first_hit)
            first_three_hits += int(first_three_hit)
            passed = first_hit
        else:
            unknown_total += 1
            rejected = not answer_result["found"]
            unknown_rejections += int(rejected)
            passed = rejected

        details.append(
            {
                "question": row.question,
                "expected_source": row.expected_source if should_find else "应拒绝",
                "actual_source": (
                    search_results[0]["source"] if answer_result["found"] else "已拒绝"
                ),
                "best_score": search_results[0]["score"],
                "passed": passed,
            }
        )

    return {
        "known_total": known_total,
        "first_result_hits": first_result_hits,
        "first_three_hits": first_three_hits,
        "unknown_total": unknown_total,
        "unknown_rejections": unknown_rejections,
        "details": details,
        "lowest_known_score": min(
            detail["best_score"]
            for detail in details
            if detail["expected_source"] != "应拒绝"
        ),
        "highest_unknown_score": max(
            detail["best_score"]
            for detail in details
            if detail["expected_source"] == "应拒绝"
        ),
    }


def build_report(result):
    """把检索评测结果生成为 Markdown 报告。"""

    first_rate = result["first_result_hits"] / result["known_total"]
    first_three_rate = result["first_three_hits"] / result["known_total"]
    rejection_rate = result["unknown_rejections"] / result["unknown_total"]

    detail_rows = []
    for detail in result["details"]:
        status = "通过" if detail["passed"] else "失败"
        detail_rows.append(
            f"| {detail['question']} | {detail['expected_source']} | "
            f"{detail['actual_source']} | {detail['best_score']:.3f} | {status} |"
        )

    return f"""# 第 5 步知识检索评测报告

## 汇总结果

- 应该找到资料的问题：{result['known_total']} 条
- 第一条结果来源正确：{result['first_result_hits']} 条，命中率 {first_rate:.1%}
- 前三条包含正确来源：{result['first_three_hits']} 条，命中率 {first_three_rate:.1%}
- 知识库外问题：{result['unknown_total']} 条
- 正确拒绝知识库外问题：{result['unknown_rejections']} 条，拒绝率 {rejection_rate:.1%}
- 当前相关度阈值：{DEFAULT_MINIMUM_SCORE:.3f}
- 知识内问题最低相关度：{result['lowest_known_score']:.3f}
- 知识外问题最高相关度：{result['highest_unknown_score']:.3f}

## 逐题结果

| 问题 | 预期 | 实际第一来源 | 最高相关度 | 结果 |
|---|---|---|---:|---|
{chr(10).join(detail_rows)}

## 说明

当前评测集规模较小，主要用于防止代码修改破坏已有检索效果。真实上线前应使用业务人员编写的更多问题，并把问题按主题、难度和表达方式分类评测。

当前阈值根据小型开发问题集调整，因此这个结果不能视为完全独立的最终测试。后续需要另建没有参与阈值选择的问题集进行验证。
"""


def main():
    """运行检索评测并保存报告。"""

    knowledge_base = KnowledgeBase()
    questions = pd.read_csv(QUESTION_PATH)
    result = evaluate(knowledge_base, questions)
    report = build_report(result)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("知识检索评测完成")
    print(
        f"第一条来源命中：{result['first_result_hits']} / "
        f"{result['known_total']}"
    )
    print(
        f"前三条来源命中：{result['first_three_hits']} / "
        f"{result['known_total']}"
    )
    print(
        f"未知问题正确拒绝：{result['unknown_rejections']} / "
        f"{result['unknown_total']}"
    )
    print(f"评测报告：{REPORT_PATH}")


if __name__ == "__main__":
    main()
