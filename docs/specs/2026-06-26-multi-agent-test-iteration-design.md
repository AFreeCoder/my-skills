# 详细设计 · `multi-agent-test-iteration`(测试阶段对抗式协作 skill)

> 状态:草案(待用户复核)· 日期:2026-06-26 · 阶段:brainstorming 产出的设计 spec
> 本 spec 只定**测试 skill**(套件第三块);薄编排层是后续独立 spec。
> 上游参考:`multi-agent-design-review`(第一块)、`multi-agent-dev-iteration`(第二块,见 `docs/specs/2026-06-24-multi-agent-dev-iteration-design.md`)。

## 1 背景与目标

终极目标:把 `multi-agent-design-review` 扩展成一整套 **设计 → 开发 → 测试** 的对抗式多智能体流水线,三个**独立可组合**的 skill + 薄编排层,产物逐级交接(`DESIGN.md` → 实现代码 → 测试验证)。三块共享同一套"怎么评审、怎么分级、什么时候停、怎么防作弊"的**对抗式迭代内核**(`_adversarial-core` 母本 + 同步副本)。

本 spec 聚焦**第三块:测试 skill**。它吃冻结的 `DESIGN.md` + 实现代码,对当前开发内容做**单元 / 功能 / 集成 / UI** 四类测试,产出测试代码 + 测试运行报告 + 实现 bug 清单。

**与前两块的两点根本差异**(详见 §4):

1. **对抗对象 = 实现,迭代对象 = 测试质量**。前两块迭代的工件是"设计文档 / 实现代码";本 skill 迭代的工件是**测试本身**——测试方扮演攻击者去证伪实现,评审方挑"测试够不够狠、有没有造假漏测"。测出的实现 bug **只报不修**(回开发阶段处理),不在本 skill 内改实现。
2. **宿主无关 + 全宿主子 agent**。前两块绑定具体外部 CLI(design 用 `codex exec`、dev 用 Codex worktree);本 skill **不调任何外部 CLI**,写 / 跑 / 审全部由**当前宿主自身的子 agent 能力**完成。换取最大稳定性(测试需大量真实运行,宿主原生工具远比跨 CLI 沙箱可靠)与通用性(任意支持子 agent 的 agent 工具——Claude Code、Codex 桌面端等——开箱即用)。

## 2 已确认决策

| # | 决策 | 取值 |
|---|---|---|
| 1 | 对抗 / 迭代对象 | **对抗实现、迭代测试质量**;测出的实现 bug **只报不修**(产结构化清单交人类) |
| 2 | 迭代单元 | **按"测试目标 / 功能场景"切**,每个目标内纵向覆盖适用的单元 / 功能 / 集成 / UI 层级 |
| 3 | 目标间执行 | **串行逐目标**(对齐 dev 逐 step);目标内各层级由**独立子 agent** 分别完成与评审 |
| 4 | 执行架构 | **宿主无关 + 全宿主子 agent**,不调外部 CLI;角色均为"宿主子 agent" |
| 5 | 评审 | **保留独立评审**(独立子 agent、只读、不继承主笔上下文),聚焦测试质量层 |
| 6 | UI / E2E 执行 | 用**宿主原生浏览器能力**(Claude Code 下 `preview_*`);**起不来降级标记"已写未执行",绝不伪造绿** |
| 7 | 阶段 0 范围规划 | 调研 → 子 agent 产测试矩阵(含超出设计的补充项)→ 独立评审做**范围对抗** → 人类检查点确认 |
| 8 | 输入前提 | **冻结 `DESIGN.md` + 实现代码必需**;`dev-log` / 走过 dev-iteration **可选**(有则增强) |
| 9 | 共享内核 | 复用 `_adversarial-core` 母本(分级 / schema / `progress-check.py` / 反作弊 / 文件驱动 / 输出校验);`category` 做测试特化 |
| 10 | 收敛阈值 | **K=2(连续无净进展轮数上限)/ M=5(硬上限)**,按测试目标分别计 |
| 11 | 命名 | `multi-agent-test-iteration` |

## 3 范围与边界

**做什么**:吃冻结的 `DESIGN.md` + 实现代码(+ 可选 `dev-log`),先规划测试范围(不局限于设计文档),再逐测试目标串行迭代——子 agent 写该目标各层级测试、宿主真实执行、独立子 agent 评审测试质量、收敛判定;产出测试代码(隔离分支)+ 测试运行报告 + 实现 bug 清单,交人类拍板。

