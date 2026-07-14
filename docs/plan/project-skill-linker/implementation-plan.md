# Project Skill Linker Implementation Plan

日期：2026-07-14

## 范围

实现 `my-skills` 项目级 Skill 链接命令，并把本机 Codex 全局规则更新为：
项目 Skill 统一落在 `.agents/skills/`，Claude Code 通过
`.claude/skills -> ../.agents/skills` 复用同一目录。

## 任务

- [x] 确认设计文档已由用户确认，冻结设计。
- [x] 新增 `bin/my-skills`，实现 `init`、`link`、`unlink`。
- [x] 新增 `tests/test-my-skills.sh`，覆盖幂等、冲突、批量预检、项目定位和软链调用。
- [x] 更新 README 的项目级接入说明。
- [x] 更新 `/Users/afreecoder/.codex/AGENTS.md` 的项目级 Skill 管理规则。
- [x] 创建用户 PATH 入口 `/Users/afreecoder/bin/my-skills`。
- [x] 运行测试和静态检查。
- [ ] 提交、合入 `main`、推送远程并清理 feature worktree。

## 验证

计划执行：

```bash
bash tests/test-my-skills.sh
shellcheck bin/my-skills tests/test-my-skills.sh
git diff --check
```

若本机没有 `shellcheck`，改用：

```bash
bash -n bin/my-skills tests/test-my-skills.sh
```

并在最终结果中说明 `shellcheck` 未运行。
