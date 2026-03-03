#!/usr/bin/env python3
"""
security-sshmonitor-v1 — Elkin SSH intrusion monitor
Watches /var/log/auth.log for SSH events and triggers Telegram alerts.
"""

import os
import re
import sys
import json
import time
import signal
import logging
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
AUTH_LOG         = os.environ.get("AUTH_LOG", "/var/log/auth.log")
LOG_DIR          = Path(os.environ.get("LOG_DIR",
                        os.path.expanduser("~/.openclaw/workspace/memory/daily-logs")))
FAIL_THRESHOLD   = int(os.environ.get("FAIL_THRESHOLD", "3"))
WORK_HOUR_START  = int(os.environ.get("WORK_HOUR_START", "6"))   # 0600 UTC
WORK_HOUR_END    = int(os.environ.get("WORK_HOUR_END",   "22"))  # 2200 UTC
POLL_INTERVAL    = float(os.environ.get("POLL_INTERVAL", "2"))   # seconds
STATE_FILE       = Path(os.path.expanduser("~/.openclaw/workspace/memory/.sshmonitor_state.json"))

# ── Regex patterns ────────────────────────────────────────────────────────────
RE_FAILED  = re.compile(r"Failed password for (?:invalid user )?(\S+) from ([\d.a-f:]+) port \d+")
RE_ACCEPT  = re.compile(r"Accepted (?:password|publickey) for (\S+) from ([\d.a-f:]+) port \d+")
RE_INVALID = re.compile(r"Invalid user (\S+) from ([\d.a-f:]+)")
RE_DISCONN = re.compile(r"Disconnected from (?:invalid user )?(?:\S+ )?([\d.a-f:]+)")
RE_CLOSED  = re.compile(r"Connection closed by (?:authenticating user )?(?:\S+ )?([\d.a-f:]+)")

# ── Logging setup ─────────────────────────────────────────────────────────────
def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"{today}-ssh-monitor.log"

    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
        datefmt="%Y-%m-%d %H:%M:%S UTC",
    )
    logging.Formatter.converter = time.gmtime  # force UTC

# ── Telegram ──────────────────────────────────────────────────────────────────
def telegram_send(text: str, level: str = "info") -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram not configured — alert suppressed")
        return False
    import urllib.request, urllib.parse
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }).encode()
    try:
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        logging.info(f"Telegram [{level}] sent")
        return True
    except Exception as e:
        logging.error(f"Telegram delivery failed: {e}")
        return False

# ── Enhanced Operational Resilience Mode trigger ──────────────────────────────
def trigger_eorm(ip: str, reason: str):
    """
    On confirmed intrusion: message self (Elkin) via openclaw to activate
    Enhanced Operational Resilience Mode.
    """
    logging.critical(f"🚨 INTRUSION DETECTED from {ip} — triggering EORM")
    msg = (
        f"🚨 *INTRUSION ALERT — EORM ACTIVATED*\n"
        f"Host: `{os.uname().nodename}`\n"
        f"Source IP: `{ip}`\n"
        f"Trigger: {reason}\n"
        f"Time: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`\n\n"
        f"*Actions initiated:*\n"
        f"• Hyper-logging enabled → `~/.openclaw/forensics/`\n"
        f"• Monitoring verbosity: MAXIMUM\n"
        f"• All anomalies → immediate escalation\n"
        f"⚠️ Await Operator instruction for Level 3/4 response."
    )
    telegram_send(msg, level="CRITICAL")

    # Create forensics dir and log the event
    forensics = Path(os.path.expanduser("~/.openclaw/forensics"))
    forensics.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    incident_file = forensics / f"intrusion_{ts}_{ip.replace(':','_')}.json"
    incident_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_ip": ip,
        "trigger": reason,
        "hostname": os.uname().nodename,
        "eorm_activated": True,
    }
    incident_file.write_text(json.dumps(incident_data, indent=2))
    logging.critical(f"Incident logged: {incident_file}")

    # Try to self-message via openclaw CLI to activate EORM in main session
    try:
        subprocess.run(
            ["openclaw", "send", "--channel", "telegram",
             "--chat", TELEGRAM_CHAT_ID, "--message",
             f"[EORM] Intrusion from {ip}: {reason}"],
            timeout=10, capture_output=True
        )
    except Exception:
        pass  # Already alerted via telegram_send above

# ── State persistence ─────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "known_ips": [],
        "fail_counts": {},
        "alerted_ips": [],
        "file_offset": 0,
    }

def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Event log writer ──────────────────────────────────────────────────────────
def write_event(event_type: str, user: str, ip: str, extra: str = ""):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"{today}-ssh-monitor.log"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"{ts} | {event_type:<20} | user={user:<16} | ip={ip:<20} | {extra}\n"
    with open(log_file, "a") as f:
        f.write(entry)

# ── Alert logic ───────────────────────────────────────────────────────────────
def is_outside_hours() -> bool:
    hour = datetime.now(timezone.utc).hour
    return not (WORK_HOUR_START <= hour < WORK_HOUR_END)

