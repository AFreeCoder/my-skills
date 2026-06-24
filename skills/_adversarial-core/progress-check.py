#!/usr/bin/env python3
"""收敛判定:依据各轮评审 JSON,判 continue / complete / escalate。
用法: progress-check.py --rounds r1.json [r2.json ...] [--k 2] [--m 5] [--disagreement]
输出(stdout 一行): complete | continue | escalate:no-progress | escalate:hard-cap | escalate:disagreement
判据(spec §7):
  - outstanding(R) = 本轮 findings 中 severity 为 blocker/major 的条数
  - complete: outstanding==0 且无 prior 处于 unresolved/partially_resolved
  - 净进展(R>=2): outstanding(R) < outstanding(R-1) 或 本轮有 prior 被标 resolved;首轮恒为基线
  - 连续 k 轮无净进展 → escalate:no-progress;R 达硬上限 m → escalate:hard-cap;分歧由外部 --disagreement 传入
判定优先级: complete > disagreement > hard-cap > no-progress > continue
"""
import argparse, json

def bm_count(rnd):
    return sum(1 for f in rnd.get("findings", []) if f.get("severity") in ("blocker", "major"))

def has_unresolved_prior(rnd):
    return any(p.get("status") in ("unresolved", "partially_resolved")
               for p in rnd.get("prior_findings_status", []))

def resolved_any_prior(rnd):
    return any(p.get("status") == "resolved" for p in rnd.get("prior_findings_status", []))

def net_progress(cur, prev):
    if prev is None:
        return True
    return bm_count(cur) < bm_count(prev) or resolved_any_prior(cur)

def decide(rounds, k, m, disagreement):
    R = len(rounds)
    last = rounds[-1]
    if bm_count(last) == 0 and not has_unresolved_prior(last):
        return "complete"
    if disagreement:
        return "escalate:disagreement"
    if R >= m:
        return "escalate:hard-cap"
    if R >= k:
        flags = [net_progress(rounds[i], rounds[i - 1] if i > 0 else None) for i in range(R)]
        if not any(flags[R - k:]):
            return "escalate:no-progress"
    return "continue"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", nargs="+", required=True)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--m", type=int, default=5)
    ap.add_argument("--disagreement", action="store_true")
    a = ap.parse_args()
    rounds = [json.load(open(p)) for p in a.rounds]
    print(decide(rounds, a.k, a.m, a.disagreement))

if __name__ == "__main__":
    main()
