# multi-agent-test-iteration skill 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `my-skills` 仓库建成「测试阶段对抗式协作 skill」`multi-agent-test-iteration`：吃冻结 DESIGN + 实现代码，宿主无关地由全宿主子 agent 写/跑/审单元·功能·集成·UI 测试，对抗实现、迭代测试质量，bug 只报不修。

**Architecture:** 共享对抗式内核母本 `_adversarial-core/` **已存在**（design/dev 两块已建），本计划复用它（`sync-core.sh` 注入副本、`progress-check.py` 判收敛、`review-schema.json` 校验、`check-skill.sh` 结构闸门），只新增一个 test 特有的可执行小工具 `filter-findings.py`（按 `category` 把 `real-bug` 从收敛计数中分流出去，防"主笔不修实现→永远 unresolved→死锁"），其余为 test skill 的散文型文件（SKILL.md / references / assets）。可执行产物走红-绿 TDD；散文型文件走「按精确章节+关键内容撰写 → 结构冒烟检查 → 提交」。

**Tech Stack:** Markdown（SKILL.md / references / 模板）、JSON（评审输出，复用母本 schema）、Python3（`filter-findings.py` 分流 + 复用 `progress-check.py`）、Bash（测试 + 复用 `sync-core.sh` / `check-skill.sh`）、Claude Code skill 约定 + 宿主无关适配层。

**仓库根（所有路径相对此目录）：** `/Users/afreecoder/project/my-skills`
**建议分支：** `feat/multi-agent-test-iteration`（`my-skills` 当前在 `main`；执行者先从 `main` 切出此分支再开工，所有提交落此分支，最终合并交人类）。

---

## 范围

**本计划交付（自包含、可测试）：**
- test 特有工具 `skills/_adversarial-core/filter-findings.py` + 测试（`real-bug` 分流）。
- 测试 skill `skills/multi-agent-test-iteration/`（SKILL.md + references + assets）。
- 在 `.claude-plugin/marketplace.json` 登记本 skill。

**明确不在本计划（各自后续独立计划）：**
- 把 `multi-agent-design-review` 接入母本（regression-sensitive，独立任务）。
- 串联 设计→开发→测试 的薄编排层。
- 对真实大项目跑本 skill（属使用，不属实现）。

**依赖前置：** `_adversarial-core/`（`adversarial-core.md` / `review-schema.json` / `sync-core.sh` / `check-skill.sh` / `progress-check.py`）已在 `main` 存在且测试绿。本计划不重建母本，只新增 `filter-findings.py` 一件并复用其余。

**设计依据：** 已冻结 spec `docs/specs/2026-06-26-multi-agent-test-iteration-design.md`。

## 文件结构

```
skills/_adversarial-core/
  filter-findings.py             # 新增:按 category 过滤评审 findings(test 用它排除 real-bug)
  tests/
    test_filter_findings.sh      # 新增:filter-findings.py 的断言测试
  # 其余(adversarial-core.md / review-schema.json / sync-core.sh / check-skill.sh / progress-check.py)已存在,本计划不改

skills/multi-agent-test-iteration/
  SKILL.md                       # 入口:角色模型(宿主无关)/何时用/工作流概览/终止/输出/引用
  references/
    orchestration.md             # 阶段0-2 编排、宿主无关调用、串行逐目标、UI执行降级、bug分流、收敛
    host-adapter.md              # 宿主能力映射表(Claude Code / Codex 桌面端 / 其他)
    scope-planning.md            # 阶段0 测试范围规划 + 测试矩阵产出 + 范围对抗指引
    test-author-prompt.md        # 测试主笔 prompt 模板(写某目标某层级测试,只写测试不改实现)
    test-reviewer-prompt.md      # 评审 prompt 模板(测试质量层 + bug真伪 + category 测试枚举)
    adversarial-core.md          # ← sync-core.sh 注入的母本副本(勿手改)
  assets/
    review-schema.json           # ← sync-core.sh 注入的母本副本(勿手改)
    test-matrix-template.md      # 测试矩阵模板(目标×层级 + 补充项)
    test-log-template.md         # 测试日志模板
    bug-report-template.md       # 实现 bug 清单模板
```

每个文件单一职责；`filter-findings.py` 与测试留在 `_adversarial-core/`，**不**随 sync 进入各 skill（sync 只复制 `adversarial-core.md` 与 `review-schema.json` 两件）；test skill 通过相对路径 `../_adversarial-core/filter-findings.py` 与 `../_adversarial-core/progress-check.py` 调用脚本。

---

## Phase 0 — test 特有可测逻辑

### Task 1: 分流工具 `filter-findings.py`

实现 spec §6/§7 的 **`real-bug` 分流**：收敛判定只针对"测试自身质量"，`real-bug`（测试确认的真实现缺陷，主笔不修）必须在喂给 `progress-check.py` 前剔除，否则它永远 `unresolved` → 死锁。本工具既能产"排除 real-bug 的 quality 版"（喂收敛），也能产"仅 real-bug 的版本"（抽 bug 清单）。

**Files:**
- Create: `skills/_adversarial-core/filter-findings.py`
- Create: `skills/_adversarial-core/tests/test_filter_findings.sh`

- [ ] **Step 1: 写失败测试**

