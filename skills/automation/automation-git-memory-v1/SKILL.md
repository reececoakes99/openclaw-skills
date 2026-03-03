# Skill: automation-git-memory-v1

- **Version:** 1
- **Domain:** automation
- **Status:** staging
- **Success Rate:** N/A (new)
- **Last Modified:** 2026-03-03
- **Author:** Elkin

---

## Description

Handles all autonomous git operations for the Elkin brain workspace. Provides a
full commit lifecycle: pull → stage → structured commit → push, with automatic
backup and Telegram reporting on failure. Designed to be called at session end,
from cron, or inline whenever the brain needs to be persisted.

---

## Prerequisites

- `git` installed and configured (`user.name`, `user.email`)
- Remote `origin` pointing to `openclaw-brain` repo with push access
- `rsync` or `tar` available (for backup fallback)
- `curl` available (for Telegram notifications)
- Environment variables (optional but recommended):
  - `TELEGRAM_BOT_TOKEN` — bot token for push/fail notifications
  - `TELEGRAM_CHAT_ID`   — operator chat ID
  - `REPO_PATH`          — override default repo path (`~/.openclaw/workspace`)

---

## Tool Chain

```
1. git pull origin main          → sync latest brain state from remote
2. git add -A                    → stage all changes (new, modified, deleted)
3. generate_commit_message()     → analyse staged files, build structured 120-char summary
4. git commit -m "<message>"     → commit with generated or overridden message
5. git push origin main          → attempt push (up to 3 retries, 15 min apart)
   └─ on failure:
       a. rsync/tar backup → ~/.openclaw/backup/brain_backup_<timestamp>/
       b. telegram alert sent
       c. retry after 900s
       d. after 3 failures → 🚨 escalate to Telegram, abort
6. Telegram success notification → commit hash + summary line
```

---

## Commit Message Format

Auto-generated messages follow this structure:

```
memory: YYYY-MM-DD: [tag1,tag2] <summary of changes> (N files)
```

**Tags** (auto-detected from changed file paths):

| Tag | Trigger |
|-----|---------|
| `soul` | `SOUL.md` modified |
| `goals` | `memory/goals*` modified |
| `skills` | `skills/` tree modified |
| `logs` | `memory/*log*` modified |
| `memory` | any `memory/` file (catch-all) |
| `config` | `.json`, `.yaml`, `.toml`, `.conf` modified |
| `misc` | none of the above |

Maximum 120 characters on the summary line — truncated with `...` if exceeded.

---

## Usage

```bash
# Full cycle (default — pull, stage, commit, push, report)
./run.sh

# Override repo path
./run.sh --repo /path/to/other/repo

# Override commit message
./run.sh --message "manual: 2026-03-03: specific override message"

# Pull only (startup sync — no commit/push)
./run.sh --pull-only

# Dry run (simulate all steps, no writes to remote)
./run.sh --dry-run
```

**Environment variable invocation:**

```bash
TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=yyy REPO_PATH=~/.openclaw/workspace ./run.sh
```

---

## Success Indicators

- Exit code `0`
- Log line: `✅ Push successful on attempt N`
- Telegram message: `✅ Brain synced | <hostname> | Commit: <hash>`
- `git log -1` on the repo shows the new commit

---

## Failure Handling

| Scenario | Response |
|----------|---------|
| `git pull` fails | Abort, Telegram alert, exit 1 |
| Nothing to commit | Clean exit 0 with log message |
| Push fails (1st attempt) | Backup + Telegram warning + retry in 15m |
| Push fails (2nd attempt) | Backup + Telegram warning + retry in 15m |
| Push fails (3rd attempt) | Backup + 🚨 Telegram escalation + exit 1 |

---

## Optimization Notes

- Set `RETRY_INTERVAL=60` for testing (override in env)
- For cron use, wrap in: `TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... /path/to/run.sh`
- Pull-only mode is intended for the Startup Protocol step 1
- Can be chained with `openclaw doctor` in End of Session Protocol

---

## Changelog

- **v1** — Initial release: full pull→stage→commit→push cycle, backup on failure,
           Telegram reporting, structured commit message generation, dry-run + pull-only modes
