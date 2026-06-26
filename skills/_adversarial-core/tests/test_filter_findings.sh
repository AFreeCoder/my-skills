#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../filter-findings.py"
fail=0
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

# 一轮评审:2 条 real-bug + 1 条 coverage-gap;另有 prior 与 open_questions
cat > "$tmp/r.json" <<'EOF'
{
  "verdict":"needs-revision","summary":"s",
  "findings":[
    {"id":"F1","severity":"major","category":"real-bug","title":"t","detail":"d","anchor":"src/a.ts:1","confidence":0.9,"recommendation":"r"},
    {"id":"F2","severity":"blocker","category":"real-bug","title":"t","detail":"d","anchor":"src/a.ts:2","confidence":0.9,"recommendation":"r"},
    {"id":"F3","severity":"major","category":"coverage-gap","title":"t","detail":"d","anchor":"test:x","confidence":0.9,"recommendation":"r"}
  ],
  "prior_findings_status":[{"id":"P1","status":"resolved","evidence":"e"}],
  "open_questions":["q1"]
}
EOF

count(){ python3 -c "import json;print(len(json.load(open('$1'))['findings']))"; }

# 1) exclude real-bug → findings 只剩 1(coverage-gap)
python3 "$SCRIPT" "$tmp/r.json" --exclude-category real-bug > "$tmp/q.json" 2>/dev/null
n=$(count "$tmp/q.json")
[ "$n" = 1 ] && echo "ok: exclude 留 quality" || { echo "FAIL: exclude n=$n want=1"; fail=1; }

# 2) 非 findings 字段原样保留
pq=$(python3 -c "import json;d=json.load(open('$tmp/q.json'));print(len(d['prior_findings_status']),len(d['open_questions']),d['verdict'])")
[ "$pq" = "1 1 needs-revision" ] && echo "ok: 其余字段保留" || { echo "FAIL: 字段丢失 [$pq]"; fail=1; }

# 3) only real-bug → findings 只剩 2
python3 "$SCRIPT" "$tmp/r.json" --only-category real-bug > "$tmp/b.json" 2>/dev/null
n=$(count "$tmp/b.json")
[ "$n" = 2 ] && echo "ok: only 抽 real-bug" || { echo "FAIL: only n=$n want=2"; fail=1; }

# 4) 两个互斥参数同给 → 非零退出
python3 "$SCRIPT" "$tmp/r.json" --exclude-category real-bug --only-category real-bug >/dev/null 2>&1
[ $? -ne 0 ] && echo "ok: 互斥报错" || { echo "FAIL: 互斥未报错"; fail=1; }

# 5) 都不给 → 非零退出
python3 "$SCRIPT" "$tmp/r.json" >/dev/null 2>&1
[ $? -ne 0 ] && echo "ok: 缺参数报错" || { echo "FAIL: 缺参数未报错"; fail=1; }

exit $((fail>0?1:0))