**不做**:

- **不改实现、不修 bug**:测出的实现缺陷归档为结构化清单上交人类,由人类决定回 dev-iteration 修 / 接受为已知问题 / 手动修;本 skill 不触碰实现代码。
- **不重新设计**:`DESIGN.md` 已冻结;发现设计本身有问题 → 作为 finding 上交人类,不私自改设计。
- **不自行合并测试分支**:由人类检查点②决定。
- **不替代 dev 的 TDD 单测**:dev-iteration 已在每个 step 写过单元测试;本 skill 的"单元"层级是**审视并补强**(补 dev 漏掉的边界 / 异常 / 设计外路径),而非从零重写。

## 4 角色模型(宿主无关)

| 角色 | 谁 | 能力位 | 关键约束 |
|---|---|---|---|
| **Orchestrator(编排者)** | 宿主主 agent(任意工具) | 读写 + **执行** | 唯一与用户交互;编排 / 循环 / 收敛判定 / 检查点把关 / 分级争议裁决;**亲自真实运行测试**(含用宿主浏览器能力跑 UI);bug 分流归档 |
| **Test Author(测试主笔)** | 宿主子 agent | 工作区写 | 在隔离 worktree 内写某测试目标某层级的测试、跑能在子 agent 内跑的(单元 / 集成);尽力**证伪实现**;不改实现代码 |
| **Reviewer(评审)** | **独立**宿主子 agent(全新上下文) | 只读 | 只喂测试 diff + 运行结果 + DESIGN/矩阵相关条目;结构化输出 findings;评审**测试质量** + 复核 bug 真伪;**只读不改** |

**"写 ⊥ 审"在同模型下如何保证独立性**:前两块靠跨实体(Claude vs Codex);本 skill 全为宿主子 agent,独立性靠三条机制——① Author 与 Reviewer 是**不同的子 agent 实例**;② Reviewer **不继承** Author 的会话上下文(全新启动,只读传入的文件);③ Reviewer **不获授工作区写权限**。主笔会爱上自己写的测试,独立评审者以全新视角去捅破——这是同模型 + 独立上下文仍能提供对抗性的根据。

**为何不调外部 CLI**:测试要大量真实运行(起 server、起浏览器、跑各类 runner)。dev-iteration 实战已实证 Codex 沙箱在 worktree 内 `next build` 因 symlink node_modules 失败、跨 CLI 长任务易被静默后台化误判。改用宿主原生执行能力(`Bash` / 浏览器工具)消除这一整类不稳定。

**宿主适配映射表**(落 `references/host-adapter.md`):SKILL 正文只用抽象词"宿主子 agent""宿主提问工具""宿主浏览器能力""宿主命令执行",由映射表给各宿主的具体实现:

| 抽象能力 | Claude Code | Codex 桌面端 / 其他 |
|---|---|---|
| 起子 agent | `Agent` 工具(`general-purpose`) | 该工具的子 agent / 子任务机制 |
| 向用户提问 | `AskUserQuestion` | 该工具的提问 / 确认机制 |
| 跑命令 / 测试 | `Bash` | 该工具的 shell 执行 |
| 跑 UI / E2E | `preview_*`(start/snapshot/screenshot/eval…) | 该工具的浏览器驱动;无则降级 |

Author / Reviewer 都不直接与用户交互;所有澄清与拍板由 Orchestrator 出面。

## 5 工作流

`<feature>` = kebab-case 短名,`<G>` = 测试目标序号,`<R>` = 该目标的评审轮次。

### 阶段 0 — 测试范围规划 + 人类检查点①(进测试前,强制前置)

用户最强调的一步:**先读文档定范围,且不局限于设计文档**。范围漏了,后面测得再细也是空的。

