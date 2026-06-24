# multi-agent-dev-iteration 编排细节

本文档是 Orchestrator（主 agent，唯一对接用户的角色）执行 `multi-agent-dev-iteration` skill 时的操作手册。它描述了从预检到合回主干的完整流程，规定了每个阶段的命令、subagent 分发方式以及各类失败的兜底策略。

**状态载体、终止规则、反作弊纪律、看门狗机制**均定义于 `references/adversarial-core.md`，本文档不重复定义，只在相关步骤中标注引用。Orchestrator 在执行前须已阅读 `adversarial-core.md` 全文。

---

## 状态载体

本 skill 采用**文件驱动协作**（见 `references/adversarial-core.md`「文件驱动协作」节），所有跨 subagent 的状态均落地为文件。主 agent、主笔 Codex subagent、评审 Claude subagent 之间**不依赖会话内记忆或变量传递**，每次调用子 agent 时必须在 prompt 中显式传入所需文件的绝对路径。

状态文件统一存放于主仓库内的 `docs/dev/<feature>/` 目录，结构如下：

- **`docs/dev/<feature>/dev-log.md`** — 迭代日志，记录每个 step 的轮次、结论、净进展计数、终止决定及人类检查点确认情况。每轮结束由 Orchestrator 追写，不由子 agent 直接写入。
- **`docs/dev/<feature>/.author/step-<N>-prompt.md`** — 第 N 个 step 传给 Codex 主笔的完整 prompt，由 Orchestrator 按 `references/codex-author-prompt.md` 模板填入后写入此文件；`codex exec` 以 stdin 方式读入。
- **`docs/dev/<feature>/.review/step-<N>-round-<R>.json`** — 第 N 个 step 第 R 轮的评审输出，必须为合法 JSON 且符合 `assets/review-schema.json`。评审 subagent 将 JSON 写入此文件；Orchestrator 读取后执行输出校验再用于收敛判定。

`.author/` 目录中的 prompt 文件在每轮修订时覆盖重写（追加上一轮 findings 与处理结论），`.review/` 目录中的 JSON 文件按轮次递增编号，永不覆盖，以保留完整历史供人类检查点②审查。

---

## 阶段 0:预检 + worktree + 人类检查点①

在任何代码改动之前，Orchestrator 首先执行完整性预检，确认运行环境、DESIGN 冻结状态和工作区干净程度均满足要求，然后创建隔离 worktree，最后向人类报告并等待确认。

**预检命令（在主仓库中执行）：**

```bash
codex login status   # 预检主笔 Codex；失败则停下告知，不伪造
REPO_ROOT=$(git rev-parse --show-toplevel)
test -f "$REPO_ROOT/docs/design/<feature>/DESIGN.md" && grep -q "已冻结" "$REPO_ROOT/docs/design/<feature>/DESIGN.md" \
  || { echo "DESIGN 未冻结，停止"; exit 1; }
git -C "$REPO_ROOT" diff --quiet && git -C "$REPO_ROOT" diff --cached --quiet || { echo "工作区不干净，停止"; exit 1; }
WT="$REPO_ROOT/../<feature>-dev"
git -C "$REPO_ROOT" worktree add -b dev/<feature> "$WT"
mkdir -p "$REPO_ROOT/docs/dev/<feature>/.author" "$REPO_ROOT/docs/dev/<feature>/.review"
```

逐项说明：

1. `codex login status` — 验证 Codex CLI 已登录可用；若失败，**立即停止并告知用户，不伪造成功状态**（见 `adversarial-core.md`「反作弊纪律」②）。
2. DESIGN 冻结检查 — 确认 `docs/design/<feature>/DESIGN.md` 存在且文件内包含"已冻结"标记；任一条件不满足则终止，不允许在未冻结 DESIGN 上开始实现。
3. 工作区干净检查 — 同时检查未暂存与已暂存变更；有任何脏文件则终止，防止意外混入无关变更。
4. `worktree add -b dev/<feature>` — 在主仓库旁边创建独立 worktree，所有代码改动在此隔离进行；Codex 的 `--cd "$WT"` 将其沙箱根目录绑定到这里。
5. 创建 `.author/` 和 `.review/` 目录 — 为后续 step 的 prompt 文件和评审 JSON 文件预备落地位置。

**预检全部通过后，向人类报告以下信息并使用宿主提问工具（ask_followup_question 或等效）等待确认后再开工：**

