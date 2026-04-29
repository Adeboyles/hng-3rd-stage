import time
import math
import threading
from collections import defaultdict, deque


class BaselineTracker:
    def __init__(self, config):
        self.window_minutes = config.get("baseline_window_minutes", 30)
        self.recalc_interval = config.get("baseline_recalc_interval", 60)
        self.floor = config.get("baseline_floor_rps", 1.0)
        self.min_samples = config.get("min_baseline_samples", 10)

        # Rolling per-second counts (global)
        self.per_second_counts = deque()  # (timestamp, count)
        self.current_second = int(time.time())
        self.current_count = 0

        # Per-hour slots
        self.hourly_slots = defaultdict(list)  # hour -> [per_second_counts]

        # Computed baseline
        self.effective_mean = self.floor
        self.effective_stddev = 1.0

        # Error baseline
        self.error_mean = 0.0
        self.error_stddev = 0.0
        self.per_second_errors = deque()
        self.current_errors = 0

        self.lock = threading.Lock()
        self._start_recalc_loop()

    def record_request(self, is_error=False):
        now = int(time.time())
        with self.lock:
            if now != self.current_second:
                self.per_second_counts.append((self.current_second, self.current_count))
                self.per_second_errors.append((self.current_second, self.current_errors))

                hour = self.current_second // 3600
                self.hourly_slots[hour].append(self.current_count)

                # Evict entries older than window
                cutoff = now - (self.window_minutes * 60)
                while self.per_second_counts and self.per_second_counts[0][0] < cutoff:
                    self.per_second_counts.popleft()
                while self.per_second_errors and self.per_second_errors[0][0] < cutoff:
                    self.per_second_errors.popleft()

                self.current_second = now
                self.current_count = 0
                self.current_errors = 0

            self.current_count += 1
            if is_error:
                self.current_errors += 1

    def _recalculate(self):
        with self.lock:
            counts = [c for _, c in self.per_second_counts]
            errors = [e for _, e in self.per_second_errors]

            # Prefer current hour data if enough samples
            current_hour = int(time.time()) // 3600
            hourly = self.hourly_slots.get(current_hour, [])
            if len(hourly) >= self.min_samples:
                counts = hourly

            if len(counts) >= self.min_samples:
                mean = sum(counts) / len(counts)
                variance = sum((x - mean) ** 2 for x in counts) / len(counts)
                stddev = math.sqrt(variance)
                self.effective_mean = max(mean, self.floor)
                self.effective_stddev = max(stddev, 0.5)
            else:
                self.effective_mean = self.floor
                self.effective_stddev = 1.0

            if len(errors) >= self.min_samples:
                emean = sum(errors) / len(errors)
                evar = sum((x - emean) ** 2 for x in errors) / len(errors)
                self.error_mean = max(emean, 0.0)
                self.error_stddev = math.sqrt(evar)

        return self.effective_mean, self.effective_stddev

    def get_baseline(self):
        with self.lock:
            return self.effective_mean, self.effective_stddev

    def get_error_baseline(self):
        with self.lock:
            return self.error_mean, self.error_stddev

    def _start_recalc_loop(self):
        def loop():
            while True:
                time.sleep(self.recalc_interval)
                mean, stddev = self._recalculate()
                from audit import write_audit
                write_audit("BASELINE_RECALC", "global",
                            condition=f"mean={mean:.2f} stddev={stddev:.2f}",
                            rate=mean, baseline=mean)
        t = threading.Thread(target=loop, daemon=True)
        t.start()