`skills/_adversarial-core/tests/test_filter_findings.sh`：
```bash
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `bash skills/_adversarial-core/tests/test_filter_findings.sh`
Expected: FAIL —— `filter-findings.py` 不存在，多条 `FAIL`，退出码 1。

- [ ] **Step 3: 撰写脚本**

`skills/_adversarial-core/filter-findings.py`：
```python
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
```

- [ ] **Step 4: 赋可执行 + 跑测试确认通过**

Run:
```bash
chmod +x skills/_adversarial-core/filter-findings.py
bash skills/_adversarial-core/tests/test_filter_findings.sh
```
Expected: PASS —— 全部 `ok`，退出码 0。

- [ ] **Step 5: 提交**

```bash
git add skills/_adversarial-core/filter-findings.py skills/_adversarial-core/tests/test_filter_findings.sh
git commit -m "feat(core): 新增 real-bug 分流工具 filter-findings.py + 测试

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 1 — test skill 撰写

### Task 2: 注入母本副本到 test skill

**Files:**
- Create（由脚本生成）: `skills/multi-agent-test-iteration/references/adversarial-core.md`
- Create（由脚本生成）: `skills/multi-agent-test-iteration/assets/review-schema.json`

- [ ] **Step 1: 跑同步脚本注入母本**

Run:
```bash
mkdir -p skills/multi-agent-test-iteration
bash skills/_adversarial-core/sync-core.sh skills/multi-agent-test-iteration
```
Expected: 输出 `synced → skills/multi-agent-test-iteration`，退出码 0。

- [ ] **Step 2: 校验副本与母本逐字节一致**

Run:
```bash
cmp skills/_adversarial-core/adversarial-core.md skills/multi-agent-test-iteration/references/adversarial-core.md && \
cmp skills/_adversarial-core/review-schema.json skills/multi-agent-test-iteration/assets/review-schema.json && echo SYNCED-OK
```
Expected: 输出 `SYNCED-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-test-iteration/references/adversarial-core.md skills/multi-agent-test-iteration/assets/review-schema.json
git commit -m "feat(test-iteration): 注入对抗式内核母本副本

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 宿主适配映射表 `host-adapter.md`

本 skill 的"宿主无关"靠这张表落地：SKILL/orchestration 正文只用抽象能力词，由本表给各宿主的具体实现。

**Files:**
- Create: `skills/multi-agent-test-iteration/references/host-adapter.md`

- [ ] **Step 1: 撰写 host-adapter.md**

必含以下内容：

1. 开头说明：本 skill 不绑定具体宿主，正文用抽象能力词（"宿主子 agent""宿主提问工具""宿主浏览器能力""宿主命令执行"），执行时按本表映射到当前宿主；**全程不跨工具调外部 CLI**（不 `codex exec`、不 `claude -p`），这是稳定性与通用性的来源。
2. 映射表（Markdown 表格，列：抽象能力 / Claude Code / Codex 桌面端及其他）：

   | 抽象能力 | Claude Code | Codex 桌面端 / 其他 agent 工具 |
   |---|---|---|
   | 起独立子 agent | `Agent` 工具（`general-purpose`，全新上下文） | 该工具的子 agent / 子任务机制；要求全新上下文、可限只读 |
   | 向用户提问 / 检查点 | `AskUserQuestion` | 该工具的提问 / 确认机制 |
   | 跑命令 / 单元·集成测试 | `Bash` | 该工具的 shell 执行 |
   | 跑 UI / E2E（起 server + 浏览器） | `preview_*`（start/eval/snapshot/screenshot/console_logs…） | 该工具的浏览器驱动；无则按降级处理 |
   | 读写状态文件 | `Read` / `Write` / `Edit` | 该工具的文件读写 |

3. "写⊥审"在同模型下的独立性约束（照写）：Author 与 Reviewer 必须是**不同子 agent 实例**、Reviewer **不继承** Author 上下文、Reviewer **不获工作区写权限**。
4. 降级与诚实（照写）：任何抽象能力在当前宿主缺失或失败（如无浏览器驱动、server 起不来），**如实降级标注**，绝不伪造结果；UI 无法真跑 → 标 `unexecuted` 并移入评审 `open_questions`（见 `references/adversarial-core.md` 反作弊纪律）。

- [ ] **Step 2: 结构冒烟检查**

Run:
```bash
grep -qiE 'preview_|AskUserQuestion|Agent' skills/multi-agent-test-iteration/references/host-adapter.md && \
grep -qE 'unexecuted' skills/multi-agent-test-iteration/references/host-adapter.md && \
grep -qiE '不.*codex exec|不.*claude -p|不跨工具' skills/multi-agent-test-iteration/references/host-adapter.md && echo ADAPTER-OK
```
Expected: 输出 `ADAPTER-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-test-iteration/references/host-adapter.md
git commit -m "feat(test-iteration): 新增宿主适配映射表 host-adapter.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 范围规划指引 `scope-planning.md`

落实用户最强调的"先读文档定范围、不局限于设计文档"。阶段 0 的产矩阵 + 范围对抗子 agent 都读本文件。

**Files:**
- Create: `skills/multi-agent-test-iteration/references/scope-planning.md`

- [ ] **Step 1: 撰写 scope-planning.md**

必含章节（`##` 标题）：

