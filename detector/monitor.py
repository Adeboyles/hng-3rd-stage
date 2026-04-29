import time
import json
import os


def tail_log(log_path):
    """Continuously tail the nginx access log and yield parsed JSON lines."""
    while not os.path.exists(log_path):
        print(f"[monitor] Waiting for log file: {log_path}")
        time.sleep(2)

    with open(log_path, "r") as f:
        f.seek(0, 2)  # seek to end of file
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                yield entry
            except json.JSONDecodeError:
                continue
