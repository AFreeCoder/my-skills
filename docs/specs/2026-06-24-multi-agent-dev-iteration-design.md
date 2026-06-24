# 详细设计 · `multi-agent-dev-iteration`(开发阶段对抗式协作 skill)

> 状态:草案(待用户复核)· 日期:2026-06-24 · 阶段:brainstorming 产出的设计 spec
> 本 spec 只定**开发 skill**;测试 skill 与编排层是后续各自独立的 spec。

## 1 背景与目标

终极目标:把现有 `multi-agent-design-review` 扩展成一整套 **设计 → 开发 → 测试** 的对抗式多智能体流水线,由三个**独立可组合**的 skill + 一个**薄编排层**串联,产物逐级交接(`DESIGN.md` → 实现代码 → 测试验证)。

三个 skill 共享同一套"怎么评审、怎么分级、什么时候停、怎么防作弊"的**对抗式迭代内核**,以"母本 + 同步副本"方式落地(逻辑单一来源、物理各自一份,保持每个 skill 自包含可移植)。

本 spec 聚焦套件的**第二块:开发 skill**。它与设计 skill 的核心差异在于**角色与权限反转**——设计阶段 Claude 主笔、Codex 只读评审;开发阶段 **Codex 主笔写代码、Claude 只读评审**。

## 2 已确认决策

| # | 决策 | 取值 |
|---|---|---|
| 1 | 套件结构 / 起点 | 三个独立可组合 skill + 薄编排层;**先做开发 skill** |
| 2 | 开发与测试的边界 | **开发内含 TDD**(Codex 先写测试再写实现、跑到绿,Claude 评审代码+测试);系统性功能/集成/回归/对抗验证交独立测试 skill |
| 3 | Codex 写权限 / 隔离 / 检查点 | **隔离 git worktree + `--sandbox workspace-write` 降权 + 头尾两个人类检查点** |
| 4 | 输入与迭代粒度 | 输入 = 冻结 `DESIGN.md` + `writing-plans` 有序计划;**逐 plan step 迭代** |
| 5 | 架构方案 | 方案 A:**独立 Claude 评审子 agent** + 三 skill **共享对抗式内核** |
| 6 | 共享内核落地 | **母本 + 同步副本**(母本权威,脚本同步进各 skill `references/`) |
| 7 | 迭代终止规则 | **收敛判定 + 硬上限**(详见 §7) |

## 3 范围与边界

**做什么**:吃冻结的 `DESIGN.md` + `writing-plans` 计划,逐 step 由 Codex 主笔(TDD 实现并跑绿)、独立 Claude 评审,迭代到每步无 blocker/major 且单测绿;产出实现代码(在隔离分支)+ `dev-log`,在合回主干前交人类拍板。

**不做**:
- 不重新设计(`DESIGN.md` 已冻结,发现设计本身有问题 → 作为 blocker 上交人类,不私自改设计);
- 不做范围外重构;
- 不做系统性功能/集成/回归/对抗测试(交测试 skill);
- **不自行合并主干**(由人类检查点②决定)。

## 4 角色模型(方案 A)

| 角色 | 谁 | 能力位 | 关键约束 |
|---|---|---|---|
| **Orchestrator(编排者)** | Claude 主 agent | 宿主主 Agent | 唯一与用户交互;编排/循环/终止判定/检查点把关/分级争议裁决;头尾检查点亲自对接人类 |
| **Author(主笔)** | **Codex** `codex exec --sandbox workspace-write --cd <worktree>` | 跨 CLI | 在隔离 worktree 内 TDD 实现+跑测试;**用 Claude 子 agent 看门狗包裹**(复用设计 skill 的存活监控,防长任务后台化/静默被杀误判通过) |
| **Reviewer(评审)** | **独立 Claude 评审子 agent**(Agent 工具,全新上下文) | 宿主原生 subagent | 只喂 diff + DESIGN 相关章节 + 本 step 目标 + 测试结果;结构化输出 findings;**只读不改** |

**权限反转点(与设计 skill 对照)**:设计 skill 中 Codex 只读、Claude 写;本 skill 中 **Codex 可写(限定 worktree,`workspace-write`、默认断网)、Claude 只读评审**。"写 ⊥ 审"不变——写=Codex,审=独立 Claude,互不为同一实体。

Author / Reviewer 都不直接与用户交互;所有澄清与拍板由 Orchestrator 出面。

## 5 工作流

`<feature>` = kebab-case 短名,`<N>` = plan step 序号,`<R>` = 该 step 的评审轮次。

