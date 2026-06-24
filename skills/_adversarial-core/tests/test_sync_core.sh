#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$(cd "$HERE/.." && pwd)"
SCRIPT="$CORE_DIR/sync-core.sh"
fail=0
check() { # check <desc> <expected-rc> <cmd...>
  local desc="$1" want="$2"; shift 2
  "$@" >/dev/null 2>&1; local rc=$?
  if [ "$rc" -eq "$want" ]; then echo "ok: $desc"; else echo "FAIL: $desc (rc=$rc want=$want)"; fail=1; fi
}

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/myskill"

# 1) 无参数 → 非零
check "无参数应报错" 1 bash "$SCRIPT"

# 2) 目标目录不存在 → 非零
check "目标缺失应报错" 1 bash "$SCRIPT" "$tmp/nope"

# 3) 正常同步 → 退出码 0
check "正常同步退出码0" 0 bash "$SCRIPT" "$tmp/myskill"

# 4) 两件产物均落地且与母本逐字节相同
if cmp -s "$CORE_DIR/adversarial-core.md" "$tmp/myskill/references/adversarial-core.md" \
   && cmp -s "$CORE_DIR/review-schema.json" "$tmp/myskill/assets/review-schema.json"; then
  echo "ok: 副本与母本一致"; else echo "FAIL: 副本与母本不一致"; fail=1; fi

# 5) 幂等:再跑一次仍 0 且文件不变
md5_before="$(cat "$tmp/myskill/references/adversarial-core.md" | wc -c)"
check "幂等再同步退出码0" 0 bash "$SCRIPT" "$tmp/myskill"
md5_after="$(cat "$tmp/myskill/references/adversarial-core.md" | wc -c)"
if [ "$md5_before" = "$md5_after" ]; then echo "ok: 幂等"; else echo "FAIL: 非幂等"; fail=1; fi

exit $((fail>0?1:0))
