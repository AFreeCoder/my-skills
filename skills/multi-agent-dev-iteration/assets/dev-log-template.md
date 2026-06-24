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
