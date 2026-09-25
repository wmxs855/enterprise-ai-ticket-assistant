"""加载已经训练的模型，并预测一条新工单的类别。"""

from pathlib import Path
import sys

import joblib


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "ticket_category_model.joblib"


def predict_category(text, model_path=MODEL_PATH):
    """返回预测类别和模型给出的最高概率。"""

    model_artifact = joblib.load(model_path)
    model = model_artifact["model"]

    predicted_category = model.predict([text])[0]
    category_probabilities = model.predict_proba([text])[0]
    highest_probability = float(max(category_probabilities))

    return predicted_category, highest_probability


def main():
    """从命令行接收工单描述并打印预测结果。"""

    if len(sys.argv) < 2:
        raise SystemExit(
            "请在命令后提供工单描述，例如：我的登录账号被锁定了"
        )

    text = " ".join(sys.argv[1:])
    category, probability = predict_category(text)

    print(f"工单描述：{text}")
    print(f"预测类别：{category}")
    print(f"最高概率：{probability:.3f}")
    print("注意：概率只反映当前演示模型，不代表真实业务置信度。")


if __name__ == "__main__":
    main()

