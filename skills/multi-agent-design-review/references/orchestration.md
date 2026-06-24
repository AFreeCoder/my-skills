# 编排细节(Orchestration)

三角色工作流的真实调用方式。主路径是 **Claude Code 为宿主**;末尾给 Codex-host 镜像。
`<SKILL_DIR>`=本 Skill 目录,`<feature>`=kebab-case 短名,`<N>`=评审轮次。

> **目录**:状态载体 · Claude-host 主路径(阶段 0→5)· **Reviewer 调用的存活监控(防静默失败)** · Codex-host 镜像 · 为什么不"一律 exec 自调用"

## 状态载体:角色基于文件协作

状态全部落在文件里,角色据此协作,**不依赖跨调用记忆**:

- `docs/design/<feature>/DESIGN.md` — 设计文档(Author 维护)
- `docs/design/<feature>/review-log.md` — 评审处理表(Author 维护)
- `docs/design/<feature>/.codex/round-<N>-prompt.md` — 每轮喂给 Reviewer 的 prompt
- `docs/design/<feature>/.codex/round-<N>.json` — 每轮 Reviewer 结构化输出

**Author 每轮都是全新 subagent**:把上述文件路径 + 本轮任务传给它即可。统一**文件驱动**——不要假设宿主能"续同一 subagent 的记忆",阶段 3 必须把所需文件显式传进去。

## Claude-host 主路径

### 阶段 0 — 需求理解与澄清(Orchestrator 亲自做)

```bash
codex login status      # 预检 Reviewer;失败则停下告知用户,不伪造

# 仓库根:非 git 仓库时回退当前目录(codex exec 已带 --skip-git-repo-check)
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || REPO_ROOT="$(pwd)"
DESIGN_DIR="$REPO_ROOT/docs/design/<feature>"

# 目录预检:禁止静默覆盖已冻结设计 / 混用旧轮次产物
if [ -d "$DESIGN_DIR" ]; then
  if grep -q "已冻结" "$DESIGN_DIR/DESIGN.md" 2>/dev/null; then
    echo "✋ 已有冻结设计 → 请用户选:换新 <feature> 名 / 归档旧目录 / 显式 resume。未选择前不要继续。"; exit 2
  fi
  # 草稿续跑:归档上一轮 .codex,避免与本轮混用(轮次隔离)
  ts=$(date +%Y%m%d-%H%M%S 2>/dev/null || echo prev)
  [ -d "$DESIGN_DIR/.codex" ] && mv "$DESIGN_DIR/.codex" "$DESIGN_DIR/.codex-$ts"
  mkdir -p "$DESIGN_DIR/.codex"
  echo "↻ 续跑:旧 .codex 已归档为 .codex-$ts;按当前轮次继续。"
else
  mkdir -p "$DESIGN_DIR/.codex"
fi
```

feature 短名由 Orchestrator 依需求拟定,放进阶段 0 第一问与用户一起确认。
现状调研可委派**宿主的调研子任务工具**(Claude Code:**Explore 子 Agent**,subagent_type: `Explore`;宿主无此类工具则 Orchestrator 自行读代码调研):

> 调研 `<feature>` 涉及的现有代码/数据模型/接口/约定,产出现状摘要与改动影响面,给出 `文件:行` 指针。

Orchestrator 汇总成「待确认清单」(`requirements-clarification.md`),用**宿主的提问工具**(Claude Code:`AskUserQuestion`;宿主无此工具则在主对话直接逐条提问)逐条确认,结论写入 `DESIGN.md` 顶部「已确认需求与约束」。

### 阶段 1 / 阶段 3 — 委派 Author 子 Agent(Agent 工具,subagent_type: `general-purpose`)

> ⚠️ **若目标环境无该 agent 类型,Orchestrator 自己主笔**(它本就是 Claude),不要因缺 agent 卡住。
> ⚠️ **把 prompt 转给子 Agent 前,必须把 `<SKILL_DIR>` 替换成绝对路径**——子 Agent 在隔离上下文里看不到本 skill 目录,拿到字面量会读不到模板。

**阶段 1(主笔)** prompt 要点:

- 角色:设计主笔,把方案写成清晰、可落地、每个功能可验证的详细设计。
- 输入:已确认需求与约束(贴全文)、现状调研摘要、模板**绝对路径** `<SKILL_DIR>/references/design-doc-template.md`。
- 任务:按模板写 `docs/design/<feature>/DESIGN.md`,**必须含「功能 × 验证矩阵」**;写"现状"前读真实代码核对。
- 约束:不写实现代码;不做范围外重构;每条落到文件/接口/数据流/测试。
- 回报:完成情况 + 关键决策 + 自己仍存疑的点。

**Author 失败兜底**:子 Agent 失败 / 返回空 / 产出不含验证矩阵 → **Orchestrator 自己接管主笔**,不空转重试、不伪造产物。

**阶段 3(分诊修订)** prompt 要点 —— **传入文件(不依赖记忆)**:`DESIGN.md` 路径、本轮 `.codex/round-<N>.json`、`review-log.md` 路径、已确认需求、上一轮处理结论。

- 任务:逐条处理 findings —— 采纳则改 `DESIGN.md` 并在 `review-log.md` 记改动位置;部分/拒绝给**技术理由**;拒绝 Blocker/Major 显式标注"与评审分歧,需上交人类"。
- 约束:不为通关软化问题;也不无脑全收(Reviewer 可能缺上下文)。

Orchestrator 拿回报后复核分级争议,决定继续循环 / 冻结 / 上交人类。

### 阶段 2 / 阶段 4 — 调起 Reviewer(`codex exec` 只读)+ 输出校验

```bash
cp "<SKILL_DIR>/assets/codex-review-schema.json" "$DESIGN_DIR/.codex/review-schema.json"

# 用 codex-review-prompt.md 填充占位符写入 round-<N>-prompt.md:
#   ROUND=1:PRIOR_FINDINGS="无(首轮)"
#   ROUND=2:PRIOR_FINDINGS = 第 1 轮 findings + Author 处理结论

codex exec \
  --sandbox read-only \
  --skip-git-repo-check \
  --cd "$REPO_ROOT" \
  --output-schema "$DESIGN_DIR/.codex/review-schema.json" \
  --output-last-message "$DESIGN_DIR/.codex/round-<N>.json" \
  < "$DESIGN_DIR/.codex/round-<N>-prompt.md"
EXIT=$?

# 输出校验:结构的"主"保证来自 --output-schema(codex 在源头按 schema 生成);
# 下面再校验一次,防 codex 异常(非零退出 / 截断 / 空输出),失败则停止、禁止进入阶段3或冻结。
test "$EXIT" -eq 0 || { echo "codex 评审失败(exit $EXIT),见 stderr"; exit 1; }
test -s "$DESIGN_DIR/.codex/round-<N>.json" || { echo "评审输出为空"; exit 1; }

# 完整 schema 校验:有 jsonschema 则做真正的 JSON Schema 校验,否则回退关键字段冒烟
python3 - "$DESIGN_DIR/.codex/round-<N>.json" "$DESIGN_DIR/.codex/review-schema.json" <<'PY' || { echo "评审输出不合 schema"; exit 1; }
import json, sys
inst = json.load(open(sys.argv[1]))
try:
    import jsonschema
    jsonschema.validate(inst, json.load(open(sys.argv[2])))
except ImportError:
    assert inst.get("verdict") in ("approve", "needs-revision")
    for k in ("findings", "prior_findings_status", "open_questions"):
        assert isinstance(inst.get(k), list)
    for f in inst["findings"]:
        assert f.get("severity") in ("blocker", "major", "minor")
        assert f.get("id") and f.get("anchor") and f.get("recommendation")
# 终止完整性(防 reviewer 漏判/手滑):任一上一轮 blocker/major 未 resolved → 不得 approve
unresolved = [p.get("id") for p in inst.get("prior_findings_status", [])
              if p.get("status") != "resolved"]
assert not (unresolved and inst.get("verdict") == "approve"), \
    f"上一轮未解决项 {unresolved} 仍在却判 approve,违反终止规则"
print("schema OK")
PY
```

`--sandbox read-only` 保证 Reviewer 只读;`--output-schema` 强约束 Blocker/Major/Minor 结构。第 2 轮的解决状态由 schema 的 `prior_findings_status` 承载(resolved / partially_resolved / unresolved),`findings` 只放未解决/新增。**调用/进程失败(非零退出/被杀/超时)可重试一次;输出存在但不合 schema、或重试后仍失败 → 停止,绝不把"缺失评审"当成通过**(与 SKILL.md 阶段 2 同一规则)。

