#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../progress-check.py"
fail=0
expect() { local desc="$1" want="$2"; shift 2; local got; got="$("$@" 2>/dev/null)"
  if [ "$got" = "$want" ]; then echo "ok: $desc"; else echo "FAIL: $desc (got=$got want=$want)"; fail=1; fi; }

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
# mkround <file> <n_blocker> <prior_resolved:0/1> <prior_unresolved:0/1>
mkround() {
  local f="$1" nb="$2" pr="$3" pu="$4" finds="" priors=""
  [ "$nb" -gt 0 ] && for i in $(seq 1 "$nb"); do finds+="{\"id\":\"F$i\",\"severity\":\"blocker\",\"category\":\"correctness\",\"title\":\"t\",\"detail\":\"d\",\"anchor\":\"a:1\",\"confidence\":0.9,\"recommendation\":\"r\"},"; done
  finds="[${finds%,}]"
  [ "$pr" = 1 ] && priors+="{\"id\":\"P1\",\"status\":\"resolved\",\"evidence\":\"e\"},"
  [ "$pu" = 1 ] && priors+="{\"id\":\"P2\",\"status\":\"unresolved\",\"evidence\":\"e\"},"
  priors="[${priors%,}]"
  printf '{"verdict":"needs-revision","summary":"s","findings":%s,"prior_findings_status":%s,"open_questions":[]}' "$finds" "$priors" > "$f"
}

mkround "$tmp/c1" 1 0 0; mkround "$tmp/c2" 0 1 0
expect "complete(无 blocker 无未解决 prior)" "complete" python3 "$SCRIPT" --rounds "$tmp/c1" "$tmp/c2"

mkround "$tmp/k1" 2 0 0; mkround "$tmp/k2" 1 0 0
expect "continue(有进展未完成)" "continue" python3 "$SCRIPT" --rounds "$tmp/k1" "$tmp/k2"

mkround "$tmp/n1" 1 0 0; mkround "$tmp/n2" 1 0 0; mkround "$tmp/n3" 1 0 0
expect "no-progress(连续2轮无进展)" "escalate:no-progress" python3 "$SCRIPT" --rounds "$tmp/n1" "$tmp/n2" "$tmp/n3"

for i in 1 2 3 4 5; do mkround "$tmp/h$i" 1 1 0; done
expect "hard-cap(每轮有进展到M=5)" "escalate:hard-cap" python3 "$SCRIPT" --rounds "$tmp/h1" "$tmp/h2" "$tmp/h3" "$tmp/h4" "$tmp/h5"

mkround "$tmp/d1" 1 0 0
expect "disagreement" "escalate:disagreement" python3 "$SCRIPT" --rounds "$tmp/d1" --disagreement

exit $((fail>0?1:0))
