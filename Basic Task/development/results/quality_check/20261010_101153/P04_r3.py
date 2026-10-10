import os
import time
import json
from datetime import datetime

# 任务配置
TASK_DIR = 'tasks'
MAX_RETRIES = 3
TASK_ID_FORMAT = 'task_{}_{}_{}'

# 任务状态
TASK_STATUS_RUNNING = 'running'
TASK_STATUS_FAILED = 'failed'
TASK_STATUS_COMPLETED = 'completed'

def get_task_id(task_name, timestamp):
    return TASK_ID_FORMAT.format(task_name, timestamp, os.getpid())

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
    task_status = load_task_state(task_id)
    if task_status and task_status['status'] == TASK_STATUS_RUNNING:
        print(f"Task {task_id} is already running.")
        return

    if task_status and task_status['status'] == TASK_STATUS_COMPLETED:
        print(f"Task {task_id} has already been completed.")
        return

    # Start task
    print(f"Starting task {task_id}...")
    try:
        result = task_func()
        save_task_state(task_id, {'status': TASK_STATUS_COMPLETED})
        print(f"Task {task_id} completed with result: {result}")
    except Exception as e:
        print(f"Task {task_id} failed with error: {e}")
        if task_status and task_status['status'] == TASK_STATUS_RUNNING:
            print(f"Task {task_id} is already running.")
        else:
            # Attempt to retry
            retry_count = 0
            while retry_count < MAX_RETRIES:
                try:
                    result = task_func()
                    save_task_state(task_id, {'status': TASK_STATUS_COMPLETED})
                    print(f"Task {task_id} completed with result: {result}")
                    break
                except Exception as e:
                    print(f"Task {task_id} failed with error: {e}")
                    retry_count += 1
                    if retry_count == MAX_RETRIES:
                        save_task_state(task_id, {'status': TASK_STATUS_FAILED})
                        print(f"Task {task_id} failed after {MAX_RETRIES} retries.")
    finally:
        # Ensure task state is saved
        if task_status and task_status['status'] == TASK_STATUS_RUNNING:
            save_task_state(task_id, {'status': TASK_STATUS_FAILED})

def main():
    # Example task function
    def example_task():
        # Simulate a task that may fail
        if random.random() < 0.5:
            raise Exception("Task failed")
        return "Task completed"

    # Run the task
    task_name = "example_task"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    task_id = get_task_id(task_name, timestamp)
    process_task(task_id, example_task)

if __name__ == "__main__":
    main()
