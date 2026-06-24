---
name: multi-agent-design-review
description: >-
  软件项目正式编码前的"详细设计阶段":先逐条与用户澄清需求,再由 Claude 主笔详细设计、Codex 作只读对抗式评审,循环迭代到
  无 Blocker / Major 后冻结为 DESIGN.md(含每功能的单元 / 功能 / UI 验证计划)。适合有一定复杂度、值得先冻结方案的改动。
  当用户准备开发功能 / 模块 / 站点 / SaaS / API / 迁移,并表达"先出详细设计再写代码""先设计后编码""做设计评审""让 Codex
  评审方案""冻结设计文档""进入开发前先把方案敲定",或意图就是"动手写实现前先把详细设计定稿"时触发。只产出并冻结设计文档,
  不写实现代码。
---

# Multi-Agent Design Review(多智能体详细设计评审)

详细设计阶段的多角色协作工作流:**先把需求抠清楚,再由主笔产出详细设计,由独立评审者对抗式审查,循环到无 Blocker/Major 后冻结**。把"写方案的人"和"挑方案毛病的人"分开,才能避免自说自话——主笔容易爱上自己的方案,独立评审者才会去捅它的失效路径。

## 角色模型(与宿主解耦)

| 角色 | 职责 | 能力位 |
|---|---|---|
| **Orchestrator(编排者)** | 流程编排、循环控制、终止判定、分级争议裁决;**唯一与用户交互的角色**;冻结时收尾补产物(见下) | 宿主主 Agent |
| **Author(主笔)** | 主笔 DESIGN.md + 每轮按评审修订 + 给逐条采纳/拒绝理由 | Claude(擅长长文档、方案表达) |
| **Reviewer(评审)** | 只读对抗式评审,结构化输出 findings | Codex(擅长代码库一致性、工程落地、测试、风险) |

**宿主适配**(详细调用见 `references/orchestration.md`):Claude Code 为宿主(主推 ✅)→ Author = Claude **subagent**(Agent 工具)、Reviewer = **`codex exec`** 只读;Codex 为宿主(镜像 ⚠️未实测)→ Author = **`claude -p`**、Reviewer = Codex 本地承担。两种宿主都**零自调用**。

**Author / Reviewer 都不直接与用户交互**:所有澄清、拍板由 Orchestrator 出面(子 Agent 无法向用户提问)。

## 何时使用 / 何时不用

**使用**:准备开发功能 / 模块 / 站点 / SaaS / API / 迁移,且希望先有详细设计再编码。

**不使用**:需求还在"做不做 / 做什么"层面 → 先 `superpowers:brainstorming`(发散);只改一两行 → 直接改;已在写实现代码 → 本 Skill 不写实现,代码评审走 `/codex:review`。

## 任务分档(开工前先判断走哪档)

不要给两行小改套全套重型编排。

- **轻量档**(改动 ≲ 3 文件、无数据迁移、无鉴权/权限变化、无新增对外接口):Orchestrator **自己**澄清关键点 + 自己写一份精简 DESIGN(省 Author 子 Agent)+ **单轮** Codex 评审。够用就好。
- **完整档**(其余,尤其涉及迁移 / 鉴权 / 跨模块 / 对外契约):走下面完整三角色流程。
- 拿不准 → 默认完整档。

## 核心原则(硬性,决定成败)

1. **需求先澄清再设计**:主笔前必须先理解需求与现状,把歧义/假设/边界逐条向用户确认(阶段 0)。设计跑偏几乎都源于需求没抠清。
2. **职责分离(评审侧 ⊥ 设计侧)**:独立性的关键是 **Reviewer(Codex)独立于设计侧**——Reviewer 只读、只评不改。设计侧内部,DESIGN.md 默认由 Author 主笔/修订;Orchestrator 只在三种情形亲自执笔:① 轻量档(本就没有独立 Author)、② Author 失败兜底接管、③ 冻结收尾。这三种都不损害评审独立性(Reviewer 始终是独立的 Codex)。
3. **真实调用 + 失败兜底**:角色一律用真实 CLI / 宿主原生 subagent 调起,开工前预检。**绝不**编造命令/参数/端点或伪造评审。任一外部调用失败(Reviewer 调不起/输出不合 schema、Author 子 Agent 失败)都要**如实处理、不得当成通过**:Reviewer 失败 → 停止并报告;Author 失败 → Orchestrator 自己接管主笔,不空转、不伪造。
4. **落到实处,不泛泛**:设计与评审的每条都落到具体的模块 / 文件 / 接口 / 数据结构 / 数据流 / 测试。
5. **每个功能都必须可验证**:每个功能点都要有验证方式(单元 / 功能 / UI 交互三层,按适用性),无法验证的功能移入「未决问题」并说明原因。见 `references/design-doc-template.md` 的「功能 × 验证矩阵」。
6. **评审者定分级,主笔可申辩**:分级由 Reviewer 给出;Author 可有理有据反驳或部分采纳,但**不能单方面把 Blocker 降级**——分歧本身就是要上交人类的未决项。
7. **不越界**:只产出和冻结设计文档,不写实现代码、不做范围外重构;会话内委派用 subagent,**不在 Claude Code 里 spawn `claude -p` 自调用**。

