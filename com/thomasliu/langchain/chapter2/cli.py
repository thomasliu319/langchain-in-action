#!/usr/bin/env python3
"""CLI 文本生成"""

import argparse
import sys
from pathlib import Path

# 支持直接运行 python cli.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from com.thomasliu.langchain.chapter2 import generate



def main():
    parser = argparse.ArgumentParser(description="本地模型文本生成")
    parser.add_argument("prompt", nargs="?", default="Write an email apologizing to sarah for the tragic gardening mishap. Explain how it happened.<|assistant|>", help="输入提示词")
    parser.add_argument("--max-tokens", type=int, default=None, help="最大生成 token 数")
    parser.add_argument("--temperature", type=float, default=None, help="采样温度")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    args = parser.parse_args()

    if args.interactive:
        print("交互模式（Ctrl+C 或空行退出）")
        while True:
            try:
                prompt = input("\n>>> ")
                if not prompt.strip():
                    break
                print(generate(prompt, args.max_tokens, args.temperature))
            except (EOFError, KeyboardInterrupt):
                break
        return

    print(generate(args.prompt, args.max_tokens, args.temperature))


if __name__ == "__main__":
    main()
