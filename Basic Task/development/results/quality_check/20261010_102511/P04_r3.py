import os
import time
import json
from threading import Lock

# 配置参数
TASK_DIR = "tasks"
MAX_RETRIES = 5
RETRY_DELAY = 1  # 秒

# 初始化锁
lock = Lock()

def save_task_state(task_id, status):
    """保存任务状态"""
    with lock:
        task_path = os.path.join(TASK_DIR, task_id)
        os.makedirs(task_path, exist_ok=True)
        with open(os.path.join(task_path, "status"), "w") as f:
            json.dump({"status": status}, f)

def load_task_state(task_id):
    """加载任务状态"""
    with lock:
        task_path = os.path.join(TASK_DIR, task_id)
        status_path = os.path.join(task_path, "status")
        if not os.path.exists(status_path):
            return None
        with open(status_path, "r") as f:
            return json.load(f).get("status")

def save_retry_info(task_id, retries):
    """保存重试信息"""
    with lock:
        task_path = os.path.join(TASK_DIR, task_id)
        retry_path = os.path.join(task_path, "retries")
        with open(retry_path, "w") as f:
            json.dump({"retries": retries}, f)

def load_retry_info(task_id):
    """加载重试信息"""
    with lock:
        task_path = os.path.join(TASK_DIR, task_id)
        retry_path = os.path.join(task_path, "retries")
        if not os.path.exists(retry_path):
            return 0
        with open(retry_path, "r") as f:
            return json.load(f).get("retries", 0)

def process_task(task_id):
    """处理任务"""
    # 检查任务是否已处理
    if load_task_state(task_id) == "completed":
        print(f"Task {task_id} already completed.")
        return

    # 检查任务是否正在处理
    if load_task_state(task_id) == "processing":
        print(f"Task {task_id} is already being processed.")
        return

    # 设置任务状态为处理中
    save_task_state(task_id, "processing")

    # 模拟任务处理
    for retry in range(MAX_RETRIES):
        try:
            # 模拟任务执行
            result = execute_task(task_id)
            if result is not None:
                # 任务成功
                save_task_state(task_id, "completed")
                return
        except Exception as e:
            print(f"Task {task_id} failed with error: {e}")
            if retry < MAX_RETRIES - 1:
                # 重试
                save_retry_info(task_id, retry + 1)
                time.sleep(RETRY_DELAY)
            else:
                # 重试失败
                save_task_state(task_id, "failed")
                return
    # 重试失败
    save_task_state(task_id, "failed")

def execute_task(task_id):
    """模拟任务执行"""
    # 这里应替换为实际的任务逻辑
    print(f"Processing task {task_id}...")
    time.sleep(2)
    return "Task completed"

# 主程序
if __name__ == "__main__":
    # 模拟多个任务
    for i in range(5):
        task_id = f"task_{i}"
        process_task(task_id)
