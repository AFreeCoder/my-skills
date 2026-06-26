# 测试日志 · <feature>

> 跨目标/跨轮累积。每个测试目标一节,记录每轮主笔产出、真实运行结果、评审 findings、bug 分流、收敛判定。
> 每轮由 Orchestrator 追写,不由子 agent 直接写入。

## 元信息
- feature: <feature> / 测试分支:test/<feature>
- 矩阵:docs/test/<feature>/test-matrix.md
- 阈值:K=2 / M=5(按目标计)

## 目标 G<G>: <目标名>

### 轮次 <R>
- 主笔产出:<新增/改的测试文件 + 命令>(各层级)
- 真实运行结果(Orchestrator 复跑):<层级 → 命令 + 退出码 + 通过/失败/未执行降级>
- 评审 findings(.review/goal-<G>-round-<R>.json):
  | id | severity | category | anchor | 处理(采纳/部分/拒绝) | 理由 |
  |----|----------|----------|--------|----------------------|------|
- bug 分流:<本轮抽出的 real-bug 条数 → 已记入 bug-report.md>
- 收敛判定:<filter-findings 排除 real-bug 后跑 progress-check → complete/continue/escalate:*>
- 本目标结论:<下一轮 / 目标完成 / 上交人类(分歧/无进展/硬上限)>

## 终止结论(全部目标后)
- 各目标轮次与最终 verdict:
- 矩阵覆盖核对:<有无遗漏目标/层级;UI 降级未执行项清单>
- 已知债务(未采纳 minor):
- 交人类决策项(bug 衔接等):