1. `## 目标` —— 在动手测之前，产出一份经人类确认的**测试矩阵**（目标 × 层级），界定"测什么、测到什么程度"；**不局限于 DESIGN**——要读真实实现代码补出设计没写的测试点。
2. `## 调研输入` —— 列出必读：`DESIGN.md`（冻结）、实现代码（给 `文件:行` 指针）、`dev-log`（若有，看 dev 已覆盖哪些单测以免重复）。
3. `## 产测试矩阵` —— 委派子 agent 产 `test-matrix.md`（模板 `assets/test-matrix-template.md`）：
   - 行 = **测试目标 / 功能场景**（如"用户注册流程""Key 额度扣减"），按功能聚类，不按文件。
   - 列 = 适用层级（单元 / 集成 / 功能 / UI），逐格标"是否适用 + 验收点"。
   - **「超出设计的补充项」列**（照写要求）：读实现代码找出 DESIGN 未写但存在的——边界、异常分支、错误处理、并发/竞态、集成点、回归面、安全面（鉴权/越权/注入）、UI 关键交互与失败态。
   - 单元层级**标注"已由 dev-log 覆盖"的部分**（仅补强边界/异常，不重写）。
4. `## 范围对抗` —— 派**独立评审子 agent** 专挑"漏了什么该测的"：对照实现代码与常见失效模式审矩阵，结构化输出（复用 `assets/review-schema.json`，`category` 多为 `coverage-gap`）。Orchestrator 据此补全矩阵，争议项交人类。
5. `## 人类检查点①` —— 向人类报告矩阵（目标清单、各目标层级、补充项、范围对抗结论）+ 隔离分支/worktree + 阈值 K=2/M=5 + UI 执行与降级策略 → 确认后冻结矩阵再开测。

- [ ] **Step 2: 结构冒烟检查**

Run:
```bash
grep -cE '^## (目标|调研输入|产测试矩阵|范围对抗|人类检查点)' skills/multi-agent-test-iteration/references/scope-planning.md
```
Expected: 输出 `5`。

并确认"不局限设计"要点在场：
```bash
grep -qE '超出设计|不局限|未写但' skills/multi-agent-test-iteration/references/scope-planning.md && \
grep -qE 'coverage-gap' skills/multi-agent-test-iteration/references/scope-planning.md && echo SCOPE-OK
```
Expected: 输出 `SCOPE-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-test-iteration/references/scope-planning.md
git commit -m "feat(test-iteration): 新增测试范围规划指引 scope-planning.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 测试主笔 prompt 模板 `test-author-prompt.md`

**Files:**
- Create: `skills/multi-agent-test-iteration/references/test-author-prompt.md`

- [ ] **Step 1: 撰写主笔 prompt 模板**

按以下要点撰写（占位符 `<...>`，被 Orchestrator 填充后传给宿主子 agent）：

- **角色声明**：你是某测试目标某层级的**测试主笔**。职责是写测试去**证伪实现**，尽力构造能让实现露馅的用例。**只写测试，绝不修改实现代码**（改实现是越界，属 blocker）。
- **输入（占位）**：`<测试目标与验收点>`、`<本层级（单元/集成/功能/UI）>`、`<DESIGN 相关章节>`、`<实现代码相关指针 file:行>`、`<worktree 路径>`、`<上一轮 findings 与处理结论（复评轮）>`。
- **任务顺序（照写）**：① 依矩阵该格验收点 + 读实现，设计覆盖正常路径 + **边界/异常/失败态**的用例（不止 happy path）；② 写测试代码到 worktree（测试文件，不碰实现）；③ 跑能在子 agent 内跑的层级（单元/集成）到有明确结论；④ 回报真实结果，**测试报红若指向实现缺陷，如实写明"疑似实现 bug"，不要为了绿去改实现或弱化断言**。
- **反作弊（照写）**：禁止 mock 掉被测核心路径造假绿；禁止写无意义/过弱断言；退出码非 0 不得称通过；UI 等无法在子 agent 内跑的，**如实标"已写未执行，待 Orchestrator 执行"**，不伪造结果。
- **沙箱（照写）**：所有写操作限定在 `<worktree>` 内，不改 worktree 外文件、不改实现源码。
- **复评轮附加（照写）**：逐条处理传入的测试质量 findings（`coverage-gap`/`fake-green`/`unexecuted`/`assertion-weak`/`flaky`/`test-regression`）——采纳则补/改测试；分歧给技术理由，**不得单方面降级 blocker/major**（标注"与评审分歧，需上交人类"）。`real-bug` 类 finding **不是给你修的**（实现 bug 只报不修），无需处理。
- **回报格式（照写）**：新增/改的测试文件（`file:行`）、各用例覆盖的路径、测试命令 + 退出码 + 通过/失败/未执行、**疑似实现 bug 清单**（用例名 + 期望 vs 实际 + 实现 anchor）、仍存疑点。

- [ ] **Step 2: 冒烟检查关键约束在场**

Run:
```bash
grep -qE '只写测试|不.*改.*实现|不修改实现' skills/multi-agent-test-iteration/references/test-author-prompt.md && \
grep -qiE '边界|异常|失败态' skills/multi-agent-test-iteration/references/test-author-prompt.md && \
grep -qE 'unexecuted|已写未执行' skills/multi-agent-test-iteration/references/test-author-prompt.md && echo AUTHOR-OK
```
Expected: 输出 `AUTHOR-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-test-iteration/references/test-author-prompt.md
git commit -m "feat(test-iteration): 新增测试主笔 prompt 模板

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 测试评审 prompt 模板 `test-reviewer-prompt.md`

