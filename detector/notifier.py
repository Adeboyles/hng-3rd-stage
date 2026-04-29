import requests
from datetime import datetime, timezone


def send_slack(webhook_url, message):
    try:
        requests.post(webhook_url, json={"text": message}, timeout=5)
    except Exception as e:
        print(f"[notifier] Slack error: {e}")


def ban_alert(webhook_url, ip, condition, rate, baseline, duration):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = (
        f":rotating_light: *BAN ALERT*\n"
        f">*IP:* `{ip}`\n"
        f">*Condition:* {condition}\n"
        f">*Current Rate:* {rate:.2f} req/s\n"
        f">*Baseline:* {baseline:.2f} req/s\n"
        f">*Ban Duration:* {duration}\n"
        f">*Time:* {ts}"
    )
    send_slack(webhook_url, msg)


def unban_alert(webhook_url, ip, duration_next):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = (
        f":white_check_mark: *UNBAN ALERT*\n"
        f">*IP:* `{ip}`\n"
        f">*Next ban duration if re-offends:* {duration_next}\n"
        f">*Time:* {ts}"
    )
    send_slack(webhook_url, msg)


def global_alert(webhook_url, condition, rate, baseline):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = (
        f":warning: *GLOBAL ANOMALY ALERT*\n"
        f">*Condition:* {condition}\n"
        f">*Global Rate:* {rate:.2f} req/s\n"
        f">*Baseline:* {baseline:.2f} req/s\n"
        f">*Time:* {ts}"
    )
    send_slack(webhook_url, msg)
