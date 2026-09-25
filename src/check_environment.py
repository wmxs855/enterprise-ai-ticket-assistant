"""检查项目的基础运行环境。

这个程序只使用 Python 自带功能，因此不需要提前安装第三方工具。
"""

from pathlib import Path
import sys


# __file__ 表示当前程序文件的位置。
# parent 表示上一级目录。连续使用两次即可得到项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    """打印 Python 信息，并检查项目所需的基础目录。"""

    print("企业知识库与智能工单助手：环境检查")
    print(f"Python 版本：{sys.version.split()[0]}")
    print(f"Python 解释器：{sys.executable}")
    print(f"项目根目录：{PROJECT_ROOT}")
    print("\n目录检查：")

    required_directories = ["data", "docs", "src", "tests"]
    all_ready = True

    for directory_name in required_directories:
        directory_path = PROJECT_ROOT / directory_name
        exists = directory_path.is_dir()
        status = "正常" if exists else "缺失"
        print(f"- {directory_name}: {status}")
        all_ready = all_ready and exists

    if not all_ready:
        raise SystemExit("环境检查失败：存在缺失目录。")

    print("\n环境检查通过，可以进入下一步。")


if __name__ == "__main__":
    main()

