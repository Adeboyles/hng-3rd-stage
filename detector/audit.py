import os
import threading
from datetime import datetime, timezone

LOG_PATH = "/var/log/detector/audit.log"
_lock = threading.Lock()


def write_audit(action, ip, condition="", rate=0, baseline=0, duration=""):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (
        f"[{timestamp}] {action} {ip} | {condition} | "
        f"rate={rate:.2f} | baseline={baseline:.2f} | duration={duration}\n"
    )
    with _lock:
        with open(LOG_PATH, "a") as f:
            f.write(line)
    print(line.strip())
