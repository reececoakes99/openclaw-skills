#!/bin/bash
set -e

# Set git identity
git config --global user.name "reececoakes99"
git config --global user.email "reececoakes99@users.noreply.github.com"

echo "=== Creating repos ==="
gh repo create reececoakes99/openclaw-skills --public --description "OpenClaw workspace - skills, configs, and memory" 2>&1 || echo "openclaw-skills: may already exist"
gh repo create reececoakes99/openclaw-brain --public --description "OpenClaw brain - workspace and agent files" 2>&1 || echo "openclaw-brain: may already exist"

echo "=== Setting up git for openclaw-skills ==="
cd /root/.openclaw/workspace
git init
git remote add origin https://github.com/reececoakes99/openclaw-skills.git 2>/dev/null || git remote set-url origin https://github.com/reececoakes99/openclaw-skills.git
git add -A
git commit -m "Initial commit - workspace files" || echo "Nothing to commit"
git branch -M main
git push -u origin main

echo "=== Done! ==="
