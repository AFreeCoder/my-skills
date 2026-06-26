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

## 角色模型(宿主无关)

本 skill 由三个角色协作完成测试工作。所有角色均通过当前宿主的原生子 agent 能力启动，**不调用任何外部 CLI**（不调用 `codex exec`，不调用 `claude -p`）。宿主适配映射见 `references/host-adapter.md`。

| 角色 | 类型 | 读写权限 | 职责 |
|---|---|---|---|
| **Orchestrator** | 宿主主 agent（当前会话） | 全权 | 编排流程、读写状态文件、复跑测试、bug 分流、向人类汇报 |
| **Test Author** | 宿主子 agent（工作区写） | 仅 worktree 内读写，不得修改实现源码 | 按测试目标与层级写测试、跑测试、回报结果与疑似 bug |
| **Reviewer** | 宿主子 agent（独立全新上下文，无写权限） | 只读 | 输出结构化评审 JSON，挑测试质量（漏测/假绿/未执行），不修改任何文件 |

**对抗关系说明：**

- **对抗对象 = 实现**：Test Author 以"尽力证伪实现"为目标写测试，而非让测试通过。
- **迭代对象 = 测试质量**：每轮 Reviewer 审的是测试本身是否充分、诚实、有效，而非审实现是否正确。
- **bug 只报不修**：测试中发现的实现 bug 由 Orchestrator 归入结构化 bug 清单，交人类处置；本 skill 不修改实现代码。

**同模型独立性三机制（写⊥审独立性）：**

1. **不同实例**：Author 与 Reviewer 必须是不同调用时间点、通过不同子 agent 启动的独立实例；严禁在同一子 agent 会话中先写后审。
2. **不继承上下文**：Reviewer 启动时全新上下文，prompt 中不传入 Author 的对话历史；Reviewer 只能看到工件本身（测试代码 diff + 真实运行结果 + 矩阵条目 + 上轮 findings）。
3. **Reviewer 无写权限**：Reviewer 只能输出评审 JSON，不能直接修改任何文件。

详细宿主适配规则与工具映射见 `references/host-adapter.md`。

---

## 何时使用 / 何时不用

### 适用场景

- 已有**冻结的 DESIGN.md** 与对应实现代码，需要做系统性测试覆盖。
- 需要对当前功能做单元/集成/功能/UI 层级的完整验证，或做回归测试。
- 用户明确表达"测一下有没有 bug""按设计文档测试并补充""做功能/集成/UI 测试""多 agent 测试评审"等意图。

### 不适用场景

- **尚无冻结设计**：DESIGN.md 未冻结时不可启动；请先用 `multi-agent-design-review` 完成设计评审并冻结。
- **想改实现修 bug**：本 skill 只报不修，修复实现应转交 `multi-agent-dev-iteration` skill。
- **仅一两行小改直接手测**：改动极小、无需系统性覆盖时，直接手测即可，不必启动多 agent 流程。

---

## 核心原则

本 skill 的对抗式内核完整定义见 `references/adversarial-core.md`，以下为对测试场景的关键约束：

**反作弊纪律：**

- **禁止伪造绿色结果**：所有"已通过"的测试必须有真实退出码和产物为证；任何未实际执行的用例不得标记为 `passed` 或 `skipped`——必须标 `unexecuted`。
- **UI 起不来如实降级**：若 dev server 无法启动，相关用例标 `unexecuted`，在评审 JSON 的 `open_questions` 中记录原因，绝不伪造执行结果。
- **禁止将评审静默当通过**：Reviewer 未产出 / JSON 不合 schema / 无法解析，均视为评审失败，立即停止并上报。
- **不私自降级 blocker/major**：主笔不得自行将 Reviewer 标注的 blocker/major 降为 minor；有分歧则上交人类裁决。

**文件驱动协作：** 所有跨 agent 状态均通过文件传递，子 agent 启动时以绝对路径显式注入所需文件，不依赖会话内记忆。

**分级评审：** finding 按 blocker/major/minor 三级管理，严格按 `references/adversarial-core.md` 的净进展定义计算收敛。

**输出校验：** 每轮评审产出后，Orchestrator 必须对照 `assets/review-schema.json` 执行 schema 校验，校验失败则拒绝该评审并上报。

---

## 工作流

完整执行细节见 `references/orchestration.md`。以下为三阶段概览：

### 阶段 0：测试范围规划 + 人类检查点①

详细执行指引见 `references/scope-planning.md`。

1. **环境检查**：验证 DESIGN.md 已冻结，工作区干净，建立 `test/<feature>` worktree。
2. **调研**：Orchestrator 亲自读 DESIGN.md、实现代码、dev-log，将关键摘要写入 `scope-input-summary.md`。
3. **产矩阵**：委派产矩阵子 agent（Author 角色），以 `scope-input-summary.md` 和 `assets/test-matrix-template.md` 为输入，产出 `test-matrix.md`（行=测试目标，列=单元/集成/功能/UI，含「超出设计的补充项」列）。
4. **范围对抗**：委派独立范围评审子 agent（Reviewer 角色），按 `assets/review-schema.json` 产出结构化评审 JSON（`scope-review-round-<R>.json`），主要 category 为 `coverage-gap`；有 blocker/major 则驱动 Author 补全矩阵，循环至收敛（K=2/M=5）。
5. **人类检查点①**：报告矩阵摘要、对抗结论、执行环境、裁决项；等待人类确认后冻结矩阵。