1. **预检**:① 宿主子 agent 能力可用;② `DESIGN.md` 存在且标"已冻结";③ 实现代码可定位(分支 / 工作区);④ 工作区 git 干净。任一不满足 → 停止并告知,不伪造。`dev-log` 存在则一并读入(增强上下文),不存在不阻塞。
2. **调研**:Orchestrator(或委派调研子 agent)读 `DESIGN.md`、实现代码、`dev-log`,建立"实现了什么、怎么实现的"现状理解(给 `文件:行` 指针)。
3. **产测试矩阵**:委派子 agent 产出 `test-matrix.md`——**测试目标 × 测试层级**的二维矩阵,每格标注:验收点(怎样算测过)、适用层级(单元 / 功能 / 集成 / UI)、**「超出设计的补充项」**(DESIGN 没写但代码里存在的路径 / 边界 / 异常 / 集成点 / 回归面 / 安全面)。
4. **范围对抗**:派**独立评审子 agent**,专职挑"**漏了什么该测的**"——对照实现代码与常见失效模式,审视矩阵是否遗漏关键目标 / 层级 / 边界。结构化输出(复用 review-schema,`category` 多为 `coverage-gap`)。Orchestrator 据此补全矩阵。
5. **人类检查点①**:向人类报告测试矩阵(目标清单、各目标覆盖的层级、补充项)、隔离分支与 worktree 路径、终止规则(K=2 / M=5)、UI 执行方式与降级策略 → **人类确认范围后才开测**。范围有增删由人类拍板。

### 每个测试目标的循环(阶段 1,串行逐目标)

测试目标按矩阵顺序逐个进行,目标间不并行。**单个目标内**,各适用层级由独立子 agent 分别完成,Orchestrator 汇总为该目标该轮的评审。

- **阶段 1a · 主笔写测试**:Orchestrator 为该目标的每个适用层级派一个 **Test Author 子 agent**(独立上下文),在 worktree 内写该层级测试,跑**能在子 agent 内跑的**(单元 / 集成),回报:新增 / 修改的测试文件、测试命令、退出码与 stdout/stderr 摘要、对实现的可疑点。主笔**只写测试不改实现**。
- **阶段 1b · 宿主执行**:Orchestrator **亲自真实运行**全部测试(独立复跑 Author 的测试以防 Author 误报,呼应 dev 实战"三方交叉")。**UI / E2E 用宿主浏览器能力执行**;凡因环境(浏览器 / dev server / symlink / 端口)**无法真实执行**的,**降级标记"已写未执行"并移入评审的 `open_questions`,绝不以"退出码缺失 = 通过"伪造绿**(反作弊纪律)。采集所有层级的真实运行结果。
- **阶段 1c · 独立评审**:Orchestrator 为各层级派**独立 Reviewer 子 agent**(只读、全新上下文),喂测试 diff + **真实运行结果** + DESIGN/矩阵相关条目 + 上一轮 findings(复评轮)。评审聚焦**测试质量层**:覆盖完整性(漏测?)、测试真实性(假绿 / 未执行 / 断言无意义?)、**bug 真伪复核**(测试报红是真实现缺陷,还是测试本身写错?)。结构化输出落 `.review/`。
- **阶段 1d · bug 分流 + 收敛判定**:Orchestrator 对该轮全层级 findings 做两件事:
  - **bug 分流**:`category = real-bug` 的 finding(测试确认的真实现缺陷)抽取累积到 `bug-report.md`,**不计入测试质量收敛**(主笔不修实现,计入会死锁,见 §6/§7)。
  - **收敛判定**:对剩余**测试质量** findings 运行 `progress-check.py`(K=2 / M=5),判 `complete` / `continue` / `escalate`。`continue` 则返回阶段 1a 让主笔补 / 修测试;`complete` 则该目标收尾(记 `test-log`),进下一目标;`escalate:*` 立即停止该目标、上交人类。

### 阶段 2 — 汇总 + 人类检查点②(交付)

全部目标 `complete` 后,Orchestrator 汇总并交人类:

1. **测试报告**:各目标 × 层级的最终运行结果(命令 / 退出码 / 通过失败数 / 未执行降级项)、矩阵覆盖核对(有无遗漏目标)。
2. **实现 bug 清单** `bug-report.md`:结构化条目——复现步骤 / 期望 vs 实际 / `anchor` / severity / 关联测试用例。
3. **测试质量结论**:各目标轮次数、最终 verdict、escalate 事件、未采纳 minor(已知债务)。
4. **bug 衔接由人类决定**:回 dev-iteration 修 / 接受为已知问题 / 手动修。本 skill 不自动触发修复,不自行合并测试分支。

## 6 评审分级与 category(复用母本,测试视角)

由 Reviewer 给出,每条必须带落点(`anchor`:`test:用例名` / `file:line` / 接口 / 数据流),无落点视为无效评审。severity 通用定义复用母本;测试视角的关键认定:

