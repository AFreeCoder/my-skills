# 实现 Bug 清单 · <feature>

> 测试阶段产物。本 skill 只报不修;人类决定:回 multi-agent-dev-iteration 修 / 接受为已知问题 / 手动修。
> 每条来自评审复核确认的 real-bug(category=real-bug),非测试自身质量问题。

## 元信息
- feature: <feature> / 实现分支:<branch> / 测试分支:test/<feature>
- 关联矩阵:docs/test/<feature>/test-matrix.md

## Bug 列表

### BUG-<n>: <标题>
- 关联测试目标 / 用例:G<G> / <test 名>
- severity:blocker / major / minor
- anchor(实现位置):<file:行 / 接口>
- 期望行为:<DESIGN/矩阵验收点要求的>
- 实际行为:<测试观察到的>
- 复现步骤:<命令 / 操作序列>
- 首次发现:目标 G<G> 轮次 <R>
- 人类裁定:<回 dev 修 / 接受为已知 / 手动修 / 待定>

## 汇总
- 总计:<n> 个(blocker <x> / major <y> / minor <z>)
- 建议衔接:<整体倾向>