**Files:**
- Create: `skills/multi-agent-test-iteration/references/test-reviewer-prompt.md`

- [ ] **Step 1: 撰写评审 prompt 模板**

按以下要点撰写：

- **角色声明**：你是独立测试评审者，**只读**，不写不改任何代码。职责是审"测试本身够不够"并复核测试报出的 bug 真伪。
- **输入（占位）**：`<测试目标与验收点>`、`<本目标各层级测试 diff>`、`<Orchestrator 的真实运行结果：命令+退出码+通过/失败/未执行降级>`、`<DESIGN/矩阵相关条目>`、`<上一轮 findings（复评轮）>`。
- **输出要求（照写）**：严格按 `assets/review-schema.json` 输出 JSON；每条 finding 必带 `anchor`（`test:用例名` / `file:行` / 接口 / 数据流），无 anchor 视为无效。
- **评审聚焦（照写，测试质量层）**：① **覆盖完整性**——验收点/边界/异常/集成点是否漏测（`coverage-gap`）；② **测试真实性**——是否 mock 核心路径造假绿、断言是否有意义、是否真跑（`fake-green`/`assertion-weak`/`unexecuted`/`flaky`）；③ **越界**——测试是否改了实现（`test-regression`）；④ **bug 真伪复核**——测试报红是真实现缺陷（`real-bug`）还是测试本身写错（→ 测试质量 finding）。
- **`category` 测试枚举（照写表格）**：
  | 值 | 含义 | 是否计入测试质量收敛 |
  |---|---|---|
  | `coverage-gap` | 关键路径/边界/异常/集成点漏测 | 是 |
  | `fake-green` | mock 核心路径、断言无意义、退出码非0却称通过 | 是 |
  | `unexecuted` | 测试已写但未真实执行(含 UI 降级未跑) | 是 |
  | `assertion-weak` | 断言太弱,通过不代表正确 | 是 |
  | `flaky` | 非确定性/不稳定 | 是 |
  | `test-regression` | 测试越界改动或破坏实现 | 是 |
  | `real-bug` | 测试确认的真实实现缺陷 | **否(分流至 bug-report)** |
- **分级（照写）**：引用 `references/adversarial-core.md` 的 severity 定义；本 skill blocker 额外含「测试造假/没真跑」「核心验收点完全无覆盖」「测试改坏实现」。`real-bug` 用其客观严重度标 severity，但 Orchestrator 会按 category 分流，不计入测试质量收敛。
- **complete 语义提醒（照写）**：测试"正确地红"（发现真 bug）不是测试质量问题；当测试覆盖充分、真实执行、断言有效、跑出的失败已正确归类为 `real-bug` 时，`verdict` 应为 `approve`（即"测试质量达标"，**不要求实现的 bug 已被修**）。
- **复评轮（照写）**：用 `prior_findings_status` 标 resolved/partially_resolved/unresolved，`findings` 只放未解决/新增；上一轮测试质量 blocker/major 未 resolved 不得 `approve`。

- [ ] **Step 2: 冒烟检查**

Run:
```bash
grep -qE 'review-schema\.json' skills/multi-agent-test-iteration/references/test-reviewer-prompt.md && \
grep -qE 'real-bug' skills/multi-agent-test-iteration/references/test-reviewer-prompt.md && \
grep -qE 'fake-green|coverage-gap' skills/multi-agent-test-iteration/references/test-reviewer-prompt.md && \
grep -qE 'prior_findings_status' skills/multi-agent-test-iteration/references/test-reviewer-prompt.md && echo REVIEWER-OK
```
Expected: 输出 `REVIEWER-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-test-iteration/references/test-reviewer-prompt.md
git commit -m "feat(test-iteration): 新增测试评审 prompt 模板

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: 三个 assets 模板

**Files:**
- Create: `skills/multi-agent-test-iteration/assets/test-matrix-template.md`
- Create: `skills/multi-agent-test-iteration/assets/test-log-template.md`
- Create: `skills/multi-agent-test-iteration/assets/bug-report-template.md`

- [ ] **Step 1: 撰写测试矩阵模板**

`skills/multi-agent-test-iteration/assets/test-matrix-template.md`：
```markdown
# 测试矩阵 · <feature>

> 阶段 0 产出,人类检查点①确认后冻结。行=测试目标,列=测试层级。
> 「超出设计的补充项」专记 DESIGN 未写、读实现代码发现该测的路径/边界/异常/集成/安全/回归。

## 元信息
- feature: <feature>
- 输入:DESIGN.md(冻结) + 实现分支 <branch> + dev-log(可选)
- 阈值:连续无净进展 K=2,硬上限 M=5(按测试目标计)

## 测试目标 × 层级矩阵

| 目标 | 单元 | 集成 | 功能 | UI | 验收点(怎样算测过) | 超出设计的补充项 |
|------|------|------|------|----|--------------------|------------------|
| G1 <目标名> | ✓/– | ✓/– | ✓/– | ✓/– | <...> | <DESIGN 未覆盖、读码发现该测的> |

