#!/usr/bin/env python3
"""
scheduler.py —— 请求调度模块

只做一件事：**给定一个等待队列，决定下一个该处理哪条请求**。
不负责发送，也不负责统计——那些由 replay.py 负责。

三种策略：
    fifo            先到先服务（基线）
    priority        交互式优先，同类内期限早的优先
    priority_cache  在 priority 基础上，优先选择能与"刚处理过的会话"
                    共享资料前缀的请求，以提高前缀缓存命中

为什么用规则而不是模型判断优先级：
    决策本身的开销必须计入端到端指标。规则查表的开销可以忽略，
    若改用决策模型，其调用耗时与资源占用必须一并测量和报告。
"""

import time
from collections import deque


def _is_interactive(job):
    return job["interaction_mode"] == "interactive"


class Scheduler:
    """请求调度器。

    policy:
        "fifo"            先到先服务
        "priority"        交互式优先，同类内期限早的优先
        "priority_cache"  再叠加缓存亲和
    warm_window:
        记忆最近若干个已处理的会话，用于缓存亲和判断。
        取值的依据：KV 池 16384 token，单条长文档请求约占 2000~3500 token，
        因此池中大致能保留数个前缀；窗口取 4 是保守估计。
    """

    def __init__(self, policy="fifo", warm_window=4):
        self.policy = policy
        self.warm_window = warm_window
        self.queue = []
        self.warm_sessions = deque(maxlen=warm_window)
        self.submit_seq = 0
        self.log = []                 # 调度决策记录

    # ---------------- 入队 ----------------
    def submit(self, job):
        job["submit_seq"] = self.submit_seq
        self.submit_seq += 1
        job["enqueued_epoch"] = time.time()
        self.queue.append(job)
        return job

    def pending(self):
        return len(self.queue)

    # ---------------- 选择下一个 ----------------
    def pick_next(self):
        if not self.queue:
            return None

        if self.policy == "fifo":
            chosen = min(self.queue, key=lambda j: j["submit_seq"])
            reason = "到达顺序"

        elif self.policy == "priority":
            chosen = min(self.queue, key=self._key_priority)
            reason = "交互式优先/期限"

        elif self.policy == "priority_cache":
            chosen = min(self.queue, key=self._key_cache)
            reason = ("命中热会话" if chosen["session_id"] in self.warm_sessions
                      else "交互式优先/期限")
        else:
            raise ValueError("未知策略：%s" % self.policy)

        self.queue.remove(chosen)
        self.log.append({
            "epoch": round(time.time(), 4),
            "request_id": chosen["request_id"],
            "policy": self.policy,
            "reason": reason,
            "queue_len_before": len(self.queue) + 1,
            "warm_sessions": list(self.warm_sessions),
        })
        return chosen

    # ---------------- 排序键 ----------------
    def _key_priority(self, job):
        # 交互式 = 0，后台 = 1；同类内期限早的优先；再同则先到先服务
        return (0 if _is_interactive(job) else 1,
                job["deadline_after_arrival_ms"],
                job["submit_seq"])

    def _key_cache(self, job):
        # 优先级不变，只是把"能命中热会话"的排在同类前面
        return (0 if _is_interactive(job) else 1,
                0 if job["session_id"] in self.warm_sessions else 1,
                job["deadline_after_arrival_ms"],
                job["submit_seq"])

    # ---------------- 处理完成后的记忆更新 ----------------
    def mark_done(self, job):
        """记录该会话已进入缓存。放在最前，代表"最近使用的"。

        只在真正读到缓存或产生了可复用前缀时才记为热会话；
        这里以"该请求确实被执行过"为准。
        """
        if job["session_id"] in self.warm_sessions:
            self.warm_sessions.remove(job["session_id"])
        self.warm_sessions.appendleft(job["session_id"])
