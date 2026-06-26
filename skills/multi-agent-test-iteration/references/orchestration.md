# Orchestrator 执行手册

> **前置声明：** Orchestrator 在执行本手册前，须已完整阅读以下两份文件：
>
> - `references/adversarial-core.md`——终止规则、反作弊纪律、文件驱动协作、输出校验、看门狗机制的完整定义均在其中；本文件不重复定义，只按需引用。
> - `references/host-adapter.md`——起子 agent、向用户提问、跑命令、跑 UI 的抽象能力到当前宿主工具的映射表；本文件使用抽象能力词，执行时按该表替换为具体工具。

---

## 状态载体

本 skill 采用**文件驱动协作**（见 `references/adversarial-core.md` 「文件驱动协作」章节）：每个子 agent 在全新上下文中启动，所需状态文件须以**绝对路径**显式传入 prompt，不依赖 agent 的会话内记忆。

所有状态文件统一落地于 `docs/test/<feature>/`（以及其子目录），清单如下：

| 文件路径 | 产出时机 | 产出方 |
|---|---|---|
| `docs/test/<feature>/scope-input-summary.md` | 阶段 0 调研后，Orchestrator 亲自写入 | Orchestrator |
| `docs/test/<feature>/.review/scope-review-round-<R>.json` | 阶段 0 每轮范围对抗后 | 评审子 agent 产出 JSON，Orchestrator 落地文件 |
| `docs/test/<feature>/test-matrix.md` | 阶段 0 人类检查点①确认后冻结 | 产矩阵子 agent 产出，Orchestrator 合并人类裁决后落地 |
| `docs/test/<feature>/test-log.md` | 每个目标收尾时追加 | Orchestrator |
| `docs/test/<feature>/bug-report.md` | 每轮 `real-bug` 分流后追加 | Orchestrator |
| `docs/test/<feature>/.author/goal-<G>-layer-<层级>-prompt.md` | 每次主笔前，Orchestrator 按模板填写后落地 | Orchestrator |
| `docs/test/<feature>/.review/goal-<G>-round-<R>.json` | 阶段 1 每目标每轮评审后，Orchestrator 汇总各层级评审产出为一个文件 | Orchestrator 汇总写入 |

**说明：**

- `scope-input-summary.md` 是阶段 0 的调研摘要（功能场景清单 + 超出设计的补充项候选 + dev-log 已覆盖单测），由 Orchestrator 在产矩阵子 agent 启动前写入，供 Author 子 agent 和 Reviewer 子 agent 读取（见 `references/scope-planning.md`）。
- `scope-review-round-<R>.json` 是阶段 0 范围对抗的结构化评审输出，`<R>` 从 1 起步，每轮一个文件，便于追溯与上交人类时提供完整历史（见 `references/scope-planning.md`）。
- `.author/goal-<G>-layer-<层级>-prompt.md` 是 Orchestrator 按 `references/test-author-prompt.md` 模板填写、传给主笔子 agent 的完整 prompt 文件；每目标每层级独立一份，留档供审计。
- `.review/goal-<G>-round-<R>.json` 是阶段 1 某目标某轮的**汇总评审文件**：各层级评审 agent 各自产出 findings，由 Orchestrator 合并为一个 JSON 后落地；`<G>` 为目标编号（1 起），`<R>` 为该目标内轮次（1 起）。

---

## 宿主无关与适配

本 skill 的 SKILL.md 与本手册使用**抽象能力词**，不绑定任何具体 CLI 或工具：

| 抽象能力 | 执行时映射 |
|---|---|
| 起独立子 agent | 见 `references/host-adapter.md` 当前宿主映射 |
| 宿主提问工具 | 见 `references/host-adapter.md` 当前宿主映射 |
| 跑命令 / 运行单元·集成测试 | 见 `references/host-adapter.md` 当前宿主映射 |
| 宿主浏览器能力 / UI 执行 | 见 `references/host-adapter.md` 当前宿主映射 |
| 读写状态文件 | 见 `references/host-adapter.md` 当前宿主映射 |

**全程不调外部 CLI。** 本 skill 不调用 `codex exec`，不调用 `claude -p`，不跨工具调任何外部 CLI。写测试、跑测试、审测试全部通过当前宿主自身的原生子 agent 能力完成（见 `references/host-adapter.md` 「说明」章节）。

**同模型独立性靠机制保证，不靠模型差异。** 主笔子 agent（Author）与评审子 agent（Reviewer）使用同一底层模型，独立性通过以下三点保障（见 `references/host-adapter.md` 「写⊥审独立性约束」章节）：

