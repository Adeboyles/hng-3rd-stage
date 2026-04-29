import yaml
import threading
from monitor import tail_log
from baseline import BaselineTracker
from detector import process_entry
from dashboard import start_dashboard, set_baseline


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    print("[main] Starting HNG Anomaly Detection Engine...")

    # Init baseline tracker
    baseline = BaselineTracker(config)
    set_baseline(baseline)

    # Start dashboard
    port = config.get("dashboard_port", 8080)
    start_dashboard(port)
    print(f"[main] Dashboard running on port {port}")

    # Start log monitoring (blocking)
    log_path = config.get("log_path", "/var/log/nginx/hng-access.log")
    print(f"[main] Monitoring log: {log_path}")

    for entry in tail_log(log_path):
        try:
            process_entry(entry, baseline, config)
        except Exception as e:
            print(f"[main] Error processing entry: {e}")


if __name__ == "__main__":
    main()