- 计划包含的 step 列表及各 step 目标摘要（来源：writing-plans 计划文档）
- Worktree 路径（`$WT`）
- Codex 沙箱权限档：`workspace-write`（只能读写 worktree 内文件，不得访问外部网络）
- 终止阈值：K=2（连续无净进展轮数上限），M=5（绝对轮数上限）

人类拒绝或提出修改意见时，Orchestrator 根据反馈调整后再次确认，不得在未获确认的情况下进入阶段 1。

---

## 阶段 1:Codex 主笔（看门狗子 agent 包裹）

每个 step 的代码实现由 **Codex** 完成，但不允许 Orchestrator 直接裸跑 `codex exec`（原因见 `references/adversarial-core.md`「看门狗 / 存活监控」节）。Orchestrator 必须分发一个**看门狗 Claude subagent**（Agent tool，general-purpose 类型），由它以**前台同步方式**运行 Codex，监控退出码和产物，并向 Orchestrator 回报明确结论。

在分发看门狗子 agent 前，Orchestrator 先记录本 step 的基准提交：

```bash
STEP_BASE=$(git -C "$WT" rev-parse HEAD)
```

此时 `dev/<feature>` 分支上的 HEAD 即为本 step 开始前的状态。Codex 在 worktree 中执行时，可能在该分支上创建一个或多个新提交；`STEP_BASE` 用于后续阶段 2 精确计算本 step 引入的全部变更（包括 Codex 已提交的变更）。

随后 Orchestrator 将本轮 prompt 写入 `.author/step-<N>-prompt.md`：按 `references/codex-author-prompt.md` 模板，填入本 step 目标、DESIGN 相关章节、worktree 路径，以及（复评轮时）上一轮 findings 与处理结论；首轮删除复评轮附加要求节，不留空占位符。

**看门狗 subagent 执行的核心命令：**

```bash
codex exec --sandbox workspace-write --cd "$WT" \
  < "$REPO_ROOT/docs/dev/<feature>/.author/step-<N>-prompt.md"
```

看门狗子 agent 的任务是：
- 使用 Bash tool（timeout 建议设为 600000ms）同步等待 `codex exec` 完成，不后台化。
- 检查退出码并按以下语义判定（见 `adversarial-core.md`「退出码语义」）：
  - `0`：调用成功，继续检查产物；
  - `1`–`2`：Codex CLI 自身报错，提取 stderr 错误信息；
  - `≥ 128`：被操作系统信号强杀，其中 `137` = SIGKILL（OOM 或超时），`143` = SIGTERM（优雅终止）。
- 确认产物存在且非空：退出码 0 但产物缺失或为空，同样视为失败。
- 向 Orchestrator 回报：成功时给出改动文件列表、测试结果摘要；失败时给出**退出码 + Codex session jsonl 末行内容**（或 stderr 关键行），绝不静默。

Orchestrator 收到看门狗回报后：若成功，继续进入阶段 2；若失败，先按「失败兜底」节处理，再决定是否继续。

---

## 阶段 2:Claude 独立评审

代码产物就绪后，Orchestrator 分发一个**独立评审 subagent**（Agent tool，general-purpose 类型）。评审 subagent 与主笔完全独立，不共享上下文，天然防止立场污染。

**Orchestrator 向评审 subagent 传入的材料（所有路径均为绝对路径）：**

- `git -C "$WT" diff "$STEP_BASE"..HEAD` 的输出（本 step 从基准提交到当前 HEAD 的全量 diff，涵盖 Codex 已提交的变更及任何未提交的残余变更；与阶段 5 的 `main...dev/<feature>` range-diff 风格一致）
- `docs/design/<feature>/DESIGN.md` 中本 step 涉及的相关章节文本
- 本 step 目标描述（来自 writing-plans 计划）
- Codex 回报中的测试运行结果（命令 + 退出码 + stdout/stderr 摘录）
- 上一轮评审 JSON 的**绝对路径** `$REPO_ROOT/docs/dev/<feature>/.review/step-<N>-round-<R-1>.json`（复评轮时必填；首轮传空）

> **注意**：评审 subagent 是无 cwd 上下文的全新 agent，Orchestrator 必须在 prompt 中传入所有状态文件的**绝对路径**（含 `$REPO_ROOT/docs/dev/<feature>/.review/`、`$REPO_ROOT/docs/dev/<feature>/dev-log.md`、`$REPO_ROOT/docs/dev/<feature>/.author/` 下的相关文件），不得使用相对路径。