1. **不同实例**：Author 与 Reviewer 必须是在不同调用时间点、通过不同子 agent 启动的独立实例；严禁在同一子 agent 会话中先写后审。
2. **不继承上下文**：Reviewer 启动时全新上下文，prompt 中**不传入** Author 的对话历史或中间思考；Reviewer 只能看到工件本身（测试代码 diff + 真实运行结果 + 矩阵条目 + 上轮 findings）。
3. **Reviewer 无写权限**：Reviewer 子 agent 只能输出评审 JSON，不能直接修改任何文件。

---

## 阶段 0：测试范围规划 + 人类检查点①

完整的阶段 0 执行指引见 `references/scope-planning.md`。本章仅描述 Orchestrator 的编排步骤与关键命令，不重复文件中的详细规则。

### 环境检查与 worktree 建立

在任何子 agent 启动前，Orchestrator 先执行以下环境检查：

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

命令执行成功后，后续所有测试代码**仅在 `$WT`（worktree）内编写**，不在主干上直接修改。

### 调研与产 `scope-input-summary.md`

Orchestrator 亲自读 DESIGN.md、实现代码、dev-log（见 `references/scope-planning.md` 「调研输入」章节），将关键摘要写入：

```
$REPO_ROOT/docs/test/<feature>/scope-input-summary.md
```

格式见 `references/scope-planning.md` 「调研输出格式」章节。

### 派子 agent 产 `test-matrix.md`

启动**产矩阵子 agent**（Author 角色，全新上下文，`general-purpose` 类型），prompt 中显式传入：

- `scope-input-summary.md` 的绝对路径
- `assets/test-matrix-template.md` 的绝对路径
- 矩阵结构要求（含「超出设计的补充项」列、dev-log 标注规则；见 `references/scope-planning.md` 「产测试矩阵」章节）

子 agent 完成后，Orchestrator 校验 `test-matrix.md` 存在且非空，再进入下一步。

### 派独立子 agent 做范围对抗

启动**范围评审子 agent**（Reviewer 角色，另起全新上下文，不传入 Author 的对话历史），传入：

- `scope-input-summary.md` 的绝对路径（实现代码指针来源）
- `test-matrix.md` 的绝对路径（被审对象）
- `assets/review-schema.json` 的绝对路径
- 范围评审规则（见 `references/scope-planning.md` 「范围对抗」章节；category 主要为 `coverage-gap`）

Reviewer 产出评审 JSON，Orchestrator 落地为：

```
$REPO_ROOT/docs/test/<feature>/.review/scope-review-round-<R>.json
```

随后执行**输出校验**（见 `references/adversarial-core.md` 「输出校验」章节）。若校验失败，触发「失败兜底」章节处理。

对所有 `coverage-gap` 类 blocker/major finding，委派新 Author 子 agent 实例补全矩阵，再委派新 Reviewer 子 agent 实例进行下一轮，直至收敛（K=2 / M=5）或触发上交人类（见 `references/adversarial-core.md` 「终止规则机制」章节）。

### 向人类报告并等待确认

通过宿主提问工具向人类报告：

1. **矩阵摘要**：测试目标清单（共 N 个）、各目标各层级适用情况、超出设计补充项数量及分类。
2. **范围对抗结论**：共经历 R 轮，最终 verdict 与 summary，仍存在争议或未决的 finding（若有）。
3. **执行环境确认**：worktree 路径（`$WT`）与分支名（`test/<feature>`）、迭代阈值 K=2/M=5、UI/E2E 降级策略（dev server 起不来 → 标 `unexecuted` + 移入 `open_questions`，不伪造绿）。
4. **人类裁决项（若有）**：列出所有仍有争议的矩阵条目及分歧描述，请人类给出最终决策。

**等待人类确认后**，Orchestrator 将裁决结果合并入 `test-matrix.md`，在文件头部写入冻结时间戳和人类确认签字，将最终版本提交至隔离分支。**矩阵冻结后不再修改**，除非人类发起新的范围调整请求。

---

## 阶段 1：逐测试目标串行迭代

以 `test-matrix.md` 中的每个测试目标（行）为单元，**目标间严格串行**：当前目标达到 `complete` 或触发上交人类后，才进入下一个目标。

对当前目标 `<G>`，执行以下子步骤：

### 1a 主笔：各层级独立子 agent

对该目标每个**适用**的层级（单元 / 集成 / 功能 / UI），各自独立起一个主笔子 agent：

