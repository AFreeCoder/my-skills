#!/usr/bin/env bash
# 把对抗式内核母本同步进各 skill。母本是唯一权威来源,各 skill 持只读副本。
# 用法: sync-core.sh <skill-dir> [<skill-dir> ...]
set -euo pipefail

CORE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MASTER_MD="$CORE_DIR/adversarial-core.md"
MASTER_SCHEMA="$CORE_DIR/review-schema.json"

die() { echo "sync-core: $*" >&2; exit 1; }

[ -f "$MASTER_MD" ]     || die "母本缺失: $MASTER_MD"
[ -f "$MASTER_SCHEMA" ] || die "母本缺失: $MASTER_SCHEMA"
[ "$#" -ge 1 ]          || die "用法: sync-core.sh <skill-dir> [<skill-dir> ...]"

for skill in "$@"; do
  [ -d "$skill" ] || die "skill 目录不存在: $skill"
  mkdir -p "$skill/references" "$skill/assets"
  cp "$MASTER_MD"     "$skill/references/adversarial-core.md"
  cp "$MASTER_SCHEMA" "$skill/assets/review-schema.json"
  echo "synced → $skill"
done
