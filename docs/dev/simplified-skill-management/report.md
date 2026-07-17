# Skill 管理体系收敛开发报告

日期：2026-07-17

## 实际完成

- 删除仓库根目录 `bin/my-skills`，管理实现不再属于 `my-skills` 根级工具。
- 删除 `.claude-plugin/marketplace.json` 和对应审计依赖。
- 将第三方清单从两个来源收藏项展开为 2 个来源、15 个具体 Skill。
- 新增 `skills/skill-manage/scripts/skill_manage.py`，实现 `list`、`init`、`install`、
  `update`、`uninstall`、`external` 和 `audit`。
- 用户级和项目级均以 `.agents/skills` 为实际安装目录，并统一创建
  `.claude/skills -> ../.agents/skills`。
- 自建 Skill 使用权威源码软链；第三方 Skill 使用清单门禁、临时获取和目录复制。
- 删除原 Shell CLI 测试和独立审计脚本测试，改为 Python 端到端测试。
- 重写 README、`skill-manage/SKILL.md` 和 Codex 展示元数据。

## 与设计的偏差

没有新增 catalog、lock/state、插件清单或安装标记。实现与设计基线一致。

第三方清单刷新属于用户显式维护动作，会直接更新 `external/skills.json`；它不会安装或更新任何
运行时 Skill，也不会自动执行 Git 操作。

## 兼容影响

- 旧的 `my-skills list|init|add|link|unlink|external` 命令被移除。
- 现有 `$HOME/bin/my-skills` 如果是指向仓库旧脚本的软链，合入后会成为断链，需要在实际启用阶段处理。
- 用户级 AGENTS 规则如果仍要求运行旧命令，需要在新实现合入后单独更新。
- 本次没有迁移 `~/.agents/skills`、`~/.claude/skills` 或任何业务项目的现有目录。
