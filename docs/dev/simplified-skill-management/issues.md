# Skill 管理体系收敛遗留事项

- [ ] 新实现合入 `main` 后，更新用户级 AGENTS 中对 `my-skills init|link|unlink` 的旧说明，改为调用 `skill-manage`。
- [ ] 新实现合入后，只读审计并迁移用户级 `~/.agents/skills` 与 `~/.claude/skills`，不要自动覆盖现有目录。
- [ ] 按项目逐个审计已有 `.agents/skills` 与 `.claude/skills`，确认内容归属后再建立统一软链。
- [ ] 确认并移除失效的 `$HOME/bin/my-skills` 入口；该动作只删除旧命令软链，不删除仓库内容。
