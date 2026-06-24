---
name: multi-agent-dev-iteration
description: >-
  开发阶段的多智能体对抗式协作:吃冻结的 DESIGN.md + writing-plans 计划,逐 step
  由 Codex 在隔离 worktree(workspace-write 降权)里 TDD 主笔实现、独立 Claude 只读
  评审,收敛判定+硬上限迭代到每步无 blocker/major 且单测绿,产出实现代码(隔离分支)
  + dev-log,合回主干前交人类。当用户已有冻结设计与实现计划、要进入编码,并表达
  "按设计实现""让 Codex 写代码 Claude 评审""TDD 落地""逐步实现并评审""开始写代码""开始实现"时触发。
---

## 角色模型

| 角色 | 身份 | 权限 | 职责 |
|------|------|------|------|
| **Orchestrator** | Claude 主 agent（唯一对接用户） | 读写（协调层） | 驱动流程、收敛判定、人类检查点交接 |
| **Author** | Codex 子 agent | worktree + workspace-write 降权 | TDD 主笔实现、运行单测、修复 blocker |
| **Reviewer** | 独立 Claude 评审子 agent | 只读（不访问工作目录写权限） | 结构化评审输出，不参与修改 |

> 权限说明：相对于设计评审 skill（Claude 主笔、Codex 只读评审），本 skill **反转了可写角色**——Codex 持有代码写权限，Claude 评审侧为只读，确保写与审严格正交。

---

## 何时使用 / 何时不用

**使用场景**
- 已有冻结的 `DESIGN.md`（经设计评审 skill 通过）和 writing-plans 产出的实现计划
- 准备正式进入编码阶段，需要 TDD + 对抗式评审保障质量

**不使用场景**
- 尚无冻结设计 → 先走设计评审 skill（`multi-agent-design-review`）
- 想修改或推翻设计 → 本 skill 不重新设计，拒绝处理设计分歧
- 系统性集成/回归测试 → 交由后续测试 skill 处理

---

## 核心原则

详细机制见 `references/adversarial-core.md`，要点如下：

- **写⊥审**：Author 与 Reviewer 角色严格隔离，Reviewer 无代码写权限，防止互相污染。
- **文件驱动**：所有决策通过结构化文件（评审报告、dev-log）传递，不依赖对话上下文。
- **分级处理**：发现项按 blocker / major / minor 三级处理；Orchestrator 不得私自将 blocker/major 降级，主笔(Codex)亦不得单方面调低 finding severity——分歧一律上交人类。
- **反作弊/看门狗**：超出硬上限时强制上交人类，不允许无限迭代掩盖根本问题。
- **隔离执行**：Codex 始终在隔离 worktree 的独立分支上操作，workspace-write 降权，不直接触碰主干。
- **人类检查点**：流程头部（确认输入冻结）和尾部（合并前）各设一个强制人类检查点。

---

## 工作流

细节见 `references/orchestration.md`，阶段概览：

- **阶段 0 — 输入核验**：Orchestrator 确认 DESIGN.md 已冻结、计划步骤清单完整；**人类检查点①**。
- **阶段 1 — 隔离环境准备**：创建 worktree + 功能分支，Author（Codex）workspace-write 降权就位。
- **阶段 2 — 逐步 TDD 实现**：按计划 step 顺序，Author 先写测试、再写实现，直到单测绿。
- **阶段 3 — 独立评审**：Reviewer（独立 Claude）只读拉取当前 step 产物，输出结构化评审报告（schema 见 `assets/review-schema.json`）。
- **阶段 4 — 收敛迭代**：Orchestrator 按收敛判定规则裁定 GO / 重写 / 上交人类；循环直至该 step 通过或触达硬上限。
- **阶段 5 — 合并检查点**：所有 step GO 后，**人类检查点②**，由人类决定是否合回主干。

---

## 终止条件

- **GO**：无 blocker/major 且单测绿 → 该 step 完成，进下一 step。
- **上交人类**：在**单个 step 内**连续 K = 2 轮无净进展、或达到该 step 的硬上限 M = 5 轮、或主笔与评审存在持续分歧 → Orchestrator 停止该 step、输出上交报告等待人类干预。
- **阈值按 step 分别计，step 之间互不累加**；机制详见 `references/adversarial-core.md`。
- **整体**：所有 step 均 GO 才进入合并检查点②。

---

## 输出

| 产物 | 位置 |
|------|------|
| 实现代码 | 隔离 worktree 的功能分支 |
| 开发日志 | `docs/dev/<feature>/dev-log.md`（模板：`assets/dev-log-template.md`） |
| 每 step 评审报告 | 嵌入 dev-log，结构遵循 `assets/review-schema.json` |
| 终止判定 | GO（进入合并检查点）或上交人类报告 |

---

## 引用文件

- `references/orchestration.md` — 完整阶段流程与 Orchestrator 决策树
- `references/codex-author-prompt.md` — Author（Codex）角色的标准提示模板
- `references/claude-review-prompt.md` — Reviewer（独立 Claude）角色的只读评审提示模板
- `references/adversarial-core.md` — 对抗式协作核心原则：分级、反作弊、硬上限、终止机制
- `assets/review-schema.json` — 评审报告结构化输出 schema
- `assets/dev-log-template.md` — 开发日志模板
