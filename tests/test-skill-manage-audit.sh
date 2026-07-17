#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -P "$SCRIPT_DIR/.." && pwd)
AUDIT_SCRIPT=$REPO_DIR/skills/skill-manage/scripts/audit_inventory.py
TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/skill-manage-audit-test.XXXXXX")

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  printf '失败：%s\n' "$*" >&2
  exit 1
}

fixture=$TMP_DIR/repo
mkdir -p "$fixture/skills/demo-skill" "$fixture/.claude-plugin" "$fixture/external"

printf '%s\n' \
  '---' \
  'name: demo-skill' \
  'description: 用于审计测试。' \
  '---' \
  '' \
  '# Demo Skill' \
  > "$fixture/skills/demo-skill/SKILL.md"

printf '%s\n' \
  '# My Skills' \
  '' \
  '当前共收录 `1` 个自建 Skill。' \
  '' \
  '| Skill | 说明 |' \
  '| --- | --- |' \
  '| `demo-skill` | 审计测试。 |' \
  > "$fixture/README.md"

printf '%s\n' \
  '{"plugins":[{"skills":["./skills/demo-skill"]}]}' \
  > "$fixture/.claude-plugin/marketplace.json"

printf '%s\n' '{"third_party":[]}' > "$fixture/external/skills.json"

python3 "$AUDIT_SCRIPT" --repo "$fixture" >/dev/null

printf '%s\n' \
  '{"third_party":[{"name":"demo-skill","source":"owner/repo","scope":"project","description":"冲突测试"}]}' \
  > "$fixture/external/skills.json"
if python3 "$AUDIT_SCRIPT" --repo "$fixture" >"$TMP_DIR/collision.out" 2>&1; then
  fail '应拒绝第三方别名与自建 Skill 重名'
fi
grep -F '第三方 Skill 别名与自建 Skill 重名：demo-skill' "$TMP_DIR/collision.out" >/dev/null || \
  fail '未报告第三方别名冲突'

printf '%s\n' '{"third_party":[]}' > "$fixture/external/skills.json"
printf '%s\n' \
  '{"plugins":[{"skills":["./skills/demo-skill","./skills/demo-skill"]}]}' \
  > "$fixture/.claude-plugin/marketplace.json"
if python3 "$AUDIT_SCRIPT" --repo "$fixture" >"$TMP_DIR/duplicate.out" 2>&1; then
  fail '应拒绝 marketplace 重复注册'
fi
grep -F 'marketplace Skill 重复注册：demo-skill' "$TMP_DIR/duplicate.out" >/dev/null || \
  fail '未报告 marketplace 重复注册'

printf 'skill-manage 清单审计测试通过。\n'