### 阶段 1：逐测试目标串行迭代

以 `test-matrix.md` 中每个测试目标为单元，**目标间严格串行**。对当前目标执行以下循环（详见 `references/orchestration.md`）：

1. **1a 主笔**：Orchestrator 按 `references/test-author-prompt.md` 模板填写 prompt（含测试目标、层级、DESIGN 章节指针、实现代码指针、worktree 路径、上轮 findings），落地为 `.author/goal-<G>-layer-<层级>-prompt.md`，启动独立主笔子 agent 写测试并跑测试，回报结果与疑似 bug 清单。
2. **1b 宿主复跑**：Orchestrator 亲自复跑全部已写测试，作为独立验证，防止主笔误报。UI/E2E 层级使用宿主浏览器能力；起不来则标 `unexecuted`，绝不伪造绿。
3. **1c 独立评审**：启动独立评审子 agent（Reviewer 角色），按 `references/test-reviewer-prompt.md` 模板传入 diff + Orchestrator 复跑结果 + 矩阵条目 + 上轮 findings；各层级独立产出评审 JSON，Orchestrator 汇总落地为 `.review/goal-<G>-round-<R>.json`，执行 schema 校验。
4. **1d bug 分流 + 收敛判定**：`real-bug` 类 finding 追加写入 `bug-report.md`（bug 只报不修）；排除 `real-bug` 后对仅含测试质量 findings 的 `.quality.json` 执行收敛判定：`complete` 则进入下一目标，`continue` 则回到 1a，`escalate:*` 则携带完整状态上交人类。

### 阶段 2：汇总 + 人类检查点②

全部测试目标达到 `complete` 后，向人类提交最终报告：矩阵覆盖汇总、各层级运行结果、`bug-report.md` 全文、测试质量结论、`unexecuted` 降级清单。本 skill 不自动修复 bug，不自行合并分支，后续处置由人类决定。

---

## 终止条件

**阈值：K=2（连续无净进展轮数上限）/ M=5（绝对迭代轮数上限）**，按测试目标独立计算。

**目标 complete 的定义 = 测试质量达标（Reviewer approve），而非"所有测试都绿"。**

- 测试正确地红（发现了实现 bug）= 测试质量达标，可 complete；bug 入清单，不阻塞该目标收尾。
- 测试假绿（主笔伪造或漏测）= 不达标，继续迭代。
- `unexecuted` 降级条目不参与 approve 判定，在阶段 2 报告中单独处置。

**终止规则完整机制**（净进展定义、软规则上交、硬上限强制停止）见 `references/adversarial-core.md` 「终止规则机制」章节。

**real-bug 不计入收敛计算**：实现 bug 多寡不影响测试质量迭代收敛，防止 bug 数量导致迭代死锁。

---

## 输出

| 产物 | 路径 | 说明 |
|---|---|---|
| 测试代码 | `test/<feature>` 分支（worktree） | Author 子 agent 在隔离 worktree 中写入，不污染主干 |
| 测试矩阵 | `docs/test/<feature>/test-matrix.md` | 人类确认冻结后的范围基准 |
| 运行日志 | `docs/test/<feature>/test-log.md` | 每个目标收尾时追加，记录最终轮次结果 |
| bug 清单 | `docs/test/<feature>/bug-report.md` | 结构化实现 bug 清单，按 category/severity 分类，供人类处置 |
| 测试结论 | 阶段 2 人类报告 | 覆盖汇总 + 运行结论 + `unexecuted` 降级清单 |

**bug 衔接**：`bug-report.md` 交人类决定是转交 `multi-agent-dev-iteration` 修复、作为已知缺陷备案，还是触发受影响目标复测；本 skill 不自动修复，不自动合并分支。

---

## 引用文件

以下文件是本 skill 的执行依据，Orchestrator 在运行前须完整读取各文件：

| 文件 | 说明 |
|---|---|
| `references/orchestration.md` | Orchestrator 执行手册：状态载体、阶段 0/1/2 编排步骤、失败兜底处理 |
| `references/host-adapter.md` | 宿主适配表：抽象能力词到当前宿主工具的映射，写⊥审独立性约束，降级与诚实规则 |
| `references/scope-planning.md` | 阶段 0 完整指引：调研输入、产测试矩阵、范围对抗、人类检查点①协议 |
| `references/test-author-prompt.md` | Test Author 子 agent 的 prompt 模板：占位符定义、回报格式、禁止事项 |
| `references/test-reviewer-prompt.md` | Reviewer 子 agent 的 prompt 模板：category 枚举表格（含 real-bug 定义）、评审规则 |
| `references/adversarial-core.md` | 对抗式迭代内核母本：评审分级、终止规则、反作弊纪律、看门狗、文件驱动协作、输出校验 |
| `assets/review-schema.json` | 评审 JSON 的 JSON Schema 定义，所有评审输出须通过此 schema 校验 |
| `assets/test-matrix-template.md` | 测试矩阵 Markdown 模板，产矩阵子 agent 按此格式输出 |
| `assets/test-log-template.md` | 运行日志模板，Orchestrator 在每个目标收尾时按此格式追加记录 |
| `assets/bug-report-template.md` | bug 清单模板，Orchestrator 在每轮 real-bug 分流后按此格式追加 |