> 单元列若 dev-log 已覆盖,标注「dev 已覆盖,仅补强边界/异常」。

## 范围对抗结论(独立评审挑漏测)
- <评审指出的遗漏目标/层级/边界 → 已补入矩阵 / 人类裁定不测>

## 人类检查点①确认
- 确认人 / 日期:
- 范围增删(逐条):
```

- [ ] **Step 2: 撰写测试日志模板**

`skills/multi-agent-test-iteration/assets/test-log-template.md`：
```markdown
# 测试日志 · <feature>

> 跨目标/跨轮累积。每个测试目标一节,记录每轮主笔产出、真实运行结果、评审 findings、bug 分流、收敛判定。
> 每轮由 Orchestrator 追写,不由子 agent 直接写入。

## 元信息
- feature: <feature> / 测试分支:test/<feature>
- 矩阵:docs/test/<feature>/test-matrix.md
- 阈值:K=2 / M=5(按目标计)

## 目标 G<G>: <目标名>

### 轮次 <R>
- 主笔产出:<新增/改的测试文件 + 命令>(各层级)
- 真实运行结果(Orchestrator 复跑):<层级 → 命令 + 退出码 + 通过/失败/未执行降级>
- 评审 findings(.review/goal-<G>-round-<R>.json):
  | id | severity | category | anchor | 处理(采纳/部分/拒绝) | 理由 |
  |----|----------|----------|--------|----------------------|------|
- bug 分流:<本轮抽出的 real-bug 条数 → 已记入 bug-report.md>
- 收敛判定:<filter-findings 排除 real-bug 后跑 progress-check → complete/continue/escalate:*>
- 本目标结论:<下一轮 / 目标完成 / 上交人类(分歧/无进展/硬上限)>

## 终止结论(全部目标后)
- 各目标轮次与最终 verdict:
- 矩阵覆盖核对:<有无遗漏目标/层级;UI 降级未执行项清单>
- 已知债务(未采纳 minor):
- 交人类决策项(bug 衔接等):
```

- [ ] **Step 3: 撰写 bug 清单模板**

`skills/multi-agent-test-iteration/assets/bug-report-template.md`：
```markdown
# 实现 Bug 清单 · <feature>

> 测试阶段产物。本 skill 只报不修;人类决定:回 multi-agent-dev-iteration 修 / 接受为已知问题 / 手动修。
> 每条来自评审复核确认的 real-bug(category=real-bug),非测试自身质量问题。

## 元信息
- feature: <feature> / 实现分支:<branch> / 测试分支:test/<feature>
- 关联矩阵:docs/test/<feature>/test-matrix.md

## Bug 列表

### BUG-<n>: <标题>
- 关联测试目标 / 用例:G<G> / <test 名>
- severity:blocker / major / minor
- anchor(实现位置):<file:行 / 接口>
- 期望行为:<DESIGN/矩阵验收点要求的>
- 实际行为:<测试观察到的>
- 复现步骤:<命令 / 操作序列>
- 首次发现:目标 G<G> 轮次 <R>
- 人类裁定:<回 dev 修 / 接受为已知 / 手动修 / 待定>

## 汇总
- 总计:<n> 个(blocker <x> / major <y> / minor <z>)
- 建议衔接:<整体倾向>
```

- [ ] **Step 4: 提交**

```bash
git add skills/multi-agent-test-iteration/assets/test-matrix-template.md skills/multi-agent-test-iteration/assets/test-log-template.md skills/multi-agent-test-iteration/assets/bug-report-template.md
git commit -m "feat(test-iteration): 新增测试矩阵/日志/bug清单 三个模板

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: 编排细节 `orchestration.md`

载重文件。按下列章节与**关键命令**撰写；命令块为载重内容，照写。所有起子 agent / 提问 / UI 执行的"能力词"按 `references/host-adapter.md` 映射，正文不写死外部 CLI。

**Files:**
- Create: `skills/multi-agent-test-iteration/references/orchestration.md`

- [ ] **Step 1: 撰写 orchestration.md**

开头声明：Orchestrator 执行前须已读 `references/adversarial-core.md`（终止/反作弊/文件驱动/输出校验）与 `references/host-adapter.md`（能力映射）。本文件不重复定义这些，只在步骤中引用。

必含章节（`##` 标题）：