评审 subagent 按 `references/claude-review-prompt.md` 模板执行评审，输出严格符合 `assets/review-schema.json` 的 JSON。评审 JSON 的落盘方式二选一：若宿主已向评审 subagent 授予 Write tool，由评审 subagent 直接将 JSON **写入** `$REPO_ROOT/docs/dev/<feature>/.review/step-<N>-round-<R>.json`；若宿主无法为 subagent 授予文件写入权限，则 Orchestrator 从评审 subagent 的返回消息中提取 JSON 内容，由 Orchestrator 自行写入该绝对路径。无论采用哪种方式，**JSON 文件必须在下一步输出校验运行前已落盘到该绝对路径**。

**Orchestrator 在使用评审结果前必须执行「输出校验」**（见 `adversarial-core.md`「输出校验」节），复用与 `_adversarial-core/tests/test_schema.py` 相同的校验逻辑：

1. **优先**：若环境中存在 `jsonschema`，执行完整 schema 校验，对照 `assets/review-schema.json`。
2. **回退**：若无 `jsonschema`，执行关键字段冒烟校验：`verdict` 为 `"approve"` 或 `"needs-revision"` 之一；`findings`、`prior_findings_status`、`open_questions` 均为列表；`summary` 非空；每条 finding 的 `severity`、`confidence`、`id`、`category`、`title`、`detail`、`anchor`、`recommendation` 均有效。
3. **强制约束**：若上一轮存在未 resolved 的 blocker/major，而本轮 `verdict` 为 `approve`——无论 schema 是否通过，该评审视为无效，触发「评审逻辑矛盾」并上交人类。

校验通过后，Orchestrator 将评审结论记录至 `dev-log.md`，然后判断是否进入阶段 3：若 `verdict` 为 `approve` 且无新 blocker/major，可直接跳至阶段 4 的终止判定；否则进入阶段 3。

---

## 阶段 3:Codex 分诊修订

当评审 `verdict` 为 `needs-revision` 时，Orchestrator 组织一次分诊修订：将评审结果与必要上下文**显式**传回给 Codex 主笔（同样包裹在看门狗 subagent 中），要求逐条处理 findings。

**传给 Codex 的材料必须包含（所有路径均为绝对路径）：**

- 本轮评审 JSON：`$REPO_ROOT/docs/dev/<feature>/.review/step-<N>-round-<R>.json`（包含所有 findings 与 prior_findings_status）
- 当前迭代日志：`$REPO_ROOT/docs/dev/<feature>/dev-log.md` 中本 step 的迭代历史
- 当前 step 的 prompt 文件：`$REPO_ROOT/docs/dev/<feature>/.author/step-<N>-prompt.md`（供 Codex 了解历轮修订累积上下文）
- DESIGN 相关章节（与阶段 2 相同部分）
- 上一轮 Codex 回报中的「关键决策」与「仍存疑点」

> **注意**：分诊修订时同样分发全新的看门狗 subagent，该 subagent 没有任何会话记忆，Orchestrator 必须在 prompt 中传入上述所有文件的**绝对路径**，不得依赖相对路径或隐含上下文。

Codex 按 `references/codex-author-prompt.md`「复评轮附加要求」节逐条处置每条 finding：

- **采纳**：直接修改代码并在回报中注明 `[采纳] <finding 编号>`；
- **部分采纳 / 拒绝**：在回报中给出有代码或设计依据的技术理由；
- **与评审分歧**：若对某条 blocker/major 的等级或成立性存在分歧，**不得单方面降级**（见 `adversarial-core.md`「反作弊纪律」④），必须在回报中显式标注「与评审分歧，需上交人类：<具体分歧描述>」。

修订完成后，Codex **必须重跑测试**，确认本 step 相关测试仍为绿色，并在回报中附上退出码和输出摘要。若重跑测试失败，Codex 应继续修复，直到测试通过，不得在测试红灯状态下提交回报。

Orchestrator 收到分诊修订回报后，更新 `.author/step-<N>-prompt.md`（追加本轮 findings 与处理结论），然后返回**阶段 2** 进行下一轮独立评审。

---

## 阶段 4:复评 + 终止判定

每轮评审输出校验通过后，Orchestrator 运行收敛判定脚本，确定本 step 是否可以结束：

```bash
python3 "<SKILL_DIR>/../_adversarial-core/progress-check.py" \
  --rounds "$REPO_ROOT"/docs/dev/<feature>/.review/step-<N>-round-*.json --k 2 --m 5
```

其中 `<SKILL_DIR>` 是本 skill 的目录（`skills/multi-agent-dev-iteration`），`../_adversarial-core/progress-check.py` 指向 `skills/_adversarial-core/progress-check.py`。`--rounds` 传入本 step 所有已完成轮次的评审 JSON，按轮次顺序（shell glob 通常按文件名排序，确保文件名中轮次编号为数字补零格式）。

