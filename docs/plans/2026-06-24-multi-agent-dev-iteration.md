# multi-agent-dev-iteration skill 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `my-skills` 仓库建成「开发阶段对抗式协作 skill」`multi-agent-dev-iteration`,以及它依赖的共享对抗式内核母本与同步机制。

**Architecture:** 先建共享内核母本(`_adversarial-core/`:通用规则 `adversarial-core.md` + 通用评审 `review-schema.json` + 同步脚本 `sync-core.sh` + 结构校验 `check-skill.sh`),再用同步脚本把母本注入 dev skill,最后撰写 dev skill 的 `SKILL.md` 与 references/assets。可执行产物(脚本/schema)走红-绿 TDD;散文型 skill 文件走「按精确结构+关键内容撰写 → 结构校验 → 提交」。

**Tech Stack:** Markdown(SKILL.md / references)、JSON Schema(draft 2020-12)、Bash(sync 与 check 脚本)、`python3` + 可选 `jsonschema`(schema 校验,带关键字段冒烟回退)、Claude Code skill 约定。

**仓库根(所有路径相对此目录):** `/Users/afreecoder/project/my-skills`
**当前分支:** `spec/multi-agent-dev-iteration`(本计划在此分支或其后续分支执行)

---

## 范围

**本计划交付(自包含、可测试):**
- 共享内核母本 `skills/_adversarial-core/`(规则 + schema + sync + check + 各自测试)
- 开发 skill `skills/multi-agent-dev-iteration/`(SKILL.md + references + assets)

**明确不在本计划(各自后续独立计划):**
- 把现有 `multi-agent-design-review` 迁入 `my-skills` 并改为消费母本(regression-sensitive,单独计划)
- 测试 skill `multi-agent-test-iteration`
- 串联三者的薄编排层

母本内容**全新撰写**(依据已冻结 spec 与设计 skill 的既有模式),不依赖设计 skill 先迁入。

## 文件结构

```
skills/_adversarial-core/
  adversarial-core.md        # 母本:通用规则(分级/终止/看门狗/反作弊/文件驱动/输出校验)
  review-schema.json         # 母本:通用结构化评审 schema(category 为自由字符串,跨 skill 共用)
  sync-core.sh               # 把母本两件产物复制进目标 skill 的 references/ 与 assets/
  check-skill.sh             # 结构校验:frontmatter 有 name/description,SKILL.md 引用的文件都存在
  progress-check.py          # 收敛判定:依据各轮评审 JSON 判 continue/complete/escalate
  tests/
    test_sync_core.sh        # sync-core.sh 的断言测试
    test_check_skill.sh      # check-skill.sh 的断言测试
    test_progress_check.sh   # progress-check.py 的断言测试
    test_schema.py           # review-schema.json 的合法/非法样本校验
    fixtures/
      valid-review.json      # schema 合法样本
      invalid-missing-anchor.json   # 缺 anchor 的非法样本
      invalid-bad-severity.json     # severity 非枚举值的非法样本

skills/multi-agent-dev-iteration/
  SKILL.md                   # 入口:角色模型/何时用/工作流概览/引用
  references/
    orchestration.md         # 三角色真实调用、worktree、看门狗、逐 step 循环、失败处理
    codex-author-prompt.md   # Codex 主笔 prompt 模板(TDD:写测试→实现→跑绿)
    claude-review-prompt.md  # Claude 评审 prompt 模板(schema/category/落点)
    adversarial-core.md      # ← sync-core.sh 注入的母本副本(勿手改)
  assets/
    review-schema.json       # ← sync-core.sh 注入的母本副本(勿手改)
    dev-log-template.md      # dev-log 模板
```

每个文件单一职责;脚本与测试留在 `_adversarial-core/`,**不**随 sync 进入各 skill(sync 只复制 `adversarial-core.md` 与 `review-schema.json` 两件)。

---

## Phase 0 — 共享内核母本

### Task 1: 母本评审 schema `review-schema.json`

**Files:**
- Create: `skills/_adversarial-core/review-schema.json`
- Create: `skills/_adversarial-core/tests/test_schema.py`
- Create: `skills/_adversarial-core/tests/fixtures/valid-review.json`
- Create: `skills/_adversarial-core/tests/fixtures/invalid-missing-anchor.json`
- Create: `skills/_adversarial-core/tests/fixtures/invalid-bad-severity.json`

