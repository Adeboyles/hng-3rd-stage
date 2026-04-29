import subprocess
import threading
from audit import write_audit
from notifier import ban_alert

banned_ips = {}  # ip -> ban_count
_lock = threading.Lock()


def is_banned(ip):
    with _lock:
        return ip in banned_ips


def ban_ip(ip, config, condition, rate, baseline, duration_seconds):
    with _lock:
        if ip in banned_ips:
            return
        banned_ips[ip] = banned_ips.get(ip, 0)

    try:
        subprocess.run(
            ["iptables", "-I", "INPUT", "-s", ip, "-j", "DROP"],
            check=True, capture_output=True
        )
        duration_str = f"{duration_seconds}s"
        write_audit("BAN", ip, condition=condition,
                    rate=rate, baseline=baseline, duration=duration_str)
        ban_alert(config["slack_webhook"], ip, condition, rate, baseline, duration_str)
        print(f"[blocker] Banned {ip} for {duration_str}")
    except subprocess.CalledProcessError as e:
        print(f"[blocker] iptables error: {e}")


def unban_ip(ip):
    try:
        subprocess.run(
            ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"],
            check=True, capture_output=True
        )
        with _lock:
            if ip in banned_ips:
                del banned_ips[ip]
        print(f"[blocker] Unbanned {ip}")
    except subprocess.CalledProcessError as e:
        print(f"[blocker] iptables unban error: {e}")


def get_banned_ips():
    with _lock:
        return dict(banned_ips)