### 阶段 0 — 预检 + 人类检查点①(进开发前)

1. **预检**:① Codex 可用(`codex login status`);② `DESIGN.md` 存在且标"已冻结";③ `writing-plans` 计划存在;④ 工作区 git 干净。任一不满足 → 停止并告知,不伪造。
2. **建隔离环境**:创建分支 `dev/<feature>` 与对应 git worktree;创建状态目录 `docs/dev/<feature>/`(`dev-log.md`、`.author/`、`.review/`)。
3. **人类检查点①**:向人类报告 — 计划步骤清单、worktree 路径、权限档(`workspace-write`)、终止规则与检查点安排 → **人类确认开工**(不确认不进入循环)。

### 每个 plan step 的循环(阶段 1→4)

- **阶段 1 · Codex 主笔(TDD)**:Orchestrator 派**看门狗子 agent** 前台同步跑 `codex exec`(大 timeout、`--sandbox workspace-write`、`--cd <worktree>`)。Prompt 要点:① 先写/补该 step 的测试 → ② 写实现 → ③ 跑到绿;只动本 step 范围;回报改了哪些文件 + 测试结果摘要。
  - **失败兜底**:Codex 失败/返回空/被信号杀(退出码判定 0=成功 / 1–2=自身报错 / ≥128 被杀,137=KILL、143=TERM)→ **如实报、重试一次、仍失败则停止上交人类**,绝不假装通过。
- **阶段 2 · Claude 独立评审**:派评审子 agent(全新上下文),喂 diff + DESIGN 相关章节 + step 目标 + 测试结果;按 schema 输出结构化 findings(`severity` / `category` / `anchor` / `confidence` / `recommendation`)与 `verdict`。
- **阶段 3 · Codex 分诊修订**:把 findings 交回 Codex(**文件驱动**,显式传入 `dev-log.md`、本轮 `.review/step-<N>-round-<R>.json`、DESIGN 相关章节、上一轮处理结论)。Codex 逐条采纳/部分/拒绝 + 技术理由,改完重跑测试;**不能单方面降级 blocker/major**(分歧 → 标注并上交人类)。
- **阶段 4 · 复评(验证修复 + 查回归)**:非重评——用 `prior_findings_status` 逐条标 resolved / partially_resolved / unresolved,`findings` 只放未解决/新增。
- **step 终止**:无 blocker/major 且单测绿 → 该 step 完成,记 `dev-log`,进下一步;否则按 §7 终止规则判定(继续 / 上交人类)。

### 阶段 5 — 人类检查点②(合回主干前)

全部 step 完成后,Orchestrator 汇总:整体 diff、测试结果、`DESIGN.md`「功能 × 验证矩阵」的覆盖情况、`dev-log` 终止结论 → **人类确认是否合并** `dev/<feature>` worktree → 主干。NO 则不合并,带未决项交人类。

## 6 评审分级规则(复用母本,代码视角)

由 Reviewer(Claude)给出,每条必须带落点(`anchor`:`file:line` / 接口 / 数据流 / 测试名),无落点视为无效评审。

- **blocker**:与 `DESIGN.md` 不符且影响核心 / 数据错误或丢失 / 安全漏洞 / **测试造假或没真跑** / 破坏现有功能(回归)。
- **major**:关键路径缺测试 / 重要失效路径未覆盖 / 明显可维护性·性能隐患 / 偏离 DESIGN 的实现选择且未说明理由。
- **minor**:改进项,不阻塞,记入「已知债务」。

Codex(主笔)可有理有据反驳或部分采纳,但**不能单方面把 blocker/major 降级**——分歧本身即上交人类的未决项。

## 7 终止规则(收敛判定 + 硬上限)

终止规则**按 plan step 分别计**:每个 step 跑自己的评审循环,轮次 `<R>` 与硬上限均为该 step 内计数,step 之间互不累加。

**不数固定轮数。**

- **软规则(真正的终止器)**:只要每轮**有净进展**(blocker/major 数量在减少、`prior_findings_status` 中有 prior 被标 resolved)就继续下一轮。出现以下任一 → **停止该 step 的循环,上交人类**:
  - **连续 2 轮无净进展**(同一 blocker/major 持续 unresolved;或本轮新增 blocker/major ≥ 本轮解决数 = 打转/抖动);
  - **Codex 与 Claude 对某 blocker/major 存在分歧**。
- **硬上限(防失控保险丝)**:绝对天花板**默认 5 轮**,到顶无论状态如何停止,带未决项上交人类。
- "净进展"由 schema 的 `prior_findings_status` 提供机器判据,不靠主观判断。

