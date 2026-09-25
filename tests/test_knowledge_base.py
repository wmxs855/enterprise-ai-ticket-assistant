"""检查知识文档加载、检索和拒绝规则。"""

import unittest

from src.knowledge_base import KnowledgeBase, load_knowledge_documents


class KnowledgeBaseTest(unittest.TestCase):
    """知识库检索功能的自动测试。"""

    @classmethod
    def setUpClass(cls):
        cls.knowledge_base = KnowledgeBase()

    def test_documents_are_split_into_chunks(self):
        """四份文档应该被切分成十六个有来源的片段。"""

        chunks = load_knowledge_documents()
        self.assertEqual(len(chunks), 16)
        self.assertTrue(all(chunk["source"] for chunk in chunks))

    def test_account_question_finds_account_policy(self):
        """账号锁定问题应该首先找到账号制度。"""

        results = self.knowledge_base.search("账号被锁定后多久恢复")
        self.assertEqual(results[0]["source"], "account_policy.md")

    def test_payment_question_finds_payment_guide(self):
        """重复扣款问题应该首先找到支付指南。"""

        results = self.knowledge_base.search("订单重复扣款怎么退款")
        self.assertEqual(results[0]["source"], "payment_guide.md")

    def test_answer_contains_source(self):
        """有依据的回答必须包含来源文件和章节。"""

        result = self.knowledge_base.answer("报销发票丢了怎么办")
        self.assertTrue(result["found"])
        self.assertEqual(result["sources"][0]["file"], "reimbursement_policy.md")
        self.assertTrue(result["sources"][0]["section"])

    def test_unrelated_question_is_rejected(self):
        """知识库外问题应该被明确拒绝。"""

        result = self.knowledge_base.answer("公司食堂今天中午吃什么")
        self.assertFalse(result["found"])
        self.assertEqual(result["sources"], [])


if __name__ == "__main__":
    unittest.main()

