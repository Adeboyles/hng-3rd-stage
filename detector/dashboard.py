import time
import psutil
import threading
from flask import Flask, jsonify, render_template_string
from blocker import get_banned_ips
from detector import get_top_ips, get_global_rate
from baseline import BaselineTracker

app = Flask(__name__)
_start_time = time.time()
_baseline_ref = None


def set_baseline(b):
    global _baseline_ref
    _baseline_ref = b


HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>HNG Anomaly Detector</title>
  <meta charset="utf-8"/>
  <style>
    body { font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }
    h1 { color: #58a6ff; }
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
            padding: 16px; margin: 12px 0; }
    table { width: 100%; border-collapse: collapse; }
    th { color: #58a6ff; text-align: left; padding: 6px; border-bottom: 1px solid #30363d; }
    td { padding: 6px; border-bottom: 1px solid #21262d; }
    .banned { color: #f85149; }
    .metric { font-size: 2em; color: #3fb950; }
    .label { color: #8b949e; font-size: 0.85em; }
  </style>
  <script>
    async function refresh() {
      const r = await fetch('/api/metrics');
      const d = await r.json();

      document.getElementById('uptime').innerText = d.uptime;
      document.getElementById('global_rps').innerText = d.global_rps;
      document.getElementById('cpu').innerText = d.cpu + '%';
      document.getElementById('mem').innerText = d.memory + '%';
      document.getElementById('mean').innerText = d.mean;
      document.getElementById('stddev').innerText = d.stddev;

      let banHTML = '';
      d.banned_ips.forEach(ip => {
        banHTML += `<tr><td class="banned">${ip}</td></tr>`;
      });
      document.getElementById('banned').innerHTML = banHTML || '<tr><td>None</td></tr>';

      let topHTML = '';
      d.top_ips.forEach(([ip, count]) => {
        topHTML += `<tr><td>${ip}</td><td>${count} req/60s</td></tr>`;
      });
      document.getElementById('top_ips').innerHTML = topHTML || '<tr><td colspan=2>No data</td></tr>';
    }
    refresh();
    setInterval(refresh, 3000);
  </script>
</head>
<body>
  <h1>🛡️ HNG Anomaly Detection Dashboard</h1>

  <div class="card">
    <div class="label">Uptime</div>
    <div class="metric" id="uptime">-</div>
  </div>

  <div class="card" style="display:flex; gap:40px;">
    <div>
      <div class="label">Global Req/s (last 60s)</div>
      <div class="metric" id="global_rps">-</div>
    </div>
    <div>
      <div class="label">CPU Usage</div>
      <div class="metric" id="cpu">-</div>
    </div>
    <div>
      <div class="label">Memory Usage</div>
      <div class="metric" id="mem">-</div>
    </div>
    <div>
      <div class="label">Baseline Mean</div>
      <div class="metric" id="mean">-</div>
    </div>
    <div>
      <div class="label">Baseline StdDev</div>
      <div class="metric" id="stddev">-</div>
    </div>
  </div>

  <div class="card">
    <h3>🚫 Banned IPs</h3>
    <table><thead><tr><th>IP Address</th></tr></thead>
    <tbody id="banned"></tbody></table>
  </div>

  <div class="card">
    <h3>📊 Top 10 Source IPs (last 60s)</h3>
    <table><thead><tr><th>IP</th><th>Requests</th></tr></thead>
    <tbody id="top_ips"></tbody></table>
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/metrics")
def metrics():
    uptime_secs = int(time.time() - _start_time)
    hours, rem = divmod(uptime_secs, 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{hours}h {mins}m {secs}s"

    mean, stddev = _baseline_ref.get_baseline() if _baseline_ref else (0, 0)

    return jsonify({
        "uptime": uptime_str,
        "global_rps": get_global_rate(),
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "mean": round(mean, 2),
        "stddev": round(stddev, 2),
        "banned_ips": list(get_banned_ips().keys()),
        "top_ips": get_top_ips(10),
    })


def start_dashboard(port=8080):
    t = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False),
        daemon=True
    )
    t.start()
