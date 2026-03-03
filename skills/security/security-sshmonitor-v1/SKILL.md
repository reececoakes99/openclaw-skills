# Skill: security-sshmonitor-v1

- **Version:** 1
- **Domain:** security
- **Status:** staging
- **Success Rate:** N/A (new)
- **Last Modified:** 2026-03-03
- **Author:** Elkin

---

## Description

Monitors `/var/log/auth.log` for SSH login events in real-time. Sends immediate
Telegram alerts on: new source IP, brute-force threshold exceeded, or login
outside working hours (0600–2200 UTC). Logs all events to the daily-logs memory
directory. On confirmed intrusion, automatically triggers Enhanced Operational
Resilience Mode (EORM) and creates a forensics incident file.

---

## Prerequisites

- Python 3.6+
- Read access to `/var/log/auth.log` (may require `sudo` or `adm` group membership)
- Environment variables sourced from `skills/credentials.env`:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
- `~/.openclaw/workspace/memory/daily-logs/` directory (auto-created)

---

## Tool Chain

```
tail /var/log/auth.log (stateful byte-offset polling, 2s interval)
  │
  ├─ RE_ACCEPT  → SSH_LOGIN_OK
  │     ├─ new IP?          → ⚠️  Telegram alert
  │     ├─ off hours?       → ⚠️  Telegram alert
  │     └─ new IP + off hrs → 🚨 EORM triggered
  │
  ├─ RE_FAILED  → SSH_FAIL (count per IP)
  │     └─ count > threshold (3) → 🚨 Telegram alert + EORM triggered
  │
  └─ RE_INVALID → SSH_INVALID_USER (counted same as failures)

All events → ~/.openclaw/workspace/memory/daily-logs/YYYY-MM-DD-ssh-monitor.log
EORM events → ~/.openclaw/forensics/intrusion_<ts>_<ip>.json
State       → ~/.openclaw/workspace/memory/.sshmonitor_state.json
```

---

## Alert Triggers

| Condition | Severity | EORM |
|-----------|----------|------|
| Login from new IP | ⚠️ Warning | Only if also off-hours |
| Login outside 0600–2200 UTC | ⚠️ Warning | Only if also new IP |
| New IP + off hours combined | 🚨 Critical | ✅ Yes |
| Failed attempts > 3 from same IP | 🚨 Critical | ✅ Yes |

---

## EORM Activation

On confirmed intrusion, the monitor:
1. Sends a 🚨 EORM Telegram alert with full incident details
2. Creates `~/.openclaw/forensics/intrusion_<ts>_<ip>.json`
3. Attempts `openclaw send` self-message to activate EORM in main session
4. Logs incident at CRITICAL level to daily log

---

## Usage

```bash
# Source credentials first
source skills/credentials.env

# Continuous monitoring (default)
python3 monitor.py

# Single pass (for cron)
python3 monitor.py --once

# Custom log path and threshold
python3 monitor.py --log /var/log/auth.log --threshold 5

# Self-test (no external dependencies)
python3 monitor.py --test

# Run as background daemon
nohup python3 monitor.py > /dev/null 2>&1 &
```

**Run as systemd service (recommended):**

```ini
[Unit]
Description=Elkin SSH Monitor
After=network.target

[Service]
Type=simple
User=kali
EnvironmentFile=/home/kali/.openclaw/workspace/skills-repo/skills/credentials.env
ExecStart=/usr/bin/python3 /home/kali/.openclaw/workspace/skills-repo/skills/security/security-sshmonitor-v1/monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Success Indicators

- Process running with exit code 0 between events
- Log file created at `memory/daily-logs/YYYY-MM-DD-ssh-monitor.log`
- State file at `memory/.sshmonitor_state.json` updates after each poll
- Telegram startup message: `🟢 SSH Monitor online`
- Self-test passes all 6 checks

---

## Optimization Notes

- `POLL_INTERVAL` defaults to 2s — lower for faster response, raise for reduced CPU
- State file persists known IPs and fail counts across restarts (no re-alerting on restart)
- Log rotation handled: if file shrinks, offset resets automatically
- `FAIL_THRESHOLD` is inclusive: alert fires when `count == threshold + 1` (once per IP)
- Off-hours window configurable via `WORK_HOUR_START` / `WORK_HOUR_END` env vars

---

## Changelog

- **v1** — Initial release: real-time auth.log tail, new-IP/off-hours/brute-force alerting,
           EORM trigger, daily log writes, stateful offset tracking, self-test mode