- **blocker**:**测试造假 / 没真跑**(mock 掉核心路径致未验证真实行为、退出码非 0 却称通过、测试文件从未执行);核心功能 / 核心验收点**完全无测试覆盖**;测试**破坏**或误改了实现代码(越界)。
- **major**:重要失效路径 / 边界 / 异常分支未覆盖;关键集成点未验证;断言过弱形同虚设;UI 关键交互缺验证。
- **minor**:命名 / 组织 / 非关键路径轻微冗余;记入「已知债务」。

**`category` 测试特化枚举**(SKILL 在 review prompt 中约定;母本 schema 仅要求非空串):

| 值 | 含义 | 是否计入测试质量收敛 |
|---|---|---|
| `coverage-gap` | 漏测:关键路径 / 边界 / 异常 / 集成点未覆盖 | 是 |
| `fake-green` | 假绿:mock 核心路径、断言无意义、退出码非 0 却称通过 | 是 |
| `unexecuted` | 测试已写但未真实执行(含 UI 降级未跑) | 是 |
| `assertion-weak` | 断言太弱 / 不充分,通过不代表正确 | 是 |
| `flaky` | 非确定性 / 不稳定测试 | 是 |
| `test-regression` | 测试代码越界改动或破坏实现 | 是 |
| **`real-bug`** | **测试确认的真实实现缺陷** | **否(分流至 bug-report)** |

**核心区分**:`real-bug` 是测试**成功**的产出(证伪了实现),主笔无法也不应修(bug 只报不修);其余 category 是测试**自身**的质量问题,主笔要修,参与收敛。Orchestrator 在阶段 1d 据 `category` 分流。

## 7 终止规则(收敛判定 + 硬上限)

终止规则**按测试目标分别计**,复用母本机制与 `progress-check.py`(K=2 / M=5),但**收敛对象是测试质量**,语义与 dev 有一处关键不同:

- **测试目标 `complete` ≠ "所有测试都绿"**。测试可能**正确地红**(发现了实现 bug)。一个目标 `complete` 的判据是:Reviewer `verdict = approve`,即**无未解决的测试质量 blocker/major**(覆盖充分、真实执行、断言有效、无假绿),且该轮跑出的失败均已被复核归类(真 bug → 入清单 / 测试自身错 → 已修)。
- **净进展**:测试质量 blocker/major 数量减少,或 `prior_findings_status` 中有 prior 被标 `resolved`。连续 K=2 轮无净进展 → `escalate:no-progress`;达 M=5 轮 → `escalate:hard-cap`;主笔与评审就某测试质量 finding 持续分歧 → `escalate:disagreement`。
- **`real-bug` 不参与收敛**:阶段 1d 已将其从喂给 `progress-check.py` 的 findings 中剔除(分流到 `bug-report.md`),避免"主笔不修实现 → 永远 unresolved → 死锁"。
- **整体**:所有目标 `complete` 才进入阶段 2 检查点②。

## 8 状态载体(文件驱动,不依赖跨调用记忆)

- 隔离:分支 `test/<feature>` + 对应 git worktree(测试只新增测试文件,不改实现)。
- `docs/test/<feature>/test-matrix.md` — 阶段 0 的测试矩阵(目标 × 层级 + 补充项),人类检查点①确认后冻结。
- `docs/test/<feature>/test-log.md` — 跨目标 / 跨轮累积(每目标各轮 findings + 处理结论 + 运行结果 + 收敛判定)。
- `docs/test/<feature>/bug-report.md` — 实现 bug 结构化清单(`real-bug` 分流归档)。
- `docs/test/<feature>/.author/goal-<G>-layer-<层级>-prompt.md` — 喂给各 Test Author 子 agent 的 prompt。
- `docs/test/<feature>/.review/goal-<G>-round-<R>.json` — 每目标每轮汇总的结构化评审(符合 `assets/review-schema.json`)。
- 所有跨调用状态落文件;子 agent 每次全新上下文,所需文件**绝对路径**显式传入。

## 9 共享内核(母本 + 同步副本)

- **母本**:`my-skills/skills/_adversarial-core/`(`adversarial-core.md` + `review-schema.json`),权威单一来源。
- **同步**:`sync-core.sh skills/multi-agent-test-iteration` 把母本复制进本 skill 的 `references/adversarial-core.md` 与 `assets/review-schema.json`(母本副本只读、勿手改)。
- **本 skill 专属**(不进母本):`SKILL.md`、角色定义、阶段流程、`category` 测试枚举、prompt 模板(scope-planning / test-author / test-reviewer)、`host-adapter.md` 映射表、`severity` 阈值(K=2/M=5)。
- **母本是否需扩展**:`real-bug` 分流目前在宿主层按 `category` 过滤完成,**不改母本 schema**(保持三块共用)。若后续认为需要 schema 级区分(如增 `reported_bugs` 字段),作为独立的母本演进项谨慎评估(影响 design/dev),见 §13。