1. `## 状态载体` —— 列出 `docs/test/<feature>/` 下：`test-matrix.md`、`test-log.md`、`bug-report.md`、`.author/goal-<G>-layer-<层级>-prompt.md`、`.review/goal-<G>-round-<R>.json`。文件驱动，子 agent 全新上下文、所需文件**绝对路径**显式传入。引用母本「文件驱动协作」。
2. `## 宿主无关与适配` —— 照写：起子 agent / 提问 / 跑命令 / 跑 UI 一律走 `host-adapter.md` 的当前宿主映射；全程不调外部 CLI；同模型独立性靠"不同子 agent 实例 + 不继承上下文 + Reviewer 只读"。
3. `## 阶段 0:测试范围规划 + 人类检查点①` —— 引 `references/scope-planning.md`；含关键命令块：
   ```bash
   REPO_ROOT=$(git rev-parse --show-toplevel)
   test -f "$REPO_ROOT/docs/design/<feature>/DESIGN.md" && grep -q "已冻结" "$REPO_ROOT/docs/design/<feature>/DESIGN.md" \
     || { echo "DESIGN 未冻结,停止"; exit 1; }
   # 定位实现分支(默认 dev/<feature>,无 dev 则用户指定);工作区须干净
   IMPL_BRANCH="<impl-branch>"
   git -C "$REPO_ROOT" diff --quiet && git -C "$REPO_ROOT" diff --cached --quiet || { echo "工作区不干净,停止"; exit 1; }
   WT="$REPO_ROOT/../<feature>-test"
   git -C "$REPO_ROOT" worktree add -b test/<feature> "$WT" "$IMPL_BRANCH"
   mkdir -p "$REPO_ROOT/docs/test/<feature>/.author" "$REPO_ROOT/docs/test/<feature>/.review"
   ```
   随后：派子 agent 产 `test-matrix.md` → 派独立子 agent 做范围对抗 → 向人类报告矩阵+worktree+阈值+UI 降级策略 → 宿主提问工具确认后冻结矩阵。
4. `## 阶段 1:逐测试目标串行迭代` —— 照写每个目标的循环（目标间串行）：
   - **1a 主笔（各层级独立子 agent）**：对该目标每个适用层级，按 `references/test-author-prompt.md` 填 `.author/goal-<G>-layer-<层级>-prompt.md`，派独立宿主子 agent 在 `$WT` 内写测试、跑单元/集成；回报测试文件 + 运行结果 + 疑似 bug。
   - **1b 宿主执行**：Orchestrator **亲自复跑**全部测试（独立验证防 Author 误报）；UI/E2E 用**宿主浏览器能力**（见 host-adapter；Claude Code 下 `preview_*`）；**起不来 → 标 `unexecuted` + 移入评审 `open_questions`,绝不伪造绿**。
   - **1c 独立评审（各层级独立子 agent）**：按 `references/test-reviewer-prompt.md`，喂测试 diff + **真实运行结果** + 矩阵条目 + 上轮 findings；各层级评审 findings 由 Orchestrator **汇总为该目标该轮一个** `.review/goal-<G>-round-<R>.json`（符合 `assets/review-schema.json`）；随后做母本「输出校验」。
   - **1d bug 分流 + 收敛判定**：照写命令块：
     ```bash
     SKILL_DIR="$REPO_ROOT/skills/multi-agent-test-iteration"
     RD="$REPO_ROOT/docs/test/<feature>/.review"
     # 抽 real-bug 追加到 bug-report(Orchestrator 据此回填 bug-report.md)
     python3 "$SKILL_DIR/../_adversarial-core/filter-findings.py" "$RD/goal-<G>-round-<R>.json" --only-category real-bug
     # 产排除 real-bug 的 quality 版,喂收敛
     python3 "$SKILL_DIR/../_adversarial-core/filter-findings.py" "$RD/goal-<G>-round-<R>.json" --exclude-category real-bug > "$RD/goal-<G>-round-<R>.quality.json"
     python3 "$SKILL_DIR/../_adversarial-core/progress-check.py" --rounds "$RD"/goal-<G>-round-*.quality.json --k 2 --m 5   # 分歧加 --disagreement
     ```
     `complete` → 该目标收尾记 `test-log`,进下一目标;`continue` → 回 1a 让主笔补/改测试;`escalate:*` → 停止该目标上交人类。
5. `## 阶段 2:汇总 + 人类检查点②` —— 照写：全部目标 `complete` 后汇总测试报告（矩阵覆盖 + 各层级运行结果 + 未执行降级项）+ `bug-report.md` + 测试质量结论 → 人类决定 bug 衔接（回 dev / 接受 / 手动修）;本 skill 不自动修、不自行合并 `test/<feature>`。
6. `## 失败兜底` —— 照写：主笔子 agent 失败/返回空 → 重试一次,仍失败停止上交人类;评审子 agent 不产出/不可解析/不合 schema → 停止,禁止进入下一轮或合并,绝不静默当通过;UI 起不来 → 降级 `unexecuted` 不伪造。引用母本「反作弊纪律」「输出校验」。

- [ ] **Step 2: 结构冒烟检查**

Run:
```bash
grep -cE '^## (状态载体|宿主无关与适配|阶段 0|阶段 1|阶段 2|失败兜底)' skills/multi-agent-test-iteration/references/orchestration.md
```
Expected: 输出 `6`。