- [ ] **Step 1: 写失败测试 + fixtures**

`tests/fixtures/valid-review.json`:
```json
{
  "verdict": "needs-revision",
  "summary": "no-ship:存在 1 个 blocker。",
  "findings": [
    {
      "id": "F1",
      "severity": "blocker",
      "category": "correctness",
      "title": "限流中间件未处理 Redis 连接失败",
      "detail": "Redis 不可用时中间件抛未捕获异常,导致所有请求 500。",
      "anchor": "src/middleware/rateLimit.ts:42",
      "confidence": 0.9,
      "recommendation": "Redis 不可用时降级放行并告警,不要让请求 500。"
    }
  ],
  "prior_findings_status": [],
  "open_questions": []
}
```

`tests/fixtures/invalid-missing-anchor.json`(finding 缺 `anchor`,应判非法):
```json
{
  "verdict": "needs-revision",
  "summary": "x",
  "findings": [
    {"id":"F1","severity":"major","category":"testing","title":"t","detail":"d","confidence":0.5,"recommendation":"r"}
  ],
  "prior_findings_status": [],
  "open_questions": []
}
```

`tests/fixtures/invalid-bad-severity.json`(`severity` 非枚举,应判非法):
```json
{
  "verdict": "approve",
  "summary": "x",
  "findings": [
    {"id":"F1","severity":"critical","category":"testing","title":"t","detail":"d","anchor":"a:1","confidence":0.5,"recommendation":"r"}
  ],
  "prior_findings_status": [],
  "open_questions": []
}
```

`tests/test_schema.py`:
```python
import json, sys, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "..", "review-schema.json")
FIX = os.path.join(HERE, "fixtures")

def load(p): return json.load(open(p))

def validate(inst):
    """返回 True=合法。优先用 jsonschema;无则回退关键字段冒烟校验。"""
    schema = load(SCHEMA)
    try:
        import jsonschema
        jsonschema.validate(inst, schema)
        return True
    except ImportError:
        # 回退冒烟:与 orchestration 中的回退校验保持一致
        if inst.get("verdict") not in ("approve", "needs-revision"): return False
        for k in ("findings", "prior_findings_status", "open_questions"):
            if not isinstance(inst.get(k), list): return False
        for f in inst.get("findings", []):
            if f.get("severity") not in ("blocker","major","minor"): return False
            for req in ("id","anchor","recommendation","category","title","detail"):
                if not f.get(req): return False
            c = f.get("confidence")
            if not isinstance(c,(int,float)) or not (0 <= c <= 1): return False
        return True
    except Exception:
        return False

def main():
    cases = [("valid-review.json", True),
             ("invalid-missing-anchor.json", False),
             ("invalid-bad-severity.json", False)]
    failed = 0
    for name, expected in cases:
        got = validate(load(os.path.join(FIX, name)))
        ok = (got == expected)
        print(f"{'ok' if ok else 'FAIL'}: {name} expected={expected} got={got}")
        if not ok: failed += 1
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 skills/_adversarial-core/tests/test_schema.py`
Expected: FAIL —— `review-schema.json` 不存在,`load(SCHEMA)` 抛 `FileNotFoundError`,进程非零退出。

- [ ] **Step 3: 撰写母本 schema**

`skills/_adversarial-core/review-schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["verdict", "summary", "findings", "prior_findings_status", "open_questions"],
  "properties": {
    "verdict": { "type": "string", "enum": ["approve", "needs-revision"] },
    "summary": { "type": "string", "minLength": 1 },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "severity", "category", "title", "detail", "anchor", "confidence", "recommendation"],
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "severity": { "type": "string", "enum": ["blocker", "major", "minor"] },
          "category": { "type": "string", "minLength": 1 },
          "title": { "type": "string", "minLength": 1 },
          "detail": { "type": "string", "minLength": 1 },
          "anchor": { "type": "string", "minLength": 1 },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
          "recommendation": { "type": "string", "minLength": 1 }
        }
      }
    },
    "prior_findings_status": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "status", "evidence"],
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "status": { "type": "string", "enum": ["resolved", "partially_resolved", "unresolved"] },
          "evidence": { "type": "string", "minLength": 1 }
        }
      }
    },
    "open_questions": { "type": "array", "items": { "type": "string", "minLength": 1 } }
  }
}
```
> 注:`category` 故意为自由字符串(非枚举),以便 design/dev/test 三 skill 各自在 prompt 里约定取值,schema 仍可共用。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 skills/_adversarial-core/tests/test_schema.py`
Expected: PASS —— 三个样本全部 `ok`(valid 合法、两个 invalid 非法),退出码 0。
(若本机装了 `jsonschema` 走真校验;没装走回退冒烟,两条路径都应通过。)

- [ ] **Step 5: 提交**

```bash
git add skills/_adversarial-core/review-schema.json skills/_adversarial-core/tests/test_schema.py skills/_adversarial-core/tests/fixtures
git commit -m "feat(core): 新增对抗式内核母本评审 schema + 校验测试

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 母本规则文档 `adversarial-core.md`

