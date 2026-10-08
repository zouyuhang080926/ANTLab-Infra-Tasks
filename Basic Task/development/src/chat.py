#!/usr/bin/env python3
"""
在终端里和本地模型对话。

原理：调用正在运行的 llama-server 的 HTTP 接口（默认 8888 端口）。
      不额外加载模型，因此不额外占用显存。

用法：
    1. 先确认服务在跑：  curl -s http://localhost:8888/health
    2. 运行：            python3 chat.py

对话中可用的指令：
    /clear   清空上下文，重新开始
    /exit    退出（也可以按 Ctrl+C）
"""

import json
import urllib.error
import urllib.request

# ---- 可以改的配置 ----
URL = "http://127.0.0.1:8888/v1/chat/completions"
SYSTEM_PROMPT = "你是一个乐于助人的中文助手。回答简洁、准确，不确定时明确说明。"
MAX_TOKENS = 512
TEMPERATURE = 0          # 0 = 每次回答尽量一致
ENABLE_THINKING = False  # False = 不输出推理过程，直接给答案
# ----------------------


def clean(text):
    """清掉终端可能送进来的非法字节。

    背景：终端若送来不是合法 UTF-8 的字节（粘贴被截断、编码不一致等），
    Python 的 stdin 会把它们变成"孤立代理字符"（U+DC80~U+DCFF）。
    这种字符无法编码成合法 JSON，服务端会返回 400。
    这里把它们替换成 '?'，让请求仍能正常发出。
    """
    fixed = text.encode("utf-8", "replace").decode("utf-8", "replace")
    if fixed != text:
        print("\n[提示] 检测到输入里有非法字符，已替换为 ? 后继续。")
    return fixed


def ask(messages):
    """把整段对话发给服务，流式接收回答，边收边打印。返回完整回答文本。"""
    body = {
        "model": "local",
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": ENABLE_THINKING},
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    pieces = []
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            payload = line[len("data: "):]
            if payload == "[DONE]":
                break
            delta = json.loads(payload)["choices"][0]["delta"].get("content")
            if delta:
                pieces.append(delta)
                print(delta, end="", flush=True)
    print()
    return "".join(pieces)


def main():
    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("=" * 60)
    print(" 本地模型对话")
    print(" /clear 清空上下文    /exit 退出（或 Ctrl+C）")
    print("=" * 60)

    while True:
        try:
            question = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not question:
            continue
        if question in ("/exit", "/quit", "/q"):
            print("再见。")
            break
        if question == "/clear":
            del history[1:]
            print("（上下文已清空，新一轮对话开始）")
            continue

        history.append({"role": "user", "content": clean(question)})
        print("模型：", end="", flush=True)
        try:
            answer = ask(history)
        except urllib.error.HTTPError as exc:
            # 关键：把服务端返回的错误正文打出来，否则只有一句无用的 "400 Bad Request"
            detail = exc.read().decode("utf-8", "replace")
            print(f"\n[请求被服务拒绝] HTTP {exc.code}")
            print(detail)
            history.pop()                             # 失败的这轮不留在上下文里
            continue
        except Exception as exc:                      # noqa: BLE001
            print(f"\n[请求失败] {type(exc).__name__}: {exc}")
            print("检查一下服务是否在跑： curl -s http://localhost:8888/health")
            history.pop()
            continue

        history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
