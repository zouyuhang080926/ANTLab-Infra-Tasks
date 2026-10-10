#!/usr/bin/env python3
"""
supervisor.py —— 推理服务管理器

职责：
  1. 状态检测：通过 /health 判断服务是否活着（不看进程是否存在，
     因为进程在但服务卡死的情况同样不可用）；
  2. 进程重启：终止旧进程并重新拉起；
  3. 就绪确认：重启后必须等到 /health 返回正常才算恢复，不能只看进程起来了；
  4. 事件记录：把每一次状态变化带时间戳写下来，供报告与前端使用。

为什么"就绪确认"要单独做：
    进程启动到模型加载完成之间有十几秒的空窗期，这段时间端口尚未监听或
    服务尚未可用。如果只看进程是否存活就宣布"已恢复"，后续请求仍然会失败。

用法：
    from supervisor import Supervisor
    sup = Supervisor()
    sup.ensure_running()          # 不可用则自动重启并等待就绪
"""

import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

DEFAULT_BIN = "/root/work/llama.cpp/build/bin/llama-server"
DEFAULT_MODEL = "/root/work/models/Qwen3-4B-Q4_K_M.gguf"
DEFAULT_LOG_DIR = Path("/root/work/logs")
DEFAULT_PORT = 8888


class Supervisor:
    def __init__(self, port=DEFAULT_PORT, bin_path=DEFAULT_BIN,
                 model_path=DEFAULT_MODEL, extra_args=None):
        self.port = port
        self.bin_path = bin_path
        self.model_path = model_path
        self.extra_args = extra_args or ["-ngl", "99", "-c", "16384", "-cram", "0", "--metrics"]
        self.log_path = DEFAULT_LOG_DIR / ("llama_%d.out" % port)
        self.events = []              # 事件时间线

    # ---------------- 状态检测 ----------------
    def health(self, timeout=3):
        """返回 (是否可用, 说明)。"""
        url = "http://127.0.0.1:%d/health" % self.port
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", "replace").strip()
            return ("ok" in body), body
        except urllib.error.URLError as exc:
            return False, "%s" % exc
        except Exception as exc:                              # noqa: BLE001
            return False, "%s: %s" % (type(exc).__name__, exc)

    def is_alive(self):
        return self.health()[0]

    # ---------------- 事件记录 ----------------
    def log(self, kind, detail=""):
        event = {
            "time": datetime.now().isoformat(timespec="milliseconds"),
            "epoch": round(time.time(), 3),
            "kind": kind,
            "detail": detail,
        }
        self.events.append(event)
        print("  [%s] %-14s %s" % (event["time"][11:], kind, detail))
        return event

    def save_events(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.events, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        return path

    # ---------------- 进程操作 ----------------
    def _pids(self):
        try:
            out = subprocess.run(["pgrep", "-f", "bin/llama-server"],
                                 capture_output=True, text=True, timeout=10).stdout
            return [int(x) for x in out.split()]
        except Exception:                                     # noqa: BLE001
            return []

    def stop(self):
        pids = self._pids()
        for pid in pids:
            try:
                subprocess.run(["kill", str(pid)], timeout=10)
            except Exception:                                 # noqa: BLE001
                pass
        for _ in range(20):
            if not self._pids():
                break
            time.sleep(0.5)
        else:
            for pid in self._pids():
                try:
                    subprocess.run(["kill", "-9", str(pid)], timeout=10)
                except Exception:                             # noqa: BLE001
                    pass
        self.log("stopped", "已终止进程 %s" % (pids or "（原本就没有）"))

    def start(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["setsid", "nohup", self.bin_path, "-m", self.model_path,
               "--host", "0.0.0.0", "--port", str(self.port)] + self.extra_args
        log_file = open(self.log_path, "ab")
        subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        self.log("started", "已拉起进程，日志 %s" % self.log_path)

    # ---------------- 就绪确认 ----------------
    def wait_ready(self, timeout=120):
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            if self.is_alive():
                used = time.monotonic() - started
                self.log("ready", "服务就绪，耗时 %.1f 秒" % used)
                return True
            time.sleep(0.5)
        self.log("ready_timeout", "等待 %.0f 秒仍未就绪" % timeout)
        return False

    def restart(self, timeout=120):
        t0 = time.monotonic()
        self.log("restart_begin", "开始重启")
        self.stop()
        self.start()
        ok = self.wait_ready(timeout)
        self.log("restart_end", "重启%s，总耗时 %.1f 秒"
                 % ("成功" if ok else "失败", time.monotonic() - t0))
        return ok

    def ensure_running(self):
        """可用就直接返回；不可用则重启。返回是否最终可用。"""
        alive, detail = self.health()
        if alive:
            return True
        self.log("detected_down", "健康检查失败：%s" % detail)
        return self.restart()
