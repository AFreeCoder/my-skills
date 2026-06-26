#!/usr/bin/env python3
"""按 category 过滤评审 JSON 的 findings。仅过滤 findings,其余字段原样输出。
用法:
  filter-findings.py <review.json> --exclude-category <cat> [<cat> ...]
  filter-findings.py <review.json> --only-category <cat> [<cat> ...]
输出(stdout): 过滤后的完整评审 JSON。--exclude-category 与 --only-category 互斥,必须二选一。
test skill 用法:
  --exclude-category real-bug  → 产收敛用的 quality 版(喂 progress-check.py)
  --only-category   real-bug  → 抽 real-bug(写入 bug-report.md)
"""
import argparse, json, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("review")
    ap.add_argument("--exclude-category", nargs="+")
    ap.add_argument("--only-category", nargs="+")
    a = ap.parse_args()
    if bool(a.exclude_category) == bool(a.only_category):
        print("filter-findings: 必须且只能给 --exclude-category 或 --only-category 之一", file=sys.stderr)
        sys.exit(2)
    try:
        with open(a.review) as fh:
            doc = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"filter-findings: 无法读取/解析 {a.review}: {e}", file=sys.stderr)
        sys.exit(2)
    findings = doc.get("findings", [])
    if a.exclude_category:
        cats = set(a.exclude_category)
        doc["findings"] = [f for f in findings if f.get("category") not in cats]
    else:
        cats = set(a.only_category)
        doc["findings"] = [f for f in findings if f.get("category") in cats]
    print(json.dumps(doc, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