**Files:**
- Create: `skills/_adversarial-core/adversarial-core.md`

散文型授权文件:按下列**精确章节与关键内容**撰写;关键规则文字为载重内容,须照写。

- [ ] **Step 1: 撰写母本规则文档**

文件首行加显式表头:`<!-- 母本:由 _adversarial-core 维护;各 skill 的副本为只读,勿手改,改这里再 sync-core.sh -->`

必含以下章节(用 `##` 标题,标题文字照下表):

1. `## 用途与适用` —— 说明这是 design/dev/test 三 skill 共用的对抗式迭代内核;副本只读;阈值与 category 由各 skill 自定。
2. `## 评审分级(severity)` —— blocker / major / minor 的**通用定义骨架**:
   - blocker:不解决不能推进——正确性/数据/安全/与现状不兼容/核心假设不成立/核心目标无法达成/无法验证。
   - major:严重但不绝对阻断——重要失效路径未覆盖、关键测试缺失、性能/可维护性实质隐患、缺回滚。
   - minor:改进项,记「已知债务」。
   - 注明:具体 `category` 取值与领域示例由各 skill 在自己的评审 prompt 里补充。
3. `## 结构化评审输出` —— 指向同目录(各 skill 内为 `assets/review-schema.json`)的 schema;每条 finding **必带 `anchor`(file:line / 接口 / 数据流 / 测试名),无 anchor 视为无效评审**;`confidence` 依赖推断时如实降低。
4. `## 终止规则机制(收敛判定 + 硬上限)` —— **通用机制**(阈值各 skill 自定,用占位 `K`/`M`):
   - **净进展**定义:本轮相较上轮,`prior_findings_status` 中有 prior 被标 `resolved`,**或** 未解决 blocker/major 计数严格下降。
   - **软规则**:连续 `K` 轮无净进展(同一 blocker/major 持续 unresolved;或本轮新增 blocker/major 数 ≥ 本轮解决数 = 打转)**或**主笔与评审存在分歧 → 停止该迭代单元,上交人类。
   - **硬上限**:绝对天花板 `M` 轮,到顶强制停止上交人类。
5. `## 反作弊纪律` —— 照写五条:① 绝不把缺失/失败/不合 schema 的评审当通过;② 不伪造命令/参数/端点/产物/评审;③ 任一外部调用失败如实处理、不得当通过;④ 主笔不能单方面把 blocker/major 降级,分歧上交人类;⑤ 无法验证的目标移入「未决问题」并说明原因。
6. `## 看门狗 / 存活监控` —— 照写:外部 CLI(`codex exec` / `claude -p`)**必须用宿主原生 subagent 包裹、前台同步跑,不让主 agent 裸跑**(否则长任务可能被自动后台化 + 子进程静默被杀 → 主 agent 干等/误判通过);退出码判定:`0`=成功、`1-2`=CLI 自身报错(看 stderr)、`≥128`=被信号杀(`137`=KILL、`143`=TERM);成功 = 退出码 0 + 合法产物,死亡 = 产物缺失;**失败至多重试一次,仍失败则停止上交人类**。
7. `## 文件驱动协作` —— 照写:状态全部落文件;子 agent 每次全新上下文;所需文件路径**显式传入**;不依赖跨调用记忆。
8. `## 输出校验` —— 照写并给出回退校验片段:退出码 + 产物非空 + 可解析 JSON + 合 schema;有 `jsonschema` 做真校验,否则回退关键字段冒烟(verdict 枚举、findings/prior_findings_status/open_questions 为 list、每条 finding 的 severity 枚举且 id/anchor/recommendation 非空);并强制:任一上一轮 blocker/major 仍非 resolved 却判 `approve` → 视为违反终止规则。

