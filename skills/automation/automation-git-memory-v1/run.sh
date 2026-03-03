#!/usr/bin/env bash
# =============================================================================
# automation-git-memory-v1 — Elkin autonomous git brain operations
# =============================================================================
# Usage: ./run.sh [--repo <path>] [--message <override>] [--dry-run] [--pull-only]
#
# Modes:
#   default    : full cycle — pull → stage → commit → push → report
#   --pull-only: git pull only (startup sync)
#   --dry-run  : simulate without writing to remote
# =============================================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
REPO="${REPO_PATH:-$HOME/.openclaw/workspace}"
BACKUP_DIR="$HOME/.openclaw/backup"
MAX_RETRIES=3
RETRY_INTERVAL=900   # 15 minutes in seconds
TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
DRY_RUN=false
PULL_ONLY=false
COMMIT_MSG_OVERRIDE=""

# ── Colour output ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[GIT-MEMORY]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Arg parsing ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)      REPO="$2";               shift 2 ;;
    --message)   COMMIT_MSG_OVERRIDE="$2"; shift 2 ;;
    --dry-run)   DRY_RUN=true;            shift   ;;
    --pull-only) PULL_ONLY=true;          shift   ;;
    *) err "Unknown argument: $1"; exit 1 ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
telegram_send() {
  local msg="$1"
  if [[ -z "$TELEGRAM_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]]; then
    warn "Telegram not configured — skipping notification"
    return 0
  fi
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" \
    -d parse_mode="Markdown" \
    -d text="$msg" > /dev/null 2>&1 || warn "Telegram delivery failed"
}

backup_workspace() {
  local ts; ts=$(date +%Y%m%d_%H%M%S)
  local backup_path="$BACKUP_DIR/brain_backup_$ts"
  mkdir -p "$backup_path"
  log "Saving backup → $backup_path"
  rsync -a --exclude='.git' "$REPO/" "$backup_path/" 2>/dev/null || \
    tar -czf "${backup_path}.tar.gz" -C "$REPO" . 2>/dev/null
  log "Backup saved: $backup_path"
}

generate_commit_message() {
  if [[ -n "$COMMIT_MSG_OVERRIDE" ]]; then
    echo "$COMMIT_MSG_OVERRIDE"
    return
  fi

  local date_str; date_str=$(date +%Y-%m-%d)
  local changed_files; changed_files=$(git -C "$REPO" diff --cached --name-only 2>/dev/null || true)
  local file_count;    file_count=$(echo "$changed_files" | grep -c . || true)

  # Categorise changes
  local has_memory=false has_skills=false has_soul=false has_goals=false has_logs=false has_config=false

  echo "$changed_files" | grep -q "^memory/"      && has_memory=true
  echo "$changed_files" | grep -q "^skills"        && has_skills=true
  echo "$changed_files" | grep -q "SOUL.md"        && has_soul=true
  echo "$changed_files" | grep -q "memory/goals"   && has_goals=true
  echo "$changed_files" | grep -q "memory/.*log"   && has_logs=true
  echo "$changed_files" | grep -qE "\.(json|yaml|yml|conf|toml)$" && has_config=true

  # Build tag list
  local tags=()
  $has_soul    && tags+=("soul")
  $has_skills  && tags+=("skills")
  $has_goals   && tags+=("goals")
  $has_logs    && tags+=("logs")
  $has_memory  && ! $has_goals && ! $has_logs && tags+=("memory")
  $has_config  && tags+=("config")
  [[ ${#tags[@]} -eq 0 ]] && tags+=("misc")

  local tag_str; tag_str=$(IFS=","; echo "${tags[*]}")

  # Build summary of changed areas
  local summary=""
  $has_soul   && summary+="SOUL updated; "
  $has_goals  && summary+="goals updated; "
  $has_skills && summary+="skills modified; "
  $has_logs   && summary+="daily logs written; "
  $has_memory && summary+="memory updated; "
  $has_config && summary+="config changes; "
  summary="${summary%; }"
  [[ -z "$summary" ]] && summary="$file_count file(s) modified"

  # Compose final message (max 120 chars on summary line)
  local msg="memory: ${date_str}: [${tag_str}] ${summary} (${file_count} files)"
  # Truncate to 120 chars
  if [[ ${#msg} -gt 120 ]]; then
    msg="${msg:0:117}..."
  fi
  echo "$msg"
}

# ── Phase 1: Pull ──────────────────────────────────────────────────────────────
phase_pull() {
  log "Phase 1 — git pull origin main"
  if $DRY_RUN; then
    log "[dry-run] would pull $REPO"
    return 0
  fi
  local output
  output=$(git -C "$REPO" pull origin main 2>&1) || {
    warn "Pull failed: $output"
    telegram_send "⚠️ *git pull failed* on \`$(hostname)\`\n\`\`\`\n${output:0:300}\n\`\`\`"
    return 1
  }
  log "Pull: $output"
}

# ── Phase 2: Stage ─────────────────────────────────────────────────────────────
phase_stage() {
  log "Phase 2 — staging all changes"
  if $DRY_RUN; then
    log "[dry-run] would: git add -A in $REPO"
    return 0
  fi
  git -C "$REPO" add -A
  local staged; staged=$(git -C "$REPO" diff --cached --name-only | wc -l)
  if [[ "$staged" -eq 0 ]]; then
    log "Nothing to commit — workspace is clean."
    exit 0
  fi
  log "Staged $staged file(s)"
}

# ── Phase 3: Commit ────────────────────────────────────────────────────────────
phase_commit() {
  log "Phase 3 — generating commit message"
  local msg; msg=$(generate_commit_message)
  log "Commit message: $msg"
  if $DRY_RUN; then
    log "[dry-run] would commit: $msg"
    return 0
  fi
  git -C "$REPO" commit -m "$msg"
}

# ── Phase 4+5: Push with retry ─────────────────────────────────────────────────
phase_push() {
  log "Phase 4 — push to origin main"

  if $DRY_RUN; then
    log "[dry-run] would push to origin main"
    return 0
  fi

  local attempt=0
  while [[ $attempt -lt $MAX_RETRIES ]]; do
    attempt=$((attempt + 1))
    log "Push attempt $attempt/$MAX_RETRIES..."

    if git -C "$REPO" push origin main 2>&1; then
      log "✅ Push successful on attempt $attempt"
      return 0
    fi

    warn "Push failed (attempt $attempt/$MAX_RETRIES)"

    if [[ $attempt -lt $MAX_RETRIES ]]; then
      # Save backup before waiting
      backup_workspace
      local wait_min=$((RETRY_INTERVAL / 60))
      warn "Retrying in ${wait_min} minutes..."
      telegram_send "⚠️ *git push failed* (attempt ${attempt}/${MAX_RETRIES}) on \`$(hostname)\`\nBackup saved. Retrying in ${wait_min}m."
      sleep $RETRY_INTERVAL
    fi
  done

  # All retries exhausted
  backup_workspace
  err "All $MAX_RETRIES push attempts failed. Brain saved to $BACKUP_DIR"
  telegram_send "🚨 *git push FAILED* after ${MAX_RETRIES} attempts on \`$(hostname)\`\nBrain backed up to \`$BACKUP_DIR\`\nManual intervention required."
  return 1
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
  log "=== automation-git-memory-v1 | $(date -u '+%Y-%m-%d %H:%M UTC') ==="
  log "Repo: $REPO | dry-run: $DRY_RUN | pull-only: $PULL_ONLY"

  if ! git -C "$REPO" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    err "$REPO is not a git repository"
    exit 1
  fi

  phase_pull || { err "Pull phase failed — aborting"; exit 1; }

  if $PULL_ONLY; then
    log "Pull-only mode — done."
    exit 0
  fi

  phase_stage
  phase_commit
  phase_push

  local short_hash; short_hash=$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo "unknown")
  local msg; msg=$(git -C "$REPO" log -1 --format="%s" 2>/dev/null || echo "")

  telegram_send "✅ *Brain synced* | \`$(hostname)\`\nCommit: \`${short_hash}\`\n\`${msg}\`"
  log "=== Complete. Commit: $short_hash ==="
}

main "$@"