## 工作流(完整档)

> `<feature>` = kebab-case 短名。每阶段的具体调用命令、子 Agent prompt、失败处理、Codex-host 镜像,见 `references/orchestration.md`。

### 阶段 0 — 需求理解与澄清(强制前置,Orchestrator 主导)

设计跑偏的根因几乎都在这一步,**不要跳过**。

1. **预检**:① Reviewer 可用(Claude-host:`codex login status`),不可用则停下告知,不伪造;② 确定仓库根:默认 `git rev-parse --show-toplevel`,**若不在 git 仓库则用当前目录作 REPO_ROOT 并在 `codex exec` 加 `--skip-git-repo-check`**。
2. **定 feature 短名**:Orchestrator 依需求拟一个 kebab-case 短名,连同需求一起请用户在第一轮确认里敲定。
3. **目录预检** `docs/design/<feature>/`:不存在→初始化(DESIGN.md / review-log.md / .codex/);已存在且 DESIGN.md 标"已冻结"→请用户选 换名/归档/显式 resume,**不静默覆盖**;存在草稿→按当前轮次接续,不混用旧 `.codex` 产物。
4. **调研**:读相关代码 + 需求文档建立现状理解(可委派宿主调研子任务工具,Claude Code:`Explore` 子 Agent;无则 Orchestrator 自行调研)。
5. **产出待确认清单**(模板 `references/requirements-clarification.md`):歧义、假设、范围边界、非功能需求、验收标准、每个功能"打算怎么验证"。
6. **逐条确认**:用宿主提问工具(Claude Code:`AskUserQuestion`;无则主对话直接提问)逐条向用户确认。若需求在"做不做/做什么"层面没定 → 退回 `brainstorming`。
7. **固化**:确认结论写入 DESIGN.md 顶部「已确认需求与约束」。

### 阶段 1 — Author 主笔第一版设计

Orchestrator 委派 **Author 子 Agent**(传入:已确认需求、现状调研、`design-doc-template.md`)。Author 产出 `DESIGN.md`(含模板全部章节与「功能×验证矩阵」),写"现状"前先读真实代码。**Author 失败 / 返回空 / 产出不含验证矩阵 → Orchestrator 自己接管主笔。**

### 阶段 2 — Reviewer 评审(第 1 轮)

Orchestrator 调起 Reviewer(只读),喂**设计全文 + 已确认需求 + 真实仓库文件指针**,结果落 `.codex/round-1.json`。**随后校验**:exit code、文件存在且非空、可解析、字段合 schema。**调用/进程失败可重试一次;输出存在但校验不过、或重试后仍失败 → 停止并向用户报告,禁止进入阶段 3 或冻结,绝不静默当通过**。

### 阶段 3 — Author 分诊并修订

Orchestrator 把 findings 交给 Author 子 Agent,**传入文件**:当前 `DESIGN.md`、`review-log.md`、本轮 `round-<N>.json`、已确认需求、上一轮处理结论(文件驱动,不依赖子 Agent 记忆)。Author 逐条记录**采纳 / 部分采纳 / 拒绝 + 理由**并修订 DESIGN.md。Orchestrator 复核:拒绝 Blocker/Major 时该分歧成为"上交人类"未决项,**不得私自降级**。

### 阶段 4 — 第 2 轮评审(验证修复 + 查回归)