1. Orchestrator 按 `references/test-author-prompt.md` 模板填写 prompt，替换所有 `<...>` 占位符（测试目标与验收点、本层级、DESIGN 相关章节、实现代码指针、worktree 路径 `$WT`、上一轮 findings；首轮上一轮留空）。
2. 将填写后的 prompt 落地为 `.author/goal-<G>-layer-<层级>-prompt.md`。
3. 通过宿主子 agent 能力，以该文件内容为 prompt 启动独立主笔子 agent（全新上下文，拥有 `$WT` 内的读写权限，**不得修改 worktree 外任何文件，不得修改实现源码**）。
4. 子 agent 在 `$WT` 内写测试，运行单元/集成层级的测试，回报测试文件列表 + 用例覆盖矩阵 + 测试命令与退出码 + 疑似实现 bug 清单 + 仍存疑点（格式见 `references/test-author-prompt.md` 「回报格式」章节）。

各层级子 agent 之间不共享上下文，各自独立完成写-跑-回报。

### 1b 宿主执行：Orchestrator 亲自复跑

主笔子 agent 回报后，**Orchestrator 亲自复跑**当前目标全部已写测试，作为独立验证，防止主笔误报：

- **单元 / 集成层级**：使用宿主命令执行能力（见 `references/host-adapter.md`）在 `$WT` 内运行测试命令，记录退出码和输出。
- **功能层级**：视环境是否能起 dev server；能起则执行并记录真实结果；否则按 UI 层级处理。
- **UI / E2E 层级**：使用**宿主浏览器能力**（见 `references/host-adapter.md`；在 Claude Code 下为 `preview_*` 系列工具，包括 `preview_start` / `preview_eval` / `preview_snapshot` / `preview_screenshot` / `preview_console_logs` 等）驱动执行。若 dev server **起不来**，或宿主无浏览器驱动：
  - 相关用例在状态文件中标记为 `unexecuted`（而非 `passed` 或 `skipped`）。
  - 当轮评审 JSON 的 `open_questions` 中记录：无法执行的原因、缺失的环境条件、需人类介入验证的具体项目。
  - **绝不伪造绿色结果**（见 `references/host-adapter.md` 「降级与诚实」章节及 `references/adversarial-core.md` 反作弊纪律第②条）。

Orchestrator 将复跑结果（命令 + 退出码 + 通过/失败/`unexecuted` 降级）汇总，作为喂给评审子 agent 的「Orchestrator 的真实运行结果」。

### 1c 独立评审：各层级独立子 agent

对该目标当前轮次 `<R>` 启动**独立评审子 agent**（Reviewer 角色），每个适用层级各起一个实例（全新上下文，无写权限）：

prompt 按 `references/test-reviewer-prompt.md` 模板填写，传入：

- 测试目标与验收点
- 本目标各层级测试 diff（主笔本轮新增或修改的所有测试代码）
- **Orchestrator 的真实运行结果**（步骤 1b 的复跑结论；评审者基于此评审，不接受主笔自行声称的结果）
- DESIGN / 矩阵相关条目
- 上一轮 findings（首轮留空；复评轮传入上轮 `.review/goal-<G>-round-<R-1>.json`）

各层级 Reviewer 各自产出符合 `assets/review-schema.json` 的评审 JSON。

**Orchestrator 汇总**：将各层级评审 findings 合并为该目标该轮**一个**汇总文件，落地为：

```
$REPO_ROOT/docs/test/<feature>/.review/goal-<G>-round-<R>.json
```

随后对该汇总文件执行**输出校验**（见 `references/adversarial-core.md` 「输出校验」章节）。校验失败则触发「失败兜底」章节处理，禁止进入下一步。

### 1d bug 分流 + 收敛判定

对汇总评审文件执行以下命令（`$WT` 和 `$REPO_ROOT` 已在阶段 0 环境检查中设置）：

```bash
SKILL_DIR="$REPO_ROOT/skills/multi-agent-test-iteration"
RD="$REPO_ROOT/docs/test/<feature>/.review"
# 抽 real-bug 追加到 bug-report(Orchestrator 据此回填 bug-report.md)
python3 "$SKILL_DIR/../_adversarial-core/filter-findings.py" "$RD/goal-<G>-round-<R>.json" --only-category real-bug
# 产排除 real-bug 的 quality 版,喂收敛
python3 "$SKILL_DIR/../_adversarial-core/filter-findings.py" "$RD/goal-<G>-round-<R>.json" --exclude-category real-bug > "$RD/goal-<G>-round-<R>.quality.json"
python3 $SKILL_DIR/../_adversarial-core/progress-check.py --rounds "$RD"/goal-<G>-round-*.quality.json --k 2 --m 5   # 分歧加 --disagreement
```