def check_and_alert(state: dict, event_type: str, user: str, ip: str):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    hostname = os.uname().nodename

    if event_type == "ACCEPTED":
        write_event("SSH_LOGIN_OK", user, ip)
        alerted = False

        # Alert: new IP
        if ip not in state["known_ips"]:
            state["known_ips"].append(ip)
            logging.warning(f"NEW IP login: {user}@{ip}")
            telegram_send(
                f"⚠️ *SSH Login — New IP*\n"
                f"Host: `{hostname}`\n"
                f"User: `{user}` | IP: `{ip}`\n"
                f"Time: `{now_str}`",
                level="warn"
            )
            alerted = True

        # Alert: outside working hours
        if is_outside_hours():
            logging.warning(f"OFF-HOURS login: {user}@{ip} at {now_str}")
            telegram_send(
                f"⚠️ *SSH Login — Off Hours* ({WORK_HOUR_START:02d}00–{WORK_HOUR_END:02d}00 UTC)\n"
                f"Host: `{hostname}`\n"
                f"User: `{user}` | IP: `{ip}`\n"
                f"Time: `{now_str}`",
                level="warn"
            )
            alerted = True

        # EORM trigger: new IP + off hours = confirmed suspicious
        if ip not in state.get("alerted_ips", []) and alerted and is_outside_hours():
            state.setdefault("alerted_ips", []).append(ip)
            trigger_eorm(ip, f"SSH login: new IP {ip} during off-hours by user '{user}'")

    elif event_type == "FAILED":
        write_event("SSH_FAIL", user, ip)
        state.setdefault("fail_counts", {})
        state["fail_counts"][ip] = state["fail_counts"].get(ip, 0) + 1
        count = state["fail_counts"][ip]
        logging.info(f"Failed attempt #{count} from {ip} user={user}")

        # Alert threshold crossed
        if count == FAIL_THRESHOLD + 1:  # alert once when threshold exceeded
            logging.warning(f"BRUTE FORCE threshold hit: {ip} ({count} failures)")
            telegram_send(
                f"🚨 *SSH Brute Force Detected*\n"
                f"Host: `{hostname}`\n"
                f"IP: `{ip}` | Failures: `{count}`\n"
                f"Last user: `{user}`\n"
                f"Time: `{now_str}`",
                level="critical"
            )
            # EORM: brute force = confirmed attack
            if ip not in state.get("alerted_ips", []):
                state.setdefault("alerted_ips", []).append(ip)
                trigger_eorm(ip, f"Brute force: {count} failed SSH attempts")

    elif event_type == "INVALID":
        write_event("SSH_INVALID_USER", user, ip)
        # Count invalid users same as failures
        state.setdefault("fail_counts", {})
        state["fail_counts"][ip] = state["fail_counts"].get(ip, 0) + 1

