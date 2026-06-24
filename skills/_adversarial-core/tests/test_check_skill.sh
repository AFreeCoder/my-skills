#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$(cd "$HERE/.." && pwd)"
SCRIPT="$CORE_DIR/check-skill.sh"
fail=0
check() { local desc="$1" want="$2"; shift 2; "$@" >/dev/null 2>&1; local rc=$?
  if [ "$rc" -eq "$want" ]; then echo "ok: $desc"; else echo "FAIL: $desc (rc=$rc want=$want)"; fail=1; fi; }

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

# A) 合规 skill:有 frontmatter + 引用的文件都在 → 0
good="$tmp/good"; mkdir -p "$good/references"
printf -- '---\nname: x\ndescription: y\n---\n见 `references/a.md`\n' > "$good/SKILL.md"
echo "hi" > "$good/references/a.md"
check "合规 skill 通过" 0 bash "$SCRIPT" "$good"

# B) 缺 description → 非零
bad1="$tmp/bad1"; mkdir -p "$bad1"
printf -- '---\nname: x\n---\nbody\n' > "$bad1/SKILL.md"
check "缺 description 报错" 1 bash "$SCRIPT" "$bad1"

# C) 引用的文件不存在 → 非零
bad2="$tmp/bad2"; mkdir -p "$bad2"
printf -- '---\nname: x\ndescription: y\n---\n见 `references/missing.md`\n' > "$bad2/SKILL.md"
check "悬空引用报错" 1 bash "$SCRIPT" "$bad2"

# D) 无 SKILL.md → 非零
check "缺 SKILL.md 报错" 1 bash "$SCRIPT" "$tmp"

exit $((fail>0?1:0))