**real-bug 分流**：`filter-findings.py --only-category real-bug` 产出的条目由 Orchestrator 逐条追加写入 `bug-report.md`，按 category/severity 分类记录；`real-bug` **不计入收敛计算**（见 `references/test-reviewer-prompt.md` 「category 枚举表格」章节），防止实现 bug 多寡导致测试质量迭代死锁。

**收敛判定**：`progress-check.py` 对仅含测试质量 findings 的 `.quality.json` 文件计算收敛：

- 输出 `complete` → 该目标通过对抗评审，收尾记录至 `test-log.md`，进入下一个测试目标。
- 输出 `continue` → 回到步骤 1a，让主笔子 agent 按本轮 findings 修订/补写测试（复评轮 prompt 中传入上轮评审 JSON）。
- 输出 `escalate:*` → 停止该目标自动迭代，携带完整状态（所有轮次评审 JSON + 当前测试文件 + 分歧摘要）上交人类决策。

---

## 阶段 2：汇总 + 人类检查点②

当 `test-matrix.md` 中**全部测试目标**均达到 `complete` 后，Orchestrator 通过宿主提问工具向人类提交最终报告：

### 测试报告内容

1. **矩阵覆盖汇总**：各测试目标 × 各层级的覆盖状态（已完成 / 上交人类 / `unexecuted` 降级）；`unexecuted` 条目须列明无法执行的原因和环境缺失条件。
2. **各层级运行结果汇总**：每个目标各层级最终轮次的测试命令、退出码、通过/失败/`unexecuted` 降级结论。
3. **`bug-report.md` 全文**：本次测试发现的全部 `real-bug` 清单，按 category 和 severity 分类，含 anchor 和发现轮次。
4. **测试质量结论**：各目标最终收敛状态（正常收敛 / K 触发上交 / M 触发上交 / 争议上交）；未完成目标的原因和当前状态。
5. **未执行降级项清单**：所有标记为 `unexecuted` 的用例及其 `open_questions` 记录，供人类决定后续补测策略。

### 后续处理决策（人类决定，本 skill 不自动执行）

本 skill **不自动修复 bug，不自行合并 `test/<feature>` 分支**。人类在查看报告后自行选择：

- 将 `bug-report.md` 中的 `real-bug` 条目交回 dev agent（或手动）修复实现，修复后可重新触发本 skill 对受影响目标复测。
- 接受当前 bug 状态（作为已知缺陷备案）。
- 手动审查并决定是否合并 `test/<feature>` 分支至主干或其他目标分支。

---

## 失败兜底

以下情形触发相应兜底处理，严格按优先级执行，**禁止静默放行**。

### 主笔子 agent 失败或返回空

若主笔子 agent 未产出回报、产出内容为空、或宿主子 agent 调用本身返回错误：

1. **至多重试一次**（见 `references/adversarial-core.md` 「看门狗 / 存活监控」章节的重试策略），重试前记录失败的退出码和 stderr。
2. 重试仍失败 → **停止当前目标**，携带失败详情（失败时间、退出码、stderr、当前状态文件路径）上交人类，不得进一步重试或绕过，不得将失败结果当作通过继续走流程（见 `references/adversarial-core.md` 反作弊纪律第③条）。

### 评审子 agent 不产出 / 不可解析 / 不合 schema

若评审子 agent 未产出 JSON、产出的 JSON 无法解析、或 JSON 不符合 `assets/review-schema.json` 校验：

1. **立即停止**该目标当前轮次（不重试评审）。
2. **禁止**以"评审静默 = 没有问题 = 通过"为由推进迭代（见 `references/adversarial-core.md` 反作弊纪律第①条）。
3. **禁止**进入下一轮或将当前状态合并至收敛计算。
4. 携带失败详情（评审 agent 原始输出、校验错误信息、当前状态文件路径）上交人类，**绝不静默当通过**。

### UI / E2E 起不来

若 dev server 启动失败，或宿主浏览器能力（`preview_start` 等）返回非零退出码：

1. 相关用例在状态文件中标记为 `unexecuted`，**不标 `passed`，不标 `skipped`**。
2. 在当轮评审 JSON 的 `open_questions` 中记录：无法执行的原因、缺失的环境条件、需人类介入验证的具体项目。
3. **绝不伪造执行结果**（见 `references/host-adapter.md` 「降级与诚实」章节及 `references/adversarial-core.md` 反作弊纪律第②条）。
4. 继续对已成功执行的层级（单元 / 集成）执行评审和收敛判定；`unexecuted` 条目在阶段 2 报告中单独列明，由人类决定后续补测策略。

> **反作弊纪律与输出校验的完整定义**见 `references/adversarial-core.md` 「反作弊纪律」与「输出校验」章节；本章节仅描述在失败情形下的触发入口和处理路径。
