import time
import math
import threading
from collections import defaultdict, deque
from blocker import ban_ip, is_banned, get_banned_ips
from unbanner import schedule_unban
from notifier import global_alert
from audit import write_audit

_lock = threading.Lock()

# Deque windows: ip -> deque of timestamps
ip_windows = defaultdict(deque)
global_window = deque()

# Track recent errors per IP
ip_error_windows = defaultdict(deque)

# Global anomaly cooldown (avoid spam)
_last_global_alert = 0
GLOBAL_ALERT_COOLDOWN = 60  # seconds


def _evict(dq, window_seconds):
    cutoff = time.time() - window_seconds
    while dq and dq[0] < cutoff:
        dq.popleft()


def process_entry(entry, baseline_tracker, config):
    global _last_global_alert

    ip = entry.get("source_ip", "")
    status = entry.get("status", 200)
    now = time.time()

    window_seconds = config.get("window_seconds", 60)
    z_thresh = config.get("z_score_threshold", 3.0)
    rate_mult = config.get("rate_multiplier", 5)
    err_mult = config.get("error_rate_multiplier", 3)

    is_error = str(status).startswith("4") or str(status).startswith("5")
    baseline_tracker.record_request(is_error=is_error)

    mean, stddev = baseline_tracker.get_baseline()
    err_mean, err_stddev = baseline_tracker.get_error_baseline()

    with _lock:
        # Update windows
        global_window.append(now)
        _evict(global_window, window_seconds)

        ip_windows[ip].append(now)
        _evict(ip_windows[ip], window_seconds)

        if is_error:
            ip_error_windows[ip].append(now)
        _evict(ip_error_windows[ip], window_seconds)

        ip_rate = len(ip_windows[ip])
        global_rate = len(global_window)
        ip_error_rate = len(ip_error_windows[ip])

    # --- Check if error rate is high for this IP → tighten thresholds ---
    tightened = False
    if err_mean > 0 and ip_error_rate >= err_mult * err_mean:
        z_thresh = z_thresh * 0.6
        rate_mult = rate_mult * 0.6
        tightened = True

    # --- Per-IP anomaly detection ---
    if ip and not is_banned(ip):
        z_score = (ip_rate - mean) / stddev if stddev > 0 else 0
        if z_score > z_thresh or ip_rate > rate_mult * mean:
            condition = (
                f"z_score={z_score:.2f}" if z_score > z_thresh
                else f"rate={ip_rate} > {rate_mult}x mean={mean:.2f}"
            )
            if tightened:
                condition += " (tightened thresholds)"

            schedule = config.get("unban_schedule", [600, 1800, 7200])
            from unbanner import ban_counts
            count = ban_counts.get(ip, 0)
            duration = schedule[count] if count < len(schedule) else None

            if duration is not None:
                ban_ip(ip, config, condition, ip_rate, mean, duration)
                schedule_unban(ip, config)

    # --- Global anomaly detection ---
    z_global = (global_rate - mean) / stddev if stddev > 0 else 0
    if z_global > z_thresh or global_rate > rate_mult * mean:
        if now - _last_global_alert > GLOBAL_ALERT_COOLDOWN:
            _last_global_alert = now
            condition = (
                f"global z_score={z_global:.2f}" if z_global > z_thresh
                else f"global rate={global_rate} > {rate_mult}x mean={mean:.2f}"
            )
            global_alert(config["slack_webhook"], condition, global_rate, mean)
            write_audit("GLOBAL_ANOMALY", "global", condition=condition,
                        rate=global_rate, baseline=mean)


def get_top_ips(n=10):
    with _lock:
        return sorted(
            [(ip, len(dq)) for ip, dq in ip_windows.items()],
            key=lambda x: x[1], reverse=True
        )[:n]


def get_global_rate():
    with _lock:
        return len(global_window)