- [ ] **Step 2: 结构冒烟检查**

Run:
```bash
grep -cE '^## (用途与适用|评审分级|结构化评审输出|终止规则机制|反作弊纪律|看门狗|文件驱动协作|输出校验)' skills/_adversarial-core/adversarial-core.md
```
Expected: 输出 `8`(八个必需章节齐全)。

- [ ] **Step 3: 提交**

```bash
git add skills/_adversarial-core/adversarial-core.md
git commit -m "feat(core): 新增对抗式内核母本规则文档

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 同步脚本 `sync-core.sh`

**Files:**
- Create: `skills/_adversarial-core/sync-core.sh`
- Create: `skills/_adversarial-core/tests/test_sync_core.sh`

- [ ] **Step 1: 写失败测试**

`tests/test_sync_core.sh`:
```bash
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `bash skills/_adversarial-core/tests/test_sync_core.sh`
Expected: FAIL —— `sync-core.sh` 不存在,多条 `FAIL`,退出码 1。

- [ ] **Step 3: 撰写同步脚本**

`skills/_adversarial-core/sync-core.sh`:
```bash
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
```

- [ ] **Step 4: 赋可执行 + 跑测试确认通过**

Run:
```bash
chmod +x skills/_adversarial-core/sync-core.sh
bash skills/_adversarial-core/tests/test_sync_core.sh
```
Expected: PASS —— 全部 `ok`,退出码 0。

- [ ] **Step 5: 提交**

