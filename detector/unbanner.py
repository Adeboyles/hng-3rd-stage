import time
import threading
from blocker import unban_ip, banned_ips
from notifier import unban_alert
from audit import write_audit

# ip -> number of times banned
ban_counts = {}
_lock = threading.Lock()
_scheduled = set()
_sched_lock = threading.Lock()


def schedule_unban(ip, config):
    with _sched_lock:
        if ip in _scheduled:
            return
        _scheduled.add(ip)

    with _lock:
        count = ban_counts.get(ip, 0)
        ban_counts[ip] = count + 1

    schedule = config.get("unban_schedule", [600, 1800, 7200])

    if count >= len(schedule):
        print(f"[unbanner] {ip} is permanently banned (offense #{count + 1})")
        write_audit("PERMANENT_BAN", ip, condition="repeat offender",
                    rate=0, baseline=0, duration="permanent")
        with _sched_lock:
            _scheduled.discard(ip)
        return

    delay = schedule[count]

    def do_unban():
        time.sleep(delay)
        unban_ip(ip)

        # Next ban duration
        next_index = count + 1
        if next_index < len(schedule):
            next_dur = f"{schedule[next_index]}s"
        else:
            next_dur = "permanent"

        unban_alert(config["slack_webhook"], ip, next_dur)
        write_audit("UNBAN", ip, condition="scheduled",
                    rate=0, baseline=0, duration=f"{delay}s")

        with _sched_lock:
            _scheduled.discard(ip)

    t = threading.Thread(target=do_unban, daemon=True)
    t.start()
    print(f"[unbanner] Scheduled unban for {ip} in {delay}s")
