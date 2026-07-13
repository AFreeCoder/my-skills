# Self-built Skills Only Implementation Plan

日期：2026-07-13

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `my-skills` 收敛为仅维护 4 个自建 Skill，并清理会造成用户级全局加载的历史 Skill 安装与 CC Switch 注册数据。

**Architecture:** `my-skills/skills/` 只保存自建 Skill 的权威源码；项目按需把自建 Skill 逐个软链到 `.agents/skills/`。官方和第三方 Skill 不进入本仓库，也不在 CC Switch 或用户级全局目录集中维护，而是在具体项目中按上游说明安装。

**Tech Stack:** Git、Shell、JSON、Markdown、SQLite、AgentSkills

---

### Task 1: 收敛仓库 Skill 集合

**Files:**
- Delete: `skills/baoyu-article-illustrator/`
- Delete: `skills/chronicle/`
- Delete: `skills/claude-to-im/`
- Delete: `skills/frontend-design/`
- Delete: `skills/json-canvas/`
- Delete: `skills/lark-*/`
- Delete: `skills/obsidian-bases/`
- Delete: `skills/obsidian-markdown/`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`

- [x] **Step 1: 删除所有官方、第三方和宿主管理 Skill 副本**

保留集合必须严格为：

```text
apipool-push-deploy
apipool-sync-upstream
push-deploy
webpage-clipper
```

- [x] **Step 2: 将 marketplace 注册表收敛到相同的 4 项**

Run:

```bash
jq empty .claude-plugin/marketplace.json
jq -r '.plugins[0].skills[]' .claude-plugin/marketplace.json
```

Expected: JSON 合法，只输出上述 4 个目录。

- [x] **Step 3: 重写 README 的职责、目录和接入说明**

README 必须明确：仓库只维护自建 Skill；自建 Skill 逐个软链进项目 `.agents/skills/`；第三方 Skill 在项目中按需安装；Claude 项目入口可软链到 `.agents/skills`；不再通过 CC Switch 全局同步。

### Task 2: 验证仓库一致性

**Files:**
- Verify: `skills/*/SKILL.md`
- Verify: `.claude-plugin/marketplace.json`
- Verify: `README.md`

- [x] **Step 1: 比较 Skill、marketplace 和 README 三组清单**

Expected: 三组集合都严格等于 4 个自建 Skill。

- [x] **Step 2: 校验每个保留 Skill 的 frontmatter**

Expected: 每个 `SKILL.md` 至少包含非空的 `name` 和 `description`。

- [x] **Step 3: 校验 JSON、Markdown 变更和 Git diff**

Run:

```bash
jq empty .claude-plugin/marketplace.json
git diff --check
git status --short
```

Expected: JSON 合法、diff 无空白错误，状态只包含本计划批准的文件。

### Task 3: 清理用户级全局 Skill

**Files:**
- Clean: `~/.cc-switch/skills/`
- Clean: `~/.codex/skills/`
- Clean: `~/.claude/skills/`
- Clean: `~/.agents/skills/`
- Modify: `~/.cc-switch/cc-switch.db`
- Backup: `~/.cc-switch/backups/cc-switch-before-skill-cleanup-<timestamp>.db`

- [x] **Step 1: 退出 CC Switch 并备份数据库**

Expected: CC Switch 没有运行；备份文件通过 SQLite 完整性检查。

- [x] **Step 2: 删除 CC Switch 的 Skill 注册记录并禁用默认仓库源**

在单个 SQLite 事务中清空 `skills` 与自定义 `skill_repos`。CC Switch 启动时会自动重建 4 个内置仓库源，因此保留这些内置记录并将 `enabled` 设为 `0`，防止它们参与后续安装或更新。

- [x] **Step 3: 清理用户级目录**

清空 `~/.cc-switch/skills/`、`~/.claude/skills/` 和 `~/.agents/skills/`。`~/.codex/skills/` 只保留 `chronicle` 与 `codex-primary-runtime` 两个宿主管理目录；不删除 `~/.codex/superpowers/`、`~/.gstack/repos/` 和 Codex 插件缓存。

- [x] **Step 4: 验证清理不会回填**

Expected: CC Switch 数据库的 `skills` 为 0 行，4 个启动时自动重建的内置仓库源全部禁用；三个待清空目录均为 0 项；`~/.codex/skills/` 只包含两个宿主管理目录。隐藏启动 CC Switch 后状态保持不变。
