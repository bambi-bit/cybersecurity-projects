#!/usr/bin/env python3
"""
Log Monitoring Agent
---------------------
Tails a log file (default: /var/log/auth.log) in real time and flags
suspicious activity based on simple rules:

  - N+ failed SSH password attempts from the same source within a time window
  - Repeated "invalid user" attempts (possible username enumeration)
  - Repeated failed sudo attempts

Alerts are printed to console and appended to alerts.log for evidence.

Usage:
    python3 log_monitor.py                     # monitor default auth.log
    python3 log_monitor.py --file /path/to/log # monitor a custom log file
    python3 log_monitor.py --demo              # run against sample_auth.log for testing

This is intentionally simple and readable so you can explain every line
in an interview or CV writeup. Extend it (email/webhook alerts, more
rules, a dashboard) once the core loop works.
"""

import argparse
import re
import time
from collections import defaultdict, deque
from datetime import datetime

# ---- Config: tune these thresholds ----
FAILED_LOGIN_THRESHOLD = 5      # number of failed attempts...
FAILED_LOGIN_WINDOW = 120       # ...within this many seconds -> alert
SUDO_FAIL_THRESHOLD = 3
SUDO_FAIL_WINDOW = 300

ALERT_LOG_PATH = "alerts.log"

# ---- Regex patterns for common auth.log lines ----
PATTERNS = {
    "failed_password": re.compile(
        r"Failed password for (invalid user )?(?P<user>\S+) from (?P<ip>[\d.]+)"
    ),
    "invalid_user": re.compile(
        r"Invalid user (?P<user>\S+) from (?P<ip>[\d.]+)"
    ),
    "sudo_fail": re.compile(
        r"sudo:.*authentication failure.*user=(?P<user>\S+)"
    ),
}


class EventTracker:
    """Keeps a rolling window of timestamps per key (e.g. per source IP)."""

    def __init__(self):
        self.events = defaultdict(deque)

    def record(self, key, window_seconds):
        now = time.time()
        dq = self.events[key]
        dq.append(now)
        # drop events outside the window
        while dq and now - dq[0] > window_seconds:
            dq.popleft()
        return len(dq)


def write_alert(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] ALERT: {message}"
    print(line)
    with open(ALERT_LOG_PATH, "a") as f:
        f.write(line + "\n")


def process_line(line, trackers):
    m = PATTERNS["failed_password"].search(line)
    if m:
        ip = m.group("ip")
        user = m.group("user")
        count = trackers["failed_login"].record(ip, FAILED_LOGIN_WINDOW)
        if count >= FAILED_LOGIN_THRESHOLD:
            write_alert(
                f"{count} failed password attempts from {ip} "
                f"(latest target user: {user}) in the last "
                f"{FAILED_LOGIN_WINDOW}s — possible brute force"
            )
        return

    m = PATTERNS["invalid_user"].search(line)
    if m:
        ip = m.group("ip")
        user = m.group("user")
        count = trackers["invalid_user"].record(ip, FAILED_LOGIN_WINDOW)
        if count >= FAILED_LOGIN_THRESHOLD:
            write_alert(
                f"{count} invalid-user login attempts from {ip} "
                f"(latest: '{user}') in the last {FAILED_LOGIN_WINDOW}s "
                f"— possible username enumeration"
            )
        return

    m = PATTERNS["sudo_fail"].search(line)
    if m:
        user = m.group("user")
        count = trackers["sudo_fail"].record(user, SUDO_FAIL_WINDOW)
        if count >= SUDO_FAIL_THRESHOLD:
            write_alert(
                f"{count} failed sudo attempts by user '{user}' in the "
                f"last {SUDO_FAIL_WINDOW}s — possible privilege escalation attempt"
            )
        return


def tail_file(path):
    """Generator that yields new lines appended to a file (like `tail -f`)."""
    with open(path, "r") as f:
        f.seek(0, 2)  # go to end of file
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            yield line


def replay_file(path):
    """Read an entire file line by line (for demo/testing on a static sample log)."""
    with open(path, "r") as f:
        for line in f:
            yield line
            time.sleep(0.05)  # small delay so timestamps/windows behave sensibly


def main():
    parser = argparse.ArgumentParser(description="Simple log monitoring agent")
    parser.add_argument(
        "--file", default="/var/log/auth.log",
        help="Path to log file to monitor (default: /var/log/auth.log)"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Replay sample_auth.log instead of tailing a live file (for testing without root/lab access)"
    )
    args = parser.parse_args()

    trackers = {
        "failed_login": EventTracker(),
        "invalid_user": EventTracker(),
        "sudo_fail": EventTracker(),
    }

    if args.demo:
        print("Running in demo mode against sample_auth.log ...\n")
        source = replay_file("sample_auth.log")
    else:
        print(f"Monitoring {args.file} (Ctrl+C to stop)...\n")
        source = tail_file(args.file)

    try:
        for line in source:
            process_line(line, trackers)
    except KeyboardInterrupt:
        print("\nStopped monitoring.")


if __name__ == "__main__":
    main()
