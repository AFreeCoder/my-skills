#!/usr/bin/env bash
# 校验一个 skill 目录的结构自包含性。
# 用法: check-skill.sh <skill-dir>
set -uo pipefail

die() { echo "check-skill: $*" >&2; exit 1; }
[ "$#" -eq 1 ] || die "用法: check-skill.sh <skill-dir>"
skill="$1"
md="$skill/SKILL.md"
[ -f "$md" ] || die "缺 SKILL.md: $md"

# frontmatter:取首个 --- 到第二个 --- 之间
fm="$(awk 'NR==1&&$0=="---"{f=1;next} f&&$0=="---"{exit} f{print}' "$md")"
echo "$fm" | grep -qE '^name:[[:space:]]*\S'        || die "frontmatter 缺 name"
echo "$fm" | grep -qE '^description:[[:space:]]*\S'  || die "frontmatter 缺 description"

# 反引号内的 references/* 与 assets/* 路径都要存在
rc=0
refs="$(grep -oE '`(references|assets)/[A-Za-z0-9._/-]+`' "$md" | tr -d '`' | sort -u)"
for p in $refs; do
  if [ ! -e "$skill/$p" ]; then echo "check-skill: 悬空引用 $p" >&2; rc=1; fi
done
[ "$rc" -eq 0 ] || exit 1
echo "check-skill: OK $skill"
