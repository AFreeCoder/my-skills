# 评审处理表 — <feature>

> 跨轮累积。每条 Codex finding 一行,记录分级与处理结论。与 `DESIGN.md` 同目录维护。
> 轻量档:可只保留「第 1 轮」+「终止结论」两节。

## 第 1 轮(`codex exec`,ROUND=1)

- Codex verdict:<approve | needs-revision>
- 总评:<summary>

| 编号 | 分级 | 类别 | 落点(文件/章节/接口/数据流/测试) | Codex 建议 | 处理(采纳/部分采纳/拒绝) | 理由 / DESIGN.md 改动位置 |
|---|---|---|---|---|---|---|
| F1 | blocker |  |  |  |  |  |
| F2 | major |  |  |  |  |  |
| F3 | minor |  |  |  |  |  |

## 第 2 轮(ROUND=2,验证修复 + 查回归)

- Codex verdict:<approve | needs-revision>

### 上一轮 Blocker/Major 解决状态(对应 schema `prior_findings_status`)

| 编号 | status(resolved / partially_resolved / unresolved) | evidence(DESIGN.md 哪处改动支撑) |
|---|---|---|
| F1 |  |  |

### 本轮仍未解决 / 新增(对应 `findings`)

| 编号 | 分级 | 落点 | 处理 / 理由 |
|---|---|---|---|
|  |  |  |  |

## 终止结论

**三档判定规则**:
- **GO** = 0 Blocker/Major 且无需开发中跟踪的条件项。
- **GO with conditions** = 0 Blocker/Major,但有需开发中跟踪的条件项或 Minor 债务。
- **NO-GO** = 任一未解决 Blocker/Major 或分歧 → 上交人类。
- 冻结语义:GO 与 GO with conditions 均**冻结并可进开发**;NO-GO **不冻结**。

- **本次结论**:<GO / GO with conditions / NO-GO>
- **带入开发的 Minor / 条件项**:<列出>
- **上交人类的未决项**:<未解决 Blocker/Major,或 Author 与 Reviewer 的分歧>
- 评审轮数:<N>
- **冻结收尾(Orchestrator 执行)**:把 `DESIGN.md` 状态行改为「已冻结 / <日期> / 经 <N> 轮评审」,本表归档。
