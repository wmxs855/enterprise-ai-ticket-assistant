"""训练并评测工单类别预测模型。"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "ticket_training.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "ticket_category_model.joblib"
REPORT_PATH = PROJECT_ROOT / "reports" / "step04_model_evaluation.md"
RANDOM_STATE = 42


def load_training_data(file_path=DATA_PATH):
    """读取带有文本和正确类别的训练数据。"""

    return pd.read_csv(file_path)


def split_data(data):
    """按照四分之三训练、四分之一测试的比例划分数据。"""

    return train_test_split(
        data["text"],
        data["category"],
        test_size=0.25,
        random_state=RANDOM_STATE,
        stratify=data["category"],
    )


def build_model():
    """创建文本数字化与分类模型组成的连续处理流程。"""

    return Pipeline(
        [
            (
                "text_vectorizer",
                TfidfVectorizer(analyzer="char", ngram_range=(1, 2)),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
            ),
        ]
    )


def evaluate_predictions(expected, predicted):
    """计算整体指标、各类别指标和混淆矩阵。"""

    precision, recall, harmonic_mean, _ = precision_recall_fscore_support(
        expected,
        predicted,
        average="macro",
        zero_division=0,
    )
    labels = sorted(expected.unique())

    return {
        "accuracy": float(accuracy_score(expected, predicted)),
        "macro_precision": float(precision),
        "macro_recall": float(recall),
        "macro_harmonic_mean": float(harmonic_mean),
        "details": classification_report(
            expected,
            predicted,
            labels=labels,
            output_dict=True,
            zero_division=0,
        ),
        "labels": labels,
        "confusion_matrix": confusion_matrix(
            expected,
            predicted,
            labels=labels,
        ).tolist(),
    }


def train_and_evaluate(data):
    """训练基准与正式模型，并返回评测所需结果。"""

    train_texts, test_texts, train_labels, test_labels = split_data(data)

    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(train_texts.to_frame(), train_labels)
    baseline_predictions = baseline.predict(test_texts.to_frame())

    model = build_model()
    model.fit(train_texts, train_labels)
    model_predictions = model.predict(test_texts)

    errors = []
    for text, expected, predicted in zip(
        test_texts,
        test_labels,
        model_predictions,
    ):
        if expected != predicted:
            errors.append(
                {
                    "text": text,
                    "expected": expected,
                    "predicted": predicted,
                }
            )

    return {
        "model": model,
        "train_count": len(train_texts),
        "test_count": len(test_texts),
        "baseline_accuracy": float(
            accuracy_score(test_labels, baseline_predictions)
        ),
        "model_metrics": evaluate_predictions(test_labels, model_predictions),
        "errors": errors,
    }


def build_report(data, result):
    """把评测结果转换成便于面试展示的文档。"""

    metrics = result["model_metrics"]
    labels = metrics["labels"]

    category_rows = []
    for label in labels:
        values = metrics["details"][label]
        category_rows.append(
            f"| {label} | {values['precision']:.3f} | "
            f"{values['recall']:.3f} | {values['f1-score']:.3f} | "
            f"{int(values['support'])} |"
        )

    matrix_header = "| 实际类别 \\ 预测类别 | " + " | ".join(labels) + " |"
    matrix_separator = "|---|" + "---|" * len(labels)
    matrix_rows = []
    for label, row in zip(labels, metrics["confusion_matrix"]):
        matrix_rows.append(f"| {label} | " + " | ".join(map(str, row)) + " |")

    category_counts = data["category"].value_counts().sort_index()
    category_text = "\n".join(
        f"- {category}：{count} 条" for category, count in category_counts.items()
    )

    if result["errors"]:
        error_text = "\n".join(
            f"- 文本：{error['text']}；正确类别：{error['expected']}；"
            f"预测类别：{error['predicted']}"
            for error in result["errors"]
        )
    else:
        error_text = "- 本次测试没有出现误判。"

    return f"""# 第 4 步模型评测报告

## 数据说明

本次使用合成演示数据，只用于验证训练、评测和保存模型的完整流程，不能代表真实企业环境的最终效果。

- 总样本数：{len(data)}
- 训练样本数：{result['train_count']}
- 测试样本数：{result['test_count']}
- 随机种子：{RANDOM_STATE}

类别分布：

{category_text}

## 基准与模型对比

- 永远预测训练集中最常见类别的基准准确率：{result['baseline_accuracy']:.3f}
- 正式模型准确率：{metrics['accuracy']:.3f}
- 各类别精确率的平均值：{metrics['macro_precision']:.3f}
- 各类别召回率的平均值：{metrics['macro_recall']:.3f}
- 各类别调和平均指标的平均值：{metrics['macro_harmonic_mean']:.3f}

## 各类别指标

| 类别 | 精确率 | 召回率 | 调和平均指标 | 测试样本数 |
|---|---:|---:|---:|---:|
{chr(10).join(category_rows)}

## 混淆矩阵

{matrix_header}
{matrix_separator}
{chr(10).join(matrix_rows)}

## 误判样本

{error_text}

## 结果限制

- 数据由人工编写，语言模式比真实工单简单。
- 总样本数仍然很少，指标可能随数据划分发生明显变化。
- 测试数据与训练数据来自同一种生成方式，不能证明模型已经适应真实业务。
- 上线前必须使用脱敏后的真实历史工单重新训练，并进行多轮人工错误分析。
"""


def main():
    """执行训练、评测、保存模型和生成报告的完整流程。"""

    data = load_training_data()
    result = train_and_evaluate(data)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "model": result["model"],
            "categories": sorted(data["category"].unique()),
            "random_state": RANDOM_STATE,
            "training_sample_count": len(data),
            "data_source": "合成演示数据",
        },
        MODEL_PATH,
    )
    REPORT_PATH.write_text(build_report(data, result), encoding="utf-8")

    metrics = result["model_metrics"]
    print("工单类别模型训练完成")
    print(f"训练样本数：{result['train_count']}")
    print(f"测试样本数：{result['test_count']}")
    print(f"基准准确率：{result['baseline_accuracy']:.3f}")
    print(f"模型准确率：{metrics['accuracy']:.3f}")
    print(f"模型位置：{MODEL_PATH}")
    print(f"评测报告：{REPORT_PATH}")


if __name__ == "__main__":
    main()
