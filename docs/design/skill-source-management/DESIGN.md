# Skill Source Management Cleanup Design

日期：2026-07-11

## 目标

根据用户确认，删除以下 7 个自建 Skill：

- `content-writing`
- `daily`
- `git-auto-commit`
- `gpt101-dashboard-renew`
- `multi-agent-design-review`
- `multi-agent-dev-iteration`
- `multi-agent-test-iteration`

删除后，`my-skills` 仍作为自建 Skill 的事实源。本次不迁移或删除 Lark、Anthropic、Obsidian、宝玉等官方/第三方 Skill；它们的来源管理另行实施。

同时把遗漏的自建 `push-deploy` 从当前经过发布门禁验证的
`~/.codex/skills/push-deploy/` 原件纳入 `my-skills`。不得使用内容较旧的
`~/.cc-switch/skills/push-deploy/` 副本。

## 范围

### 删除

- 上述 7 个 `skills/<name>/` 目录。
- 三个 multi-agent Skill 删除后不再有运行时消费者的 `skills/_adversarial-core/` 私有共享资产。
- `.claude-plugin/marketplace.json` 中对应的 7 个注册项。
- `README.md` 中对应的 7 行与过期 Skill 总数。

### 新增

- `skills/push-deploy/`，内容与当前 Codex 全局原件逐文件一致。
- `.claude-plugin/marketplace.json` 中的 `./skills/push-deploy` 注册项。
- `README.md` 中的 `push-deploy` 目录项。

### 保留

- `docs/specs/`、`docs/plans/`、`docs/verification/` 下既有 multi-agent 过程文档。这些文档是历史记录，保持冻结。
- `apipool-push-deploy`、`apipool-sync-upstream`、`webpage-clipper` 及所有未被点名的 Skill。
- CC Switch 与用户级 Skill 入口。本次只修改 `my-skills` 仓库，入口迁移另行处理。

## 一致性规则

变更完成后必须同时满足：

1. 7 个 Skill 目录和 `_adversarial-core` 不存在。
2. marketplace 不再注册这 7 个 Skill。
3. README 不再列出这 7 个 Skill，列出新增的 `push-deploy`，并显示实际的 35 个 Skill。
4. marketplace 注册集合与所有包含 `SKILL.md` 的一级目录完全一致。
5. JSON 可解析，剩余 Skill 的 `SKILL.md` 均具备 `name` 和 `description`。
6. 仓库内 `push-deploy` 与 `~/.codex/skills/push-deploy/` 完全一致。

## 风险控制

- 删除仅发生在隔离 worktree 的 `chore/skill-source-cleanup` 分支。
- 删除前运行现有 `_adversarial-core` 测试，确认基线正常。
- 先执行一个预期失败的库存断言，证明测试能捕获待删除项。
- 不删除冻结过程文档，不修改主工作区，不推送远程。