当主笔与评审在某条 blocker/major 上持续存在分歧（连续出现超过 1 轮）时，在命令后追加 `--disagreement`，让脚本将分歧纳入判定：

```bash
python3 "<SKILL_DIR>/../_adversarial-core/progress-check.py" \
  --rounds "$REPO_ROOT"/docs/dev/<feature>/.review/step-<N>-round-*.json --k 2 --m 5 --disagreement
```

脚本输出（stdout 一行）的处理规则：

- **`complete`** — 本 step 已通过对抗评审，Orchestrator 在 `dev-log.md` 中记录「step-<N> 完成」，推进到下一 step（重新从阶段 1 开始）或全部 step 完成后进入阶段 5。
- **`continue`** — 迭代尚未收敛，返回阶段 1 继续下一轮主笔修订。
- **`escalate:*`** — 触发软规则或硬上限：
  - `escalate:no-progress`：连续 K=2 轮无净进展，自动循环已无法突破；
  - `escalate:hard-cap`：已达 M=5 轮绝对上限；
  - `escalate:disagreement`：主笔与评审分歧超阈值。

  任一 `escalate` 结果均**必须立即停止当前 step 的自动迭代**，将完整状态（所有轮次评审 JSON、当前 worktree diff、`dev-log.md`、分歧摘要）上交人类决策，并明确说明触发原因。不得静默继续。

---

## 阶段 5:人类检查点②（合回主干）

所有 step 均以 `complete` 结束后，Orchestrator 汇总本次开发的整体情况，向人类提交合并请求并等待确认：

**汇总内容：**

1. 整体 diff 摘要：`git -C "$WT" diff main...dev/<feature>`（或对比基准分支）中改动的文件列表与行数统计；
2. 测试结果：最后一轮各 step 的测试命令与通过情况；
3. DESIGN 覆盖检查：`dev-log.md` 中每个 step 与 DESIGN 章节的对应关系，确认无遗漏；
4. `dev-log.md` 终止结论：各 step 的轮次数、最终 verdict、有无上交人类的 escalate 事件；
5. 已知债务清单：各轮未采纳的 minor findings（记录于 `dev-log.md`「已知债务」节）。

**人类确认后执行合并：**

```bash
git -C "$REPO_ROOT" merge --no-ff dev/<feature>   # 仅人类确认后
git -C "$REPO_ROOT" worktree remove "$WT"
```

`--no-ff` 保留完整的 feature 分支历史，便于后续追溯。合并完成后移除 worktree（不删除 `dev/<feature>` 分支，由人类决定是否保留）。

**人类拒绝时：** 不执行合并，保留 `dev/<feature>` 分支和 worktree，将人类提出的未决问题记录至 `dev-log.md` 末尾，等待人类进一步指示。Orchestrator 不得在未获人类明确确认的情况下自行合并。

---

## 失败兜底

本节定义所有非正常退出情形的处理规则，适用于阶段 1 至阶段 4 中任一步骤。

**Codex 主笔（看门狗 subagent）失败：**

若看门狗 subagent 报告 Codex 调用失败（退出码非 0、产物缺失/为空、或信号强杀），Orchestrator **至多重试一次**。重试前在 `dev-log.md` 中记录失败的退出码、stderr 关键行，以及重试原因。若重试仍失败，则**立即停止当前 step，将失败详情（退出码 + 错误信息 + session jsonl 末行）上交人类**，不得第三次重试，不得绕过失败继续走评审流程（见 `adversarial-core.md`「重试策略」）。

**评审 subagent 调用失败或输出不合 schema：**

若评审 subagent 未产出输出、输出不可解析为 JSON、或 JSON 未通过输出校验，**立即停止迭代**。禁止进入阶段 3 修订或阶段 5 合并，绝不将评审失败静默当作"通过"处理（见 `adversarial-core.md`「反作弊纪律」①）。Orchestrator 将失败情况（校验失败原因 + 原始输出片段）记录至 `dev-log.md` 并上交人类，由人类决定是否重试该轮评审。

**通用原则：** 任何外部调用（`codex exec`、评审 subagent）失败后，Orchestrator 的报告中必须包含：失败发生在哪个 step 的第几轮、失败类型（主笔/评审）、具体错误信息、已完成的轮次评审 JSON 路径列表。这样人类在接手时能完整了解现状，不需要 Orchestrator 代为解读。