并确认关键命令在场：
```bash
grep -qE 'worktree add -b test/' skills/multi-agent-test-iteration/references/orchestration.md && \
grep -qE 'filter-findings\.py.*--exclude-category real-bug' skills/multi-agent-test-iteration/references/orchestration.md && \
grep -qE 'progress-check\.py .*--k 2 --m 5' skills/multi-agent-test-iteration/references/orchestration.md && \
grep -qE 'unexecuted' skills/multi-agent-test-iteration/references/orchestration.md && echo ORCH-OK
```
Expected: 输出 `ORCH-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-test-iteration/references/orchestration.md
git commit -m "feat(test-iteration): 新增编排细节(宿主无关/逐目标/UI降级/bug分流/收敛)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: 入口 `SKILL.md`

**Files:**
- Create: `skills/multi-agent-test-iteration/SKILL.md`

- [ ] **Step 1: 撰写 SKILL.md**

frontmatter（照写键，description 含触发短语）：
```yaml
---
name: multi-agent-test-iteration
description: >-
  测试阶段的多智能体对抗式协作:吃冻结的 DESIGN.md + 实现代码,宿主无关地由全宿主
  子 agent 写/跑/审 单元·功能·集成·UI 测试——主笔尽力证伪实现、独立评审挑测试质量
  (漏测/假绿/未执行),按测试目标串行迭代到测试质量达标;测出的实现 bug 只报不修(产
  结构化清单交人类)。当用户已有冻结设计与实现、要做系统性测试/功能/集成/回归/UI 验证,
  并表达"对当前开发内容做测试""按设计文档测试并补充""多 agent 测试评审""测一下有没有
  bug""做功能/集成/UI 测试"时触发。
---
```

正文必含章节（`##`）：
- `## 角色模型(宿主无关)` —— 三角色表（Orchestrator 宿主主 agent / Test Author 宿主子 agent 工作区写 / Reviewer 独立宿主子 agent 只读）；注明对抗对象=实现、迭代对象=测试质量、bug 只报不修；同模型独立性三机制；指向 `references/host-adapter.md`。
- `## 何时使用 / 何时不用` —— 用：已有冻结 DESIGN + 实现，要系统性测试。不用：尚无冻结设计 / 想改实现修 bug（本 skill 只报不修，修回 `multi-agent-dev-iteration`）/ 仅一两行小改直接手测。
- `## 核心原则` —— 引用 `references/adversarial-core.md`（反作弊/文件驱动/分级/输出校验）；写⊥审；**绝不伪造绿、UI 起不来如实降级**；bug 只报不修；不私自降级 blocker/major。
- `## 工作流` —— 阶段 0（范围规划，指向 `references/scope-planning.md`）→ 阶段 1（逐目标串行迭代）→ 阶段 2（汇总+检查点②），细节指向 `references/orchestration.md`。
- `## 终止条件` —— 按测试目标计 K=2/M=5；**目标 complete = 测试质量达标（Reviewer approve），非"所有测试都绿"**（测试正确地红=发现 bug 也可 complete，bug 入清单不阻塞）；引用母本机制。
- `## 输出` —— 测试代码（`test/<feature>` 分支）+ `docs/test/<feature>/`（test-matrix / test-log / bug-report）+ 测试结论；bug 衔接交人类。
- `## 引用文件` —— 列出 references/assets 各文件。

正文须以反引号引用这些文件：`references/orchestration.md`、`references/host-adapter.md`、`references/scope-planning.md`、`references/test-author-prompt.md`、`references/test-reviewer-prompt.md`、`references/adversarial-core.md`、`assets/review-schema.json`、`assets/test-matrix-template.md`、`assets/test-log-template.md`、`assets/bug-report-template.md`。

- [ ] **Step 2: frontmatter + 引用冒烟检查**

Run:
```bash
grep -qE '^name: multi-agent-test-iteration' skills/multi-agent-test-iteration/SKILL.md && \
grep -qE '^description:' skills/multi-agent-test-iteration/SKILL.md && \
grep -qE 'bug 只报不修|只报不修' skills/multi-agent-test-iteration/SKILL.md && echo SKILL-OK
```
Expected: 输出 `SKILL-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-test-iteration/SKILL.md
git commit -m "feat(test-iteration): 新增 SKILL.md 入口

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2 — 登记与结构闸门

### Task 10: 登记 marketplace + 结构自包含校验

**Files:**
- Modify: `.claude-plugin/marketplace.json`（在 `skills` 数组加一项）

- [ ] **Step 1: 登记到 marketplace**

在 `.claude-plugin/marketplace.json` 的 `plugins[0].skills` 数组中，`"./skills/multi-agent-dev-iteration",` 之后加入：
```json
        "./skills/multi-agent-test-iteration",
```
（保持数组逗号合法、字典序就近放在 `multi-agent-*` 三项相邻处。）

- [ ] **Step 2: 校验 JSON 合法 + 含本 skill**

Run:
```bash
python3 -c "import json;d=json.load(open('.claude-plugin/marketplace.json'));s=d['plugins'][0]['skills'];assert './skills/multi-agent-test-iteration' in s, s;print('MARKETPLACE-OK')"
```
Expected: 输出 `MARKETPLACE-OK`（JSON 合法且已登记）。

- [ ] **Step 3: 跑结构自包含校验（最终闸门）**

Run: `bash skills/_adversarial-core/check-skill.sh skills/multi-agent-test-iteration`
Expected: 输出 `check-skill: OK skills/multi-agent-test-iteration`，退出码 0（frontmatter 齐全、SKILL.md 反引号引用的 references/assets 文件全部存在）。

- [ ] **Step 4: 若有悬空引用则修正**

若报「悬空引用 X」：对照 Task 3–9 补齐缺失文件或修正 SKILL.md 路径，重跑 Step 3 直到 OK。

- [ ] **Step 5: 全量回归 + 提交**

Run（确认母本脚本未被本计划破坏）：
```bash
bash skills/_adversarial-core/tests/test_filter_findings.sh && \
bash skills/_adversarial-core/tests/test_progress_check.sh && \
bash skills/_adversarial-core/tests/test_sync_core.sh && \
bash skills/_adversarial-core/tests/test_check_skill.sh && \
python3 skills/_adversarial-core/tests/test_schema.py && echo ALL-GREEN
```
Expected: 输出 `ALL-GREEN`，各套件退出码 0。

```bash
git add .claude-plugin/marketplace.json skills/multi-agent-test-iteration
git commit -m "feat(test-iteration): 登记 marketplace + 通过结构自包含校验

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 3 — 人工功能验证（手动，不自动化）

