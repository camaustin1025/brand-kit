#!/usr/bin/env bash
# Install the skill for Claude Code on this machine by symlinking it into ~/.claude/skills.
set -euo pipefail
src="$(cd "$(dirname "$0")/.." && pwd)/brand-pack"
mkdir -p "$HOME/.claude/skills"
ln -sfn "$src" "$HOME/.claude/skills/brand-pack"
echo "linked $HOME/.claude/skills/brand-pack -> $src"
echo "Start a new Claude Code session and type: /brand-pack https://example.com/"
