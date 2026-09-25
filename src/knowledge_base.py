"""读取企业文档，并根据问题检索相关段落。"""

from pathlib import Path
import sys

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
# 当前值根据小型开发问题集设定，真实业务需要用独立数据重新验证。
DEFAULT_MINIMUM_SCORE = 0.20


def split_document(file_path):
    """按标题和自然段把一个文档切分成较小片段。"""

    content = file_path.read_text(encoding="utf-8")
    blocks = [block.strip() for block in content.split("\n\n") if block.strip()]

    document_title = file_path.stem
    section_title = "正文"
    chunks = []

    for block in blocks:
        if block.startswith("# "):
            document_title = block[2:].strip()
            continue

        if block.startswith("## "):
            section_title = block[3:].strip()
            continue

        chunks.append(
            {
                "source": file_path.name,
                "document_title": document_title,
                "section_title": section_title,
                "text": block,
            }
        )

    return chunks


def load_knowledge_documents(knowledge_dir=KNOWLEDGE_DIR):
    """读取知识目录中的所有 Markdown 文档。"""

    chunks = []
    for file_path in sorted(knowledge_dir.glob("*.md")):
        chunks.extend(split_document(file_path))

    if not chunks:
        raise ValueError(f"知识目录中没有可检索内容：{knowledge_dir}")

    return chunks


class KnowledgeBase:
    """使用词频—逆文档频率检索相关文档片段。"""

    def __init__(self, knowledge_dir=KNOWLEDGE_DIR):
        self.chunks = load_knowledge_documents(knowledge_dir)
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 2))

        searchable_texts = [
            f"{chunk['document_title']} {chunk['section_title']} {chunk['text']}"
            for chunk in self.chunks
        ]
        self.document_vectors = self.vectorizer.fit_transform(searchable_texts)

    def search(self, question, result_count=3):
        """返回与问题最相关的若干文档片段。"""

        question_vector = self.vectorizer.transform([question])
        scores = cosine_similarity(
            question_vector,
            self.document_vectors,
        )[0]

        result_indexes = np.argsort(scores)[::-1][:result_count]
        results = []

        for index in result_indexes:
            chunk = self.chunks[int(index)]
            results.append(
                {
                    **chunk,
                    "score": float(scores[index]),
                }
            )

        return results

    def answer(self, question, minimum_score=DEFAULT_MINIMUM_SCORE):
        """返回最相关原文；没有可靠结果时明确拒绝回答。"""

        results = self.search(question, result_count=3)
        best_result = results[0]

        if best_result["score"] < minimum_score:
            return {
                "found": False,
                "answer": "知识库中没有找到足够可靠的依据，请创建人工工单。",
                "sources": [],
                "search_results": results,
            }

        return {
            "found": True,
            "answer": best_result["text"],
            "sources": [
                {
                    "file": best_result["source"],
                    "section": best_result["section_title"],
                    "score": best_result["score"],
                }
            ],
            "search_results": results,
        }


def main():
    """从命令行接收问题并显示答案和来源。"""

    if len(sys.argv) < 2:
        raise SystemExit("请在命令后输入问题，例如：账号被锁定多久能恢复")

    question = " ".join(sys.argv[1:])
    knowledge_base = KnowledgeBase()
    result = knowledge_base.answer(question)

    print(f"问题：{question}")
    print(f"回答：{result['answer']}")

    if result["sources"]:
        print("来源：")
        for source in result["sources"]:
            print(
                f"- {source['file']} / {source['section']} "
                f"（相关度：{source['score']:.3f}）"
            )
    else:
        print("来源：无可靠来源")


if __name__ == "__main__":
    main()