```bash
git add skills/_adversarial-core/sync-core.sh skills/_adversarial-core/tests/test_sync_core.sh
git commit -m "feat(core): 新增母本同步脚本 sync-core.sh + 测试

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 结构校验脚本 `check-skill.sh`

**Files:**
- Create: `skills/_adversarial-core/check-skill.sh`
- Create: `skills/_adversarial-core/tests/test_check_skill.sh`

校验目标 skill:① `SKILL.md` 存在;② frontmatter 含 `name:` 与 `description:`;③ `SKILL.md` 内以反引号引用的 `references/*` 与 `assets/*` 路径对应文件都存在。

- [ ] **Step 1: 写失败测试**

`tests/test_check_skill.sh`:
```bash
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `bash skills/_adversarial-core/tests/test_check_skill.sh`
Expected: FAIL —— `check-skill.sh` 不存在,退出码 1。

- [ ] **Step 3: 撰写校验脚本**

`skills/_adversarial-core/check-skill.sh`:
```bash
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
```

- [ ] **Step 4: 赋可执行 + 跑测试确认通过**

Run:
```bash
chmod +x skills/_adversarial-core/check-skill.sh
bash skills/_adversarial-core/tests/test_check_skill.sh
```
Expected: PASS —— 全部 `ok`,退出码 0。

- [ ] **Step 5: 提交**

```bash
git add skills/_adversarial-core/check-skill.sh skills/_adversarial-core/tests/test_check_skill.sh
git commit -m "feat(core): 新增 skill 结构校验脚本 check-skill.sh + 测试

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 收敛判定脚本 `progress-check.py`

实现 spec §7 / §11 的「净进展 + 硬上限」**机器判定**:给定各轮评审 JSON,输出 `complete` / `continue` / `escalate:no-progress` / `escalate:hard-cap` / `escalate:disagreement`。Orchestrator 在阶段 4 调用它做终止判定,不靠主观判断。

**Files:**
- Create: `skills/_adversarial-core/progress-check.py`
- Create: `skills/_adversarial-core/tests/test_progress_check.sh`

- [ ] **Step 1: 写失败测试**

`tests/test_progress_check.sh`:
```bash
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
  for i in $(seq 1 "$nb"); do finds+="{\"id\":\"F$i\",\"severity\":\"blocker\",\"category\":\"correctness\",\"title\":\"t\",\"detail\":\"d\",\"anchor\":\"a:1\",\"confidence\":0.9,\"recommendation\":\"r\"},"; done
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `bash skills/_adversarial-core/tests/test_progress_check.sh`
Expected: FAIL —— `progress-check.py` 不存在,退出码 1。

- [ ] **Step 3: 撰写脚本**

`skills/_adversarial-core/progress-check.py`:
```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run:
```bash
chmod +x skills/_adversarial-core/progress-check.py
bash skills/_adversarial-core/tests/test_progress_check.sh
```
Expected: PASS —— 全部 `ok`,退出码 0。

- [ ] **Step 5: 提交**

```bash
git add skills/_adversarial-core/progress-check.py skills/_adversarial-core/tests/test_progress_check.sh
git commit -m "feat(core): 新增收敛判定脚本 progress-check.py + 测试

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 1 — dev skill 撰写

### Task 6: 注入母本副本到 dev skill

**Files:**
- Create(由脚本生成): `skills/multi-agent-dev-iteration/references/adversarial-core.md`
- Create(由脚本生成): `skills/multi-agent-dev-iteration/assets/review-schema.json`

- [ ] **Step 1: 跑同步脚本注入母本**

Run:
```bash
mkdir -p skills/multi-agent-dev-iteration
bash skills/_adversarial-core/sync-core.sh skills/multi-agent-dev-iteration
```
Expected: 输出 `synced → skills/multi-agent-dev-iteration`,退出码 0。

- [ ] **Step 2: 校验副本与母本一致**

Run:
```bash
cmp skills/_adversarial-core/adversarial-core.md skills/multi-agent-dev-iteration/references/adversarial-core.md && \
cmp skills/_adversarial-core/review-schema.json skills/multi-agent-dev-iteration/assets/review-schema.json && echo SYNCED-OK
```
Expected: 输出 `SYNCED-OK`(两件副本逐字节等于母本)。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-dev-iteration/references/adversarial-core.md skills/multi-agent-dev-iteration/assets/review-schema.json
git commit -m "feat(dev-iteration): 注入对抗式内核母本副本

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Codex 主笔 prompt 模板 `codex-author-prompt.md`

**Files:**
- Create: `skills/multi-agent-dev-iteration/references/codex-author-prompt.md`

- [ ] **Step 1: 撰写主笔 prompt 模板**

按以下要点撰写(占位符用 `<...>`,被编排者填充后传给 Codex):
- 角色声明:你是实现主笔,按已冻结 DESIGN 与本 step 计划做 TDD 实现。
- 输入(占位):`<DESIGN 相关章节>`、`<本 step 计划条目>`、`<worktree 路径>`、`<上一轮 findings 与处理结论(若复评轮)>`。
- 任务顺序(照写):① 先写/补该 step 的测试;② 写最小实现;③ 跑测试到绿;④ 只动本 step 范围,不做范围外重构、不改 DESIGN。
- 沙箱与权限(照写):在 `<worktree>` 内操作,`--sandbox workspace-write`,默认断网。
- 复评轮附加:逐条处理传入的 findings,采纳则改代码、部分/拒绝给技术理由;**不得单方面降级 blocker/major**(分歧显式标注「与评审分歧,需上交人类」)。
- 回报格式(照写):改了哪些文件(`file:行`)、测试命令与结果、关键决策、仍存疑点。

- [ ] **Step 2: 冒烟检查关键占位符在场**

Run:
```bash
grep -qE 'workspace-write' skills/multi-agent-dev-iteration/references/codex-author-prompt.md && \
grep -qiE 'TDD|先写.*测试|跑.*绿' skills/multi-agent-dev-iteration/references/codex-author-prompt.md && echo PROMPT-OK
```
Expected: 输出 `PROMPT-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-dev-iteration/references/codex-author-prompt.md
git commit -m "feat(dev-iteration): 新增 Codex 主笔 prompt 模板

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Claude 评审 prompt 模板 `claude-review-prompt.md`

**Files:**
- Create: `skills/multi-agent-dev-iteration/references/claude-review-prompt.md`

- [ ] **Step 1: 撰写评审 prompt 模板**

按以下要点撰写:
- 角色声明:你是独立评审者,只读,挑实现的失效路径,不改代码。
- 输入(占位):`<diff>`、`<DESIGN 相关章节>`、`<本 step 目标>`、`<测试结果>`、`<上一轮 findings(复评轮)>`。
- 输出要求(照写):严格按 `assets/review-schema.json` 输出 JSON;每条 finding 必带 `anchor`(`file:行`/接口/数据流/测试名),无 anchor 无效。
- 本 skill 的 `category` 取值(照写枚举建议):`correctness` / `design-fidelity` / `test-quality` / `security` / `regression` / `maintainability` / `performance` / `scope`。
- 分级:引用 `references/adversarial-core.md` 的 severity 定义;本 skill blocker 额外含「测试造假或没真跑」「破坏现有功能(回归)」。
- 复评轮(照写):用 `prior_findings_status` 标 resolved/partially_resolved/unresolved,`findings` 只放未解决/新增;上一轮 blocker/major 未 resolved 不得 `approve`。

- [ ] **Step 2: 冒烟检查**

Run:
```bash
grep -qE 'review-schema\.json' skills/multi-agent-dev-iteration/references/claude-review-prompt.md && \
grep -qE 'anchor' skills/multi-agent-dev-iteration/references/claude-review-prompt.md && \
grep -qE 'prior_findings_status' skills/multi-agent-dev-iteration/references/claude-review-prompt.md && echo REVIEW-PROMPT-OK
```
Expected: 输出 `REVIEW-PROMPT-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-dev-iteration/references/claude-review-prompt.md
git commit -m "feat(dev-iteration): 新增 Claude 评审 prompt 模板

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: dev-log 模板 `dev-log-template.md`

**Files:**
- Create: `skills/multi-agent-dev-iteration/assets/dev-log-template.md`

- [ ] **Step 1: 撰写模板**

`skills/multi-agent-dev-iteration/assets/dev-log-template.md`:
```markdown
# 开发评审处理表 · <feature>

> 跨 step / 跨轮累积。每个 step 一节,记录每轮评审 findings、处理结论、测试结果。

## 元信息
- feature: <feature>
- 分支 / worktree: dev/<feature>
- 输入:DESIGN.md(冻结) + 实现计划
- 终止阈值:连续无进展轮数 K=2,硬上限 M=5

## Step <N>: <step 标题>

### 轮次 <R>
- 测试结果:<命令 + 通过/失败摘要>
- findings(来自 .review/step-<N>-round-<R>.json):
  | id | severity | category | anchor | 处理(采纳/部分/拒绝) | 理由 |
  |----|----------|----------|--------|----------------------|------|
  | F1 | blocker  | ...      | ...    | 采纳                 | ... |
- 净进展判定:<有/无,依据>
- 本 step 结论:<继续下一轮 / step 完成 / 上交人类(分歧或无进展或到硬上限)>

## 终止结论(全部 step 后)
- 整体:<GO / 上交人类>
- DESIGN 覆盖:<功能×验证矩阵 哪些项已实现>
- 待人类决策项:<若有>
```

- [ ] **Step 2: 提交**

```bash
git add skills/multi-agent-dev-iteration/assets/dev-log-template.md
git commit -m "feat(dev-iteration): 新增 dev-log 模板

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: 编排细节 `orchestration.md`

**Files:**
- Create: `skills/multi-agent-dev-iteration/references/orchestration.md`

载重文件。按下列章节与**关键命令**撰写;命令块为载重内容,照写。

- [ ] **Step 1: 撰写 orchestration.md**

必含章节(`##` 标题):

1. `## 状态载体` —— 列出 `docs/dev/<feature>/` 下 `dev-log.md` / `.author/step-<N>-prompt.md` / `.review/step-<N>-round-<R>.json`;文件驱动,引用 `references/adversarial-core.md` 的「文件驱动协作」。
2. `## 阶段 0:预检 + worktree + 人类检查点①` —— 含关键命令块:
   ```bash
   codex login status   # 预检 Reviewer 对侧主笔 Codex;失败则停下告知,不伪造
   REPO_ROOT=$(git rev-parse --show-toplevel)
   test -f "$REPO_ROOT/docs/design/<feature>/DESIGN.md" && grep -q "已冻结" "$REPO_ROOT/docs/design/<feature>/DESIGN.md" \
     || { echo "DESIGN 未冻结,停止"; exit 1; }
   git -C "$REPO_ROOT" diff --quiet && git -C "$REPO_ROOT" diff --cached --quiet || { echo "工作区不干净,停止"; exit 1; }
   WT="$REPO_ROOT/../<feature>-dev"
   git -C "$REPO_ROOT" worktree add -b dev/<feature> "$WT"
   mkdir -p "$REPO_ROOT/docs/dev/<feature>/.author" "$REPO_ROOT/docs/dev/<feature>/.review"
   ```
   随后向人类报告(计划步骤/worktree 路径/权限档/终止阈值)→ 用宿主提问工具确认开工。
3. `## 阶段 1:Codex 主笔(看门狗子 agent 包裹)` —— 照写:Orchestrator 用 Agent 工具(subagent_type `general-purpose`)派**看门狗子 agent**,任务=前台跑:
   ```bash
   codex exec --sandbox workspace-write --cd "$WT" \
     < "$REPO_ROOT/docs/dev/<feature>/.author/step-<N>-prompt.md"
   ```
   要点:Bash 工具 timeout 设 ~600000ms;子 agent 内判退出码(0/1-2/≥128,137/143)与产物;回报成功摘要或明确失败(退出码 + session jsonl 末行定因)。引用母本「看门狗 / 存活监控」。prompt 由 `codex-author-prompt.md` 填充写入 `.author/step-<N>-prompt.md`。
4. `## 阶段 2:Claude 独立评审` —— 照写:派**独立评审子 agent**,喂 `git -C "$WT" diff`、DESIGN 章节、step 目标、测试结果;按 `claude-review-prompt.md`;输出落 `.review/step-<N>-round-<R>.json`;随后做母本「输出校验」(退出码 + 非空 + 合 schema,可用 `_adversarial-core/tests/test_schema.py` 同款回退校验逻辑)。
5. `## 阶段 3:Codex 分诊修订` —— 照写:把 `.review/step-<N>-round-<R>.json` + `dev-log.md` + DESIGN 章节 + 上轮结论显式传回 Codex 子 agent;逐条采纳/部分/拒绝 + 理由;改完重跑测试;不得单方面降级。
6. `## 阶段 4:复评 + 终止判定` —— 照写:复评只标 `prior_findings_status` + 新增;按母本终止规则(本 skill K=2、M=5)判 继续/step 完成/上交人类,**调用 `_adversarial-core/progress-check.py --rounds .review/step-<N>-round-*.json --k 2 --m 5`(主笔↔评审分歧时加 `--disagreement`)做机器判定**。
7. `## 阶段 5:人类检查点②(合回主干)` —— 照写:全部 step 完成后汇总整体 diff / 测试 / DESIGN 覆盖 / dev-log 终止结论 → 人类确认后:
   ```bash
   git -C "$REPO_ROOT" merge --no-ff dev/<feature>   # 仅人类确认后
   git -C "$REPO_ROOT" worktree remove "$WT"
   ```
   NO 则不合并、保留分支、带未决项交人类。
8. `## 失败兜底` —— 照写:Codex 主笔失败/被杀 → 重试一次,仍失败停止上交人类;评审调用失败或不合 schema → 停止,禁止进入修订或合并,绝不静默当通过。

- [ ] **Step 2: 结构冒烟检查**

Run:
```bash
grep -cE '^## (状态载体|阶段 0|阶段 1|阶段 2|阶段 3|阶段 4|阶段 5|失败兜底)' skills/multi-agent-dev-iteration/references/orchestration.md
```
Expected: 输出 `8`。

并确认关键命令在场:
```bash
grep -qE 'worktree add -b dev/' skills/multi-agent-dev-iteration/references/orchestration.md && \
grep -qE 'codex exec --sandbox workspace-write --cd' skills/multi-agent-dev-iteration/references/orchestration.md && echo ORCH-OK
```
Expected: 输出 `ORCH-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-dev-iteration/references/orchestration.md
git commit -m "feat(dev-iteration): 新增编排细节(worktree/看门狗/逐 step 循环)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: 入口 `SKILL.md`

**Files:**
- Create: `skills/multi-agent-dev-iteration/SKILL.md`

- [ ] **Step 1: 撰写 SKILL.md**

frontmatter(照写键):
```yaml
---
name: multi-agent-dev-iteration
description: >-
  开发阶段的多智能体对抗式协作:吃冻结的 DESIGN.md + writing-plans 计划,逐 step
  由 Codex 在隔离 worktree(workspace-write 降权)里 TDD 主笔实现、独立 Claude 只读
  评审,收敛判定+硬上限迭代到每步无 blocker/major 且单测绿,产出实现代码(隔离分支)
  + dev-log,合回主干前交人类。当用户已有冻结设计与实现计划、要进入编码,并表达
  "按设计实现""让 Codex 写代码 Claude 评审""TDD 落地""逐步实现并评审"时触发。
---
```
正文必含章节(`##`):`角色模型`(三角色表,Codex 主笔/Claude 评审/Orchestrator,注明权限相对设计 skill 反转)、`何时使用 / 何时不用`(上游 DESIGN+计划已就绪;不重新设计、不做系统测试)、`核心原则`(引用 `references/adversarial-core.md` 反作弊/看门狗/文件驱动;写⊥审;头尾人类检查点;不私自降级 blocker)、`工作流`(阶段 0–5 概览,细节指向 `references/orchestration.md`)、`终止条件`(K=2/M=5,引用母本机制)、`输出`(隔离分支代码 + `docs/dev/<feature>/dev-log.md` + GO/上交人类)、`引用文件`(列出 references/assets 各文件)。
正文须以反引号引用这些文件:`references/orchestration.md`、`references/codex-author-prompt.md`、`references/claude-review-prompt.md`、`references/adversarial-core.md`、`assets/review-schema.json`、`assets/dev-log-template.md`。

- [ ] **Step 2: frontmatter 冒烟检查**

Run:
```bash
grep -qE '^name: multi-agent-dev-iteration' skills/multi-agent-dev-iteration/SKILL.md && \
grep -qE '^description:' skills/multi-agent-dev-iteration/SKILL.md && echo SKILL-OK
```
Expected: 输出 `SKILL-OK`。

- [ ] **Step 3: 提交**

```bash
git add skills/multi-agent-dev-iteration/SKILL.md
git commit -m "feat(dev-iteration): 新增 SKILL.md 入口

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: 结构自包含校验(最终闸门)

**Files:**
- 无新增(运行 Task 4 的校验脚本)

- [ ] **Step 1: 跑结构校验**

Run: `bash skills/_adversarial-core/check-skill.sh skills/multi-agent-dev-iteration`
Expected: 输出 `check-skill: OK skills/multi-agent-dev-iteration`,退出码 0(frontmatter 齐全、SKILL.md 引用的 references/assets 文件全部存在)。

- [ ] **Step 2: 若有悬空引用则修正**

若报「悬空引用 X」:对照 Task 7–11,补齐缺失文件或修正 SKILL.md 中的路径,重跑 Step 1 直到 OK。

- [ ] **Step 3: 提交(若有修正)**

```bash
git add -A skills/multi-agent-dev-iteration
git commit -m "fix(dev-iteration): 修正结构校验发现的悬空引用" || echo "无需修正"
```

---

## Phase 2 — 人工功能验证(手动,不自动化)

### Task 13: 真实回路冒烟与异常路径手动验证

> 这些是**集成/功能级手动验证**(需真实调起 Codex/Claude 子 agent),不纳入自动化测试。逐项手动执行并记录结果。

- [ ] **Step 1: 真实回路冒烟**
取一个最小真实 step(例如给某小模块加一个函数 + 单测),在一个 throwaway 仓库里实跑本 skill 的阶段 0→5,确认:worktree 建立、Codex TDD 实现跑绿、Claude 评审产 `.review/*.json` 且合 schema、修订后复评、step 完成、检查点②人工确认后合并。记录到一次性 dev-log。

- [ ] **Step 2: Codex 被杀 → 不假装通过**
人为让阶段 1 的 `codex exec` 被杀(如 timeout 调极小),确认看门狗子 agent 回报明确失败、Orchestrator 重试一次后停止上交人类,**绝不**进入评审/合并。

- [ ] **Step 3: 分歧 → 上交人类**
构造一个 Codex 拒绝某 blocker 的场景,确认流程标注「与评审分歧」并停下交人类,未私自降级。

- [ ] **Step 4: 无进展 / 硬上限 → 上交人类**
构造连续 2 轮同一 blocker 未解决,确认按 K=2 触发上交人类;另构造持续有新问题直到 M=5,确认到硬上限强制停止。

- [ ] **Step 5: 记录验证结论**
把上述 5 项结果汇总写入 `skills/multi-agent-dev-iteration/` 的一则验证记录(或 PR 描述),作为 §11 功能/集成验证的证据。

---

## 完成定义

- Phase 0、1 全部 Task 的自动化测试通过(`test_schema.py`、`test_sync_core.sh`、`test_check_skill.sh`、`test_progress_check.sh` 全绿;`check-skill.sh` 对 dev skill 输出 OK)。
- Phase 2 手动验证 5 项均有记录结论。
- dev skill 自包含、可被 Claude Code 识别加载。
- 后续(不在本计划):设计 skill 迁入 + 接入母本;测试 skill;编排层。
