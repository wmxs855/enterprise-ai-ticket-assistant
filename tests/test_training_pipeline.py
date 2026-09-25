"""检查训练数据和模型训练流程。"""

import unittest

from src.generate_training_data import build_training_data
from src.train_classifier import train_and_evaluate


class TrainingPipelineTest(unittest.TestCase):
    """工单分类模型的数据与训练测试。"""

    @classmethod
    def setUpClass(cls):
        cls.data = build_training_data()
        cls.result = train_and_evaluate(cls.data)

    def test_dataset_has_expected_size(self):
        """合成数据应该包含一百二十条记录。"""

        self.assertEqual(len(self.data), 120)

    def test_categories_are_balanced(self):
        """四个类别应该各有三十条记录。"""

        category_counts = self.data["category"].value_counts().to_dict()
        self.assertEqual(set(category_counts.values()), {30})

    def test_texts_are_unique(self):
        """训练文本不应该重复。"""

        self.assertTrue(self.data["text"].is_unique)

    def test_model_beats_simple_baseline(self):
        """正式模型准确率应该明显超过简单基准。"""

        model_accuracy = self.result["model_metrics"]["accuracy"]
        baseline_accuracy = self.result["baseline_accuracy"]
        self.assertGreater(model_accuracy, baseline_accuracy + 0.30)

    def test_model_can_predict_known_categories(self):
        """模型输出必须属于四个已知类别。"""

        predictions = self.result["model"].predict(
            ["我的登录账号被锁定了", "订单扣款以后没有显示支付成功"]
        )
        known_categories = set(self.data["category"])
        self.assertTrue(set(predictions).issubset(known_categories))


if __name__ == "__main__":
    unittest.main()

