import os
import time
import json
from datetime import datetime, timedelta

# 任务配置
TASK_DIR = 'tasks'
MAX_RETRIES = 3
RETRY_DELAY = 1  # 秒
TASK_ID_FORMAT = 'task_{}_{}_{}'

# 任务状态
TASK_STATUS_RUNNING = 'running'
TASK_STATUS_FAILED = 'failed'
TASK_STATUS_COMPLETED = 'completed'

def get_task_id(task_name, timestamp):
    return TASK_ID_FORMAT.format(task_name, timestamp.strftime('%Y%m%d%H%M%S'), os.getpid())

def save_task_state(task_id, status):
    with open(os.path.join(TASK_DIR, task_id + '.json'), 'w') as f:
        json.dump({'status': status}, f)

def load_task_state(task_id):
    file_path = os.path.join(TASK_DIR, task_id + '.json')
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r') as f:
        return json.load(f)

def process_task(task_id, task_func):
    task_state = load_task_state(task_id)
    if task_state and task_state['status'] == TASK_STATUS_RUNNING:
        print(f"Task {task_id} is already running.")
        return

    if task_state and task_state['status'] == TASK_STATUS_FAILED:
        print(f"Task {task_id} has failed. Skipping.")
        return

    # Start task
    print(f"Starting task {task_id}...")
    try:
        task_func()
        save_task_state(task_id, {'status': TASK_STATUS_COMPLETED})
        print(f"Task {task_id} completed.")
    except Exception as e:
        print(f"Task {task_id} failed: {e}")
        if task_state and task_state['status'] == TASK_STATUS_RUNNING:
            print(f"Task {task_id} is already running. Skipping.")
        else:
            # Retry
            for i in range(MAX_RETRIES):
                if i > 0:
                    time.sleep(RETRY_DELAY)
                try:
                    task_func()
                    save_task_state(task_id, {'status': TASK_STATUS_COMPLETED})
                    print(f"Task {task_id} completed after retry {i+1}.")
                    break
                except Exception as e:
                    print(f"Task {task_id} failed after retry {i+1}: {e}")
            else:
                save_task_state(task_id, {'status': TASK_STATUS_FAILED})
                print(f"Task {task_id} failed after all retries.")

def main():
    # Example task function
    def example_task():
        # Simulate a task that may fail
        if random.random() < 0.5:
            raise Exception("Task failed")
        print("Task executed successfully")

    # Run the task
    task_name = 'example_task'
    timestamp = datetime.now()
    task_id = get_task_id(task_name, timestamp)
    process_task(task_id, example_task)

if __name__ == '__main__':
    main()
