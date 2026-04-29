# HNG Stage 3 — Anomaly Detection Engine

## Live URLs
- **Server IP:** 54.172.183.212
- **Metrics Dashboard:** http://boyles-detector.duckdns.org:8080
- **GitHub Repo:** https://github.com/Adeboyles/hng-3rd-stage.git

## Blog Post
YOUR_BLOG_URL=https://medium.com/@oluwoleadeboye3/how-i-built-a-real-time-ddos-detection-engine-from-scratch-b608c023f259

## Language Choice
Python — chosen for its readable syntax, rich standard library, and ease of
working with system tools like subprocess for iptables, threading for
concurrent operations, and Flask for the dashboard.

## How the Sliding Window Works
Two deque-based windows track request timestamps — one per IP, one global —
over the last 60 seconds. On every incoming request, timestamps older than
60 seconds are evicted from the left of the deque using a while loop. The
current rate is simply the length of the deque after eviction. This gives an
accurate real-time count of requests in the last 60 seconds without any
per-minute approximation.

## How the Baseline Works
A rolling 30-minute window of per-second request counts is maintained using
a deque. Every 60 seconds, the mean and standard deviation are recalculated
from all samples in the window. Per-hour slots are also maintained — if the
current hour has enough samples (at least 3), those are preferred over the
full 30-minute window for more accurate recent-traffic awareness. The baseline
mean never drops below 1.0 req/s (floor value) to avoid false positives
during idle periods.

## How Detection Works
On every request, the current rate (deque length) is compared against the
baseline using two conditions — whichever fires first triggers an anomaly:
1. Z-score > 0.5 — rate deviates more than 0.5 standard deviations from mean
2. Rate > 1.5x the baseline mean
If an IP's 4xx/5xx error rate is 3x the baseline error rate, thresholds are
automatically tightened by 40% for that IP.

## How iptables Blocking Works
When a per-IP anomaly is detected, the daemon runs:
`iptables -I INPUT -s <ip> -j DROP`
This inserts a DROP rule at the top of the INPUT chain, immediately blocking
all traffic from that IP at the kernel level. The rule is removed automatically
on a backoff schedule: 10 minutes, 30 minutes, 2 hours, then permanent ban.
A Slack alert is sent within 10 seconds of every ban and unban.

## Setup Instructions

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/hng-stage3.git
cd hng-stage3
```

### 2. Set your Slack webhook in detector/config.yaml
```yaml
slack_webhook: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### 3. Set your server IP in docker-compose.yml
```yaml
NEXTCLOUD_TRUSTED_DOMAINS=YOUR_SERVER_IP
```

### 4. Install Docker
```bash
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 5. Launch the stack
```bash
docker compose up -d --build
```

### 6. Verify everything is running
```bash
docker compose ps
cat /var/log/detector/audit.log
```

### 7. Access the dashboard
