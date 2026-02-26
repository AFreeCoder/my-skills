---
name: git-auto-commit
description: 自动读取当前本地 Git 仓库的最新变更，生成变更摘要与提交信息并完成 git commit。适用于用户要求“自动提交/提交最新变更/总结后提交/生成 commit message 并提交”等场景。
---

# Git Auto Commit

## 概览

自动读取仓库最新变更，生成中文摘要与提交信息，并执行提交。

## 工作流

### 1. 采集变更

- 执行 `git rev-parse --show-toplevel` 确认处于 Git 仓库内。
- 执行 `git status -sb` 获取整体状态并识别冲突/变基/合并中状态。
- 执行 `git diff --stat` 与 `git diff --numstat` 获取改动范围与规模。
- 执行 `git diff` 获取未暂存改动；如已有暂存改动，执行 `git diff --cached`。
- 执行 `git ls-files --others --exclude-standard` 获取未跟踪文件。
- 当改动过大时，优先依据 `--stat/--numstat` 与关键文件抽样查看细节。

### 2. 生成摘要

- 用 2-6 条要点总结变更，按模块/目录/文件归类。
- 明确标注新增/修改/删除与核心意图。
- 如涉及配置、依赖、迁移、安全或破坏性变更，必须单独强调。

### 3. 合并 vault backup 提交（如适用）

- 执行 `git log -n 20 --oneline` 查看近期提交。
- 检测从 HEAD 开始的**连续** `vault backup: *` 提交（由 obsidian-git 插件自动生成）。
- 若连续 vault backup 提交 ≥ 2 条：
  1. 记录这些提交覆盖的变更范围：`git diff <最早vault backup的父提交>..HEAD --stat`。
  2. 将当前工作区未提交的变更（如有）先 `git stash`。
  3. 执行 `git reset --soft <最早vault backup提交的父commit>`，将所有 vault backup 提交压缩为暂存区变更。
  4. 基于合并后的完整变更内容，按第 4 步规则生成一条有意义的提交信息。
  5. 执行 `git commit` 完成合并提交。
  6. 如之前 stash 了变更，执行 `git stash pop` 恢复。
- 若连续 vault backup 提交 ≤ 1 条，跳过本步骤。
- **注意**：仅合并尚未推送到远程的本地提交。若 vault backup 提交已推送（`git log origin/main..HEAD` 不包含），不做合并。

### 4. 生成提交信息

- 使用简化 Conventional Commits：`<type>(scope): 主题`。
- 选择 `type`：`feat`、`fix`、`docs`、`refactor`、`chore`、`test`、`build`。
- 选择 `scope`：主要目录/模块名；`主题` 用简洁中文动词短语。
- 如存在提交模板，执行 `git config --get commit.template` 并遵循其格式。

### 5. 执行提交

- 默认提交所有最新变更，执行 `git add -A`。
- 若用户明确"仅提交已暂存"，跳过 `git add -A`。
- 执行 `git commit -m "<message>"` 完成提交。
- 若提交失败（如钩子报错、冲突未解、空提交），停止并报告错误与原因。

### 6. 输出格式

- 先输出"变更摘要"，再输出"提交信息"与"提交结果（commit hash）"。
- 若执行了 vault backup 合并，额外说明合并了几条提交。
- 若无可提交变更，明确说明并不执行提交。

## 保护性检查

- 若处于 merge/rebase/cherry-pick 等进行中状态，停止并提示用户先处理。
- 若出现二进制或异常大文件新增，提示并确认是否继续提交。