### Reviewer 调用的存活监控(防静默失败)—— 用子 agent 包装,别让主 agent 裸跑

**问题(实证踩过)**:若 Orchestrator **直接**用 Bash 跑上面那条 `codex exec`,长任务会被 Bash 工具**自动转入后台**;一旦 codex 子进程在 turn 边界被外部信号静默杀死(死在 `task_started`、无产物),后台完成通知**不可靠** → **主 agent 无限干等**,甚至把"缺失评审"误当通过。根因是「单一唤醒源(后台通知)+ 子进程静默死亡」,**与推理强度无关**(同样 xhigh 在前台能跑完;"xhigh 太慢"是被证伪的草率归因)。

**解法:把 `codex exec` 包进一个专职子 agent**,而不是主 agent 直接跑。理由:Claude Code 对**子 agent** 的生命周期监管是可靠的——`Agent` 调用要么返回结果、要么在子 agent 终态死亡时返回 `null`,**主 agent 绝不会卡在"等一个永不来的通知"里**。对那个子 agent 而言,`codex exec` 就是**前台同步**的(实测:子 agent 内部前台跑久命令**不会**被自动后台化,90s 命令照样阻塞到结束、单次往返返回;成功=退出码 0+合法 JSON 产物、死亡=退出码 137+产物缺失,都在单次往返内确定性闭环)。

阶段 2/4 不再由主 agent 裸跑 codex,改为:

> Orchestrator 用 **Agent 工具(subagent_type: `general-purpose`)** 派一个子 agent,任务 = **前台**跑上面那条 `codex exec`:
> - 把 **Bash 工具 timeout 设到 ~600000ms** 覆盖最长耗时(否则工具层先超时);
> - **必须显式 `--sandbox read-only` 降权**(该用户 codex 全局默认 danger-full-access + never);
> - **保持全局 xhigh 全量思考深度,不加任何降 effort 的 `-c` 覆盖**(effort 与可靠性无关,看门狗/监管才是);
> - 子 agent 内做上面的输出校验(退出码 0 + `round-<N>.json` 非空、合法 JSON、合 schema);
> - **回报**:成功 → 回传校验通过的评审 JSON(或其路径);失败 → 回传**明确失败**:退出码(0=成功 / 1-2=codex 自身报错看 stderr / ≥128=被信号杀,137=KILL、143=TERM)+ 本次 session jsonl 末行定因(`~/.codex/sessions/<年>/<月>/<日>/rollout-<ISO>-<sessionid>.jsonl`;停在 `event_msg/task_started` 而非 `task_complete` = 被外部杀、非业务失败)。

主 agent 收到子 agent 回报(成功 JSON / 明确失败 / `null`)→ 按原则:成功进阶段 3 或冻结;失败**至多重试一次**(重派子 agent);仍失败则**停止并向用户报告**,绝不静默当通过。**全程不依赖后台通知、不手搓轮询、主 agent 不会干等。**

**残留(非阻塞,真踩到再处理)**:① Bash 工具 timeout 上限 600000ms(10 分钟),codex 评审若可能超 10 分钟需另拆(实测一轮通常几分钟内);② 子 agent 内 codex 被 Bash timeout 杀时,codex 子进程树是否被干净回收、会不会留孤儿烧配额,未实测。
> 次选(不便派子 agent 时):主 agent **前台同步** + 大 timeout 跑 codex(始终把控制权同步还给宿主、不依赖通知),但要承受"长任务可能被自动后台化"的风险;首选仍是子 agent 包装。

## Codex-host 镜像(⚠️ 未实测,备用)

宿主是 Codex 时:Orchestrator + Reviewer = Codex 本地承担(**不要** `codex exec` 自调用);Author = 跨 CLI:

```bash
claude -p "<Author prompt,要点同上>" \
  --append-system-prompt "你是设计主笔,只产出设计文档,不写实现代码。" \
  --output-format text
```

Codex 读回 `DESIGN.md`、本地评审,循环逻辑同主路径。

## 为什么不"一律 exec 自调用"

会话内委派子任务,Claude Code 官方推荐 **subagent**(隔离上下文/共享基础设施/集成权限);`claude -p` 是给外部脚本/CI 的无状态模式。**跨模型**才用对方 headless CLI。两种宿主下都**零自调用**。