> 该机制进**母本**,阈值(连续无进展轮数、硬上限)各 skill 自定:设计 skill 可继续用更紧的早停取向,开发 skill 用上面这套收敛式 + 硬上限 5。

## 8 状态载体(文件驱动,不依赖跨调用记忆)

- 隔离:分支 `dev/<feature>` + 对应 git worktree。
- `docs/dev/<feature>/dev-log.md` — 跨 step / 跨轮累积(每 step 的 findings + 处理结论 + 理由 + 测试结果)。
- `docs/dev/<feature>/.author/step-<N>-prompt.md` — 每次喂给 Codex 主笔的 prompt。
- `docs/dev/<feature>/.review/step-<N>-round-<R>.json` — 每轮 Claude 评审的结构化输出。
- 所有跨调用状态落文件;子 agent 每次都是全新上下文,所需文件路径显式传入。

## 9 共享内核(母本 + 同步副本)

- **母本(权威单一来源)**,放套件仓库(`my-skills`)内,建议 `my-skills/skills/_adversarial-core/`:
  - `adversarial-core.md` — 通用规则:分级定义、终止规则机制、看门狗/存活监控、文件驱动约定、反作弊纪律、子 agent 调用与失败处理。
  - `review-schema.json` — 通用结构化评审输出 schema(含 `prior_findings_status`)。
- **同步**:`sync-core.sh` 把母本复制进 design / dev / test 三个 skill 各自的 `references/`,母本文件顶部标注「勿手改,从母本重新生成」。每个 skill 因此自包含、可独立安装/分发。
- **skill 专属部分**(不进母本):各自的 `SKILL.md`、角色定义、阶段流程、`category` 取值、prompt 模板、`severity` 阈值。

## 10 套件命名(建议,可调)

- 设计:`multi-agent-design-review`(已有)
- 开发:`multi-agent-dev-iteration`(本 spec)
- 测试:`multi-agent-test-iteration`(后续)
- 共享内核:`_adversarial-core`

## 11 本 skill 的验证计划(每功能可验证)

- **单元级**:`sync-core.sh` 幂等性;schema 校验逻辑(合法/非法样本);worktree 建立与拆除;看门狗对 Codex 退出码(0 / 137 / 143)的判定分支;终止规则的"净进展"判定函数(给定多轮 `prior_findings_status` 序列,正确判 继续/无进展/到硬上限)。
- **功能级**:① 取一个小真实 step 跑通整循环(实现→评审→修订→绿→下一步);② 模拟 Codex 被外部杀死,验证"如实报失败、不假装通过";③ 模拟 blocker 分歧,验证"上交人类、不私自降级";④ 模拟"连续 2 轮无净进展",验证触发上交人类;⑤ 模拟到硬上限,验证强制停止。
- **集成级**:与设计 skill 产物对接(正确吃 `DESIGN.md` + `writing-plans` 计划);向测试 skill 交接(`dev/<feature>` 分支 + `dev-log` 可被下游消费)。
- 无法验证的点移入「未决问题」并说明原因。

## 12 与其他 skill 衔接

- **上游**:`multi-agent-design-review`(产 `DESIGN.md`)→ `superpowers:writing-plans`(产有序实现计划)→ **本 skill**。
- **下游**:`multi-agent-test-iteration`(吃 `dev/<feature>` 分支 + `dev-log`,做功能/集成/回归/对抗验证)。
- **横向按需**:`Explore` 调研、`frontend-design` 等。

## 13 前置 / 未决事项

1. **设计 skill 迁移**:`multi-agent-design-review` 目前在 `~/.claude/skills/`,不在 `my-skills` 仓库。套件要统一 + 共享母本,需先把它迁入 `my-skills/skills/` 并接入母本同步。属前置迁移项,本 skill 实现前需处理。
2. **测试 skill** `multi-agent-test-iteration`:形态"类似开发 skill"(主笔/评审角色与验证手段待定),后续独立 spec。
3. **薄编排层**:把 设计→开发→测试 串成一条命令/meta-skill,产物自动交接,后续独立 spec。
4. **母本反哺设计 skill**:把通用规则从现有设计 skill 抽出形成母本时,需保证设计 skill 行为不回退(其已冻结、经实证)。

## 14 下一步

本 spec 经用户复核通过后 → 进入 `superpowers:writing-plans`,产出"按什么顺序、分几步实现本 skill"的执行计划(含前置迁移项的排序)。