若第 1 轮有 Blocker/Major,修订后跑第 2 轮。**不是重评**,而是:① 用结构化字段 `prior_findings_status` 逐条标记第 1 轮 Blocker/Major 是否 resolved / partially_resolved / unresolved;② `findings` 只承载未解决或新增问题。带上第 1 轮 findings 与处理结论。

### 阶段 5 — 终止判定与冻结

见"终止条件"。**冻结动作**(仅 GO / GO with conditions):Orchestrator 把 DESIGN.md 状态行改为"已冻结 / 日期 / N 轮"、补 review-log 终止结论;NO-GO 不冻结。这是原则 2 列明的 Orchestrator 三种执笔情形之一。

## 评审分级规则(由 Reviewer 给出)

- **Blocker**:不解决不能进入开发——数据错误/丢失、安全漏洞、与现状不兼容且无迁移路径、核心假设不成立、关键场景无法实现、核心功能完全无法验证。
- **Major**:严重但不绝对阻断——明显落地困难、重要失效路径未覆盖、性能/可维护性实质隐患、关键功能缺应有测试层、缺回滚方案。
- **Minor**:改进项,不阻塞,但记入"已知债务"。

每条问题**必须带落点(anchor)**:文件 / 章节 / 接口 / 数据流 / 测试。无落点视为无效评审。

## 终止条件

- ✅ **可冻结(= GO 或 GO with conditions)/ 早停**:无 Blocker、无 Major(**可含 Minor 或需跟踪的条件项**;第 1 轮即如此则直接冻结,无需第 2 轮)。两档都**冻结 DESIGN 并可进开发**,差别只在**是否存在**需在开发中跟踪的条件项 / Minor 债务(记入 review-log)。
- ⛔ **NO-GO / 上交人类(不冻结)**:满 2 轮仍有未解决 Blocker/Major,**或** Author 与 Reviewer 对某 Blocker/Major 有分歧 → 停止循环、**不冻结**,带未决项清单交用户拍板。绝不为"通关"私自降级。
- **open_questions 不阻塞冻结、也不得藏 blocker**:Reviewer 的 open_questions 仅为非阻塞澄清/取舍;凡影响范围 / 可行性 / 安全 / 迁移 / 验证的问题必须是带 severity 的 finding;上一轮 Blocker/Major 未 resolved 则**不得 approve**(已由 `codex-review-prompt.md` + 阶段 2/4 输出校验强制)。

## 输出格式(最终交付三部分)

1. **设计文档** `docs/design/<feature>/DESIGN.md`(冻结版,文末标注冻结日期与轮数)。
2. **评审处理表** `docs/design/<feature>/review-log.md`(全部 findings + 分级 + 处理结论 + 理由,跨轮累积)。
3. **是否可进入开发(三档,有判定规则)**:
   - **GO**:0 Blocker/Major,且无需在开发中跟踪的条件项。
   - **GO with conditions**:0 Blocker/Major,但有需开发中跟踪的条件项或 Minor 债务。
   - **NO-GO**:任一未解决 Blocker/Major 或分歧 → 上交人类,列出待决清单。

## 与其他 skill 的衔接

- **上游**:需求要发散/定方向 → `superpowers:brainstorming`。
- **本 Skill**:详细设计 + 评审 + 冻结。产出"改什么 / 为什么 / 怎么验证"(设计意图)。
- **下游**:`superpowers:writing-plans` 产出"按什么顺序、分几步落地"(执行序列)——**本阶段不排实现步骤**;再 `superpowers:test-driven-development` 编码。
- **横向按需**:UI → `frontend-design:frontend-design`;设计系统 / 无障碍 / 文案 → `design:*`;现状调研 → `Explore` 子 Agent。

## 引用文件

- `references/orchestration.md` — 三角色编排、各阶段真实命令、失败处理、subagent 要点、Codex-host 镜像。
- `references/requirements-clarification.md` — 阶段 0「需求理解 + 待确认清单」模板。
- `references/design-doc-template.md` — 设计文档模板(含「功能 × 验证矩阵」)。
- `references/codex-review-prompt.md` — Reviewer 评审 prompt 模板。
- `assets/codex-review-schema.json` — 评审结构化输出 schema(含第 2 轮 `prior_findings_status`)。
- `assets/review-log-template.md` — 评审处理表模板。