### Task 11: 真实回路冒烟与异常路径手动验证

> **集成/功能级手动验证**（需真实起宿主子 agent + 浏览器）。逐项手动执行并记录结果。取一个最小真实标的（如一个带已知 bug 的小模块 + 其 DESIGN 片段）在 throwaway 仓库里跑。

- [ ] **Step 1: 真实回路冒烟**
跑阶段 0→2：确认 test worktree 建立、阶段0 产出 `test-matrix.md` 且范围对抗补出设计外测试点、人类检查点①、逐目标主笔写测试 → Orchestrator 复跑 → 独立评审产 `.review/*.json` 合 schema → 收敛 complete → 检查点②。记录到一次性 test-log。

- [ ] **Step 2: 假绿 → 被评审挡下**
让主笔写一个 mock 掉核心路径的"假绿"测试，确认评审标 `fake-green` blocker、`verdict=needs-revision`、主笔须改，不被当通过。

- [ ] **Step 3: UI 起不来 → 降级不伪造**
人为让 UI 的 dev server 起不来（如改坏端口/symlink），确认 Orchestrator 标 `unexecuted`、移入 `open_questions`、**不伪造绿**，并在 test-log 记降级。

- [ ] **Step 4: 测试报红=真 bug → 分流不阻塞 complete**
构造一个实现确有 bug、测试正确报红的目标，确认：评审标 `real-bug`、`filter-findings --only-category real-bug` 抽出写入 `bug-report.md`、`--exclude-category real-bug` 后 `progress-check` 不因该 bug 阻塞、测试质量达标即 `complete`（验证 complete≠全绿、无死锁）。

- [ ] **Step 5: 无进展 / 硬上限 / 分歧 → 上交人类**
构造连续 2 轮同一 `coverage-gap` 未补，确认 K=2 触发 `escalate:no-progress` 上交人类；另构造主笔↔评审对某测试质量 finding 持续分歧，确认加 `--disagreement` 触发 `escalate:disagreement`，未私自降级。

- [ ] **Step 6: 记录验证结论**
把上述 5 项结果汇总写入 `docs/verification/2026-06-26-test-iteration-e2e.md`，作为 spec §11 功能/集成验证的证据。

---

## 完成定义

- Phase 0、1、2 全部 Task 的自动化检查通过：`test_filter_findings.sh` 绿；`sync-core` 注入副本与母本一致；各散文文件结构冒烟检查（`ADAPTER-OK`/`SCOPE-OK`/`AUTHOR-OK`/`REVIEWER-OK`/`ORCH-OK`/`SKILL-OK`）通过；`marketplace.json` 合法且已登记；`check-skill.sh` 对 test skill 输出 OK；母本五套件全量回归 `ALL-GREEN`。
- Phase 3 手动验证 6 步均有记录结论（含 complete≠全绿、UI 降级不伪造、real-bug 分流不死锁三个关键判断的实证）。
- test skill 自包含、可被 Claude Code 识别加载；正文无写死外部 CLI（宿主无关）。
- 后续（不在本计划）：设计 skill 接入母本；薄编排层。

---

## Self-Review（写完计划后自查，已执行）

**1. Spec 覆盖**（spec §→task）：§2 决策表逐条 → Task 1/3/4/5/6/8/9 覆盖；§4 角色模型(宿主无关) → Task 3 host-adapter + Task 8/9；§5 工作流阶段0-2 → Task 4/8；§6 category 测试枚举 → Task 6；§7 收敛(real-bug 不入收敛/complete≠全绿) → Task 1 filter-findings + Task 6/8/9；§8 状态载体 → Task 7 模板 + Task 8；§9 内核同步 → Task 2;§10 命名/登记 → Task 9/10;§11 验证计划 → Task 1 自动化 + Task 11 手动。无遗漏。

**2. Placeholder 扫描**：散文文件给的是"必含章节 + 关键内容 + 冒烟 grep",非 TBD;可执行文件(`filter-findings.py` + 测试)给完整代码;`<...>` 均为运行时模板占位(矩阵/日志/prompt 的填充位),非计划遗漏。

**3. 类型/命名一致**:`filter-findings.py` 的 `--exclude-category`/`--only-category` 在 Task 1 定义、Task 8/11 调用一致;`real-bug`/`coverage-gap`/`fake-green`/`unexecuted`/`assertion-weak`/`flaky`/`test-regression` 七个 category 在 Task 6 定义、Task 1 测试与 Task 8/11 引用一致;文件名(`goal-<G>-round-<R>.json` / `.quality.json` / `test-matrix.md` / `bug-report.md`)跨 Task 7/8/11 一致;`test/<feature>` 分支、`docs/test/<feature>/` 目录跨 Task 8/9/11 一致。