## 10 套件命名

- 设计:`multi-agent-design-review`(已有)· 开发:`multi-agent-dev-iteration`(已有)· 测试:**`multi-agent-test-iteration`**(本 spec)· 共享内核:`_adversarial-core`。
- 登记:在 `.claude-plugin/marketplace.json` 的 `skills` 数组加 `"./skills/multi-agent-test-iteration"`。

## 11 本 skill 的验证计划(每功能可验证)

- **单元级**:① `category` 分流逻辑(给定混合 findings,`real-bug` 正确抽出、其余正确喂收敛);② 复用 `progress-check.py` 在测试语义下的判定(构造多轮 `prior_findings_status` 序列,验 continue/complete/escalate);③ `sync-core.sh` 同步幂等;④ review JSON 的 schema 校验(合法 / 非法样本);⑤ worktree 建立与拆除。
- **功能级**:① 取一个小真实测试目标跑通整循环(写测试 → 执行 → 评审 → 收敛 → complete);② 模拟"测试假绿(mock 核心路径)",验证评审标 `fake-green` blocker 且主笔须修;③ 模拟"UI 起不来",验证降级标 `unexecuted`、移入 `open_questions`、**不伪造绿**;④ 模拟"测试报红=真 bug",验证分流入 `bug-report` 且**不阻塞 complete**;⑤ 模拟连续 2 轮无净进展 / 到硬上限,验证 escalate 上交人类;⑥ 模拟测试质量分歧,验证上交人类不私自降级。
- **集成级**:① 正确吃 `multi-agent-dev-iteration` 产物(`dev/<feature>` 实现 + `dev-log`);② 无 dev-log 时仅凭 DESIGN + 实现也能跑(输入前提弹性);③ `bug-report.md` 可被人类 / 回流 dev-iteration 消费。
- **宿主无关级**:host-adapter 映射表在 Claude Code 下端到端可跑;抽象能力词在 SKILL 正文无残留的写死 CLI。
- 无法验证的点移入「未决问题」并说明原因。

## 12 与其他 skill 衔接

- **上游**:`multi-agent-dev-iteration`(产 `dev/<feature>` 实现 + `dev-log`)→ **本 skill**;或任意"已有冻结 DESIGN + 实现"的项目直接进入(不强制走过 dev)。
- **下游 / 回流**:`bug-report.md` → 人类决定回 `multi-agent-dev-iteration` 修复,或接受为已知问题。
- **横向按需**:`Explore` 调研;UI 测试编写参考 `frontend-design` 的交互约定;`chrome-devtools` / `playwright` MCP 作为 UI 执行的可选增强(经 host-adapter)。
- **薄编排层**(远期):把 设计 → 开发 → 测试 串成一条流水线,产物自动交接。

## 13 前置 / 未决事项

1. **工作区与 UI 执行环境**:worktree symlink node_modules 可能令 UI 的 dev server 在 worktree 内起不来(dev 实战⑤已现)。策略:UI 执行优先在 worktree 起;起不来则回退到主仓库 checkout 实现分支起(或用户环境),再不行按降级标记 `unexecuted`。具体回退细节留 plan/实现细化。
2. **`real-bug` 是否需母本 schema 支持**:当前在宿主层按 `category` 过滤,不改母本。若实践中发现 schema 级区分更稳,作为母本演进项单独评估(须保证 design/dev 行为不回退)。
3. **dev 已写单测的去重**:本 skill 单元层级应"审视 + 补强"而非重写 dev 单测;如何避免重复、如何标注"已由 dev 覆盖",留 prompt 模板细化。
4. **设计 skill 接入母本**(套件遗留项,非本 skill 阻塞):`multi-agent-design-review` 仍用内联 schema,接入母本是独立的 regression-sensitive 任务。

## 14 下一步

本 spec 经用户复核通过后 → 进入 `superpowers:writing-plans`,产出"按什么顺序、分几步实现本 skill"的执行计划(含内核同步、prompt 模板、host-adapter、验证脚本、marketplace 登记的排序)。