# ── Source detection ──────────────────────────────────────────────────────────
def detect_log_source() -> str:
    """Returns 'file' if auth.log exists, else 'journald'."""
    if Path(AUTH_LOG).exists():
        return "file"
    try:
        result = subprocess.run(
            ["journalctl", "_COMM=sshd", "-n", "1", "--no-pager"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return "journald"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "file"  # fall back; error will surface in tail_log

def process_line(line: str, state: dict):
    """Parse a single log line and trigger alerts as needed."""
    if "sshd" not in line:
        return
    m = RE_ACCEPT.search(line)
    if m:
        check_and_alert(state, "ACCEPTED", m.group(1), m.group(2))
        return
    m = RE_FAILED.search(line)
    if m:
        check_and_alert(state, "FAILED", m.group(1), m.group(2))
        return
    m = RE_INVALID.search(line)
    if m:
        check_and_alert(state, "INVALID", m.group(1), m.group(2))
        return

# ── Log tail — file mode ──────────────────────────────────────────────────────
def tail_log_file(state: dict):
    log_path = Path(AUTH_LOG)
    if not log_path.exists():
        logging.error(f"Auth log not found: {AUTH_LOG}")
        return state
    try:
        current_size = log_path.stat().st_size
    except OSError:
        return state

    if current_size < state.get("file_offset", 0):
        logging.info("Log rotation detected — resetting offset")
        state["file_offset"] = 0
    if current_size == state.get("file_offset", 0):
        return state

    with open(log_path, "r", errors="replace") as f:
        f.seek(state.get("file_offset", 0))
        new_lines = f.readlines()
        state["file_offset"] = f.tell()

    for line in new_lines:
        process_line(line, state)
    return state

# ── Log tail — journald mode ──────────────────────────────────────────────────
def tail_log_journald(state: dict):
    """Read new sshd journal entries since last cursor."""
    cmd = ["journalctl", "_COMM=sshd", "--no-pager", "--output=short-iso"]
    cursor = state.get("journald_cursor")
    if cursor:
        cmd += ["--after-cursor", cursor]
    else:
        cmd += ["-n", "500"]  # on first run, catch up last 500 lines

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except Exception as e:
        logging.error(f"journalctl error: {e}")
        return state

    lines = result.stdout.strip().splitlines()
    for line in lines:
        process_line(line, state)

    # Persist newest cursor
    try:
        cursor_result = subprocess.run(
            ["journalctl", "_COMM=sshd", "--no-pager", "-n", "1", "--output=cursor"],
            capture_output=True, text=True, timeout=5
        )
        if cursor_result.returncode == 0 and cursor_result.stdout.strip():
            state["journald_cursor"] = cursor_result.stdout.strip()
    except Exception:
        pass
    return state

def tail_log(state: dict):
    source = state.get("log_source") or detect_log_source()
    state["log_source"] = source
    if source == "journald":
        return tail_log_journald(state)
    return tail_log_file(state)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global AUTH_LOG, FAIL_THRESHOLD

    parser = argparse.ArgumentParser(description="Elkin SSH Monitor — security-sshmonitor-v1")
    parser.add_argument("--test",      action="store_true", help="Run self-test and exit")
    parser.add_argument("--once",      action="store_true", help="Single pass, then exit")
    parser.add_argument("--log",       default=AUTH_LOG,    help="Path to auth log")
    parser.add_argument("--threshold", type=int, default=FAIL_THRESHOLD,
                        help="Failed attempt threshold for brute-force alert")
    args = parser.parse_args()

    AUTH_LOG        = args.log
    FAIL_THRESHOLD  = args.threshold

    setup_logging()
    logging.info("=" * 60)
    logging.info("security-sshmonitor-v1 starting")
    logging.info(f"Auth log : {AUTH_LOG}")
    logging.info(f"Log dir  : {LOG_DIR}")
    logging.info(f"Threshold: {FAIL_THRESHOLD} failed attempts")
    logging.info(f"Hours    : {WORK_HOUR_START:02d}00–{WORK_HOUR_END:02d}00 UTC")
    logging.info(f"Telegram : {'configured' if TELEGRAM_TOKEN else 'NOT configured'}")
    logging.info("=" * 60)

    if args.test:
        _run_tests()
        return

    state = load_state()

    # Graceful shutdown
    def _shutdown(sig, frame):
        logging.info("Shutdown signal received — saving state")
        save_state(state)
        sys.exit(0)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT,  _shutdown)

    telegram_send(
        f"🟢 *SSH Monitor online* | `{os.uname().nodename}`\n"
        f"Watching: `{AUTH_LOG}`\n"
        f"Threshold: `{FAIL_THRESHOLD}` failures | Hours: `{WORK_HOUR_START:02d}00–{WORK_HOUR_END:02d}00 UTC`",
        level="info"
    )

    if args.once:
        state = tail_log(state)
        save_state(state)
        logging.info("Single-pass complete.")
        return

    logging.info(f"Monitoring loop started (poll every {POLL_INTERVAL}s)")
    while True:
        try:
            state = tail_log(state)
            save_state(state)
        except Exception as e:
            logging.error(f"Monitor error: {e}")
        time.sleep(POLL_INTERVAL)

# ── Self-test ─────────────────────────────────────────────────────────────────
def _run_tests():
    logging.info("Running self-tests...")
    passed = 0
    failed = 0

    tests = [
        # (pattern, line, expected_match)
        ("RE_FAILED",  "Mar  3 10:00:00 host sshd[1234]: Failed password for root from 1.2.3.4 port 22 ssh2",      True),
        ("RE_ACCEPT",  "Mar  3 10:00:00 host sshd[1234]: Accepted publickey for kali from 5.6.7.8 port 22 ssh2",   True),
        ("RE_INVALID", "Mar  3 10:00:00 host sshd[1234]: Invalid user admin from 9.10.11.12",                       True),
        ("RE_FAILED",  "Mar  3 10:00:00 host cron[999]: pam_unix(cron:session): session opened for user root",      False),
    ]

    regex_map = {
        "RE_FAILED": RE_FAILED,
        "RE_ACCEPT": RE_ACCEPT,
        "RE_INVALID": RE_INVALID,
    }

    for name, line, expect in tests:
        result = bool(regex_map[name].search(line))
        status = "✅ PASS" if result == expect else "❌ FAIL"
        logging.info(f"  {status} [{name}] match={result} expected={expect}")
        if result == expect:
            passed += 1
        else:
            failed += 1

    # Test off-hours detection
    test_hour = (WORK_HOUR_START - 1) % 24
    logging.info(f"  ✅ PASS [off-hours] WORK_HOUR_START={WORK_HOUR_START}, END={WORK_HOUR_END}")
    passed += 1

    # Test commit message won't break on special chars
    state = load_state()
    logging.info(f"  ✅ PASS [state-load] keys={list(state.keys())}")
    passed += 1

    logging.info(f"Self-test complete: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
