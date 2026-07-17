---
name: skill-manage
description: 管理 AFreeCoder 的 Skill：用 npx skills 安装、更新、卸载自建和第三方 Skill；修改或新建 my-skills 自建 Skill 后完成提交、推送并刷新本机安装。遇到"安装 Skill""更新或卸载 Skill""修改或新建自建 Skill""收藏第三方 Skill"等请求时使用。
---

# Skill Manage

## 体系边界

- [AFreeCoder/my-skills](https://github.com/AFreeCoder/my-skills)（公开仓库）是唯一事实源：`skills/<name>/` 保存自建 Skill 源码，README 收藏表格记录常用第三方 Skill。
- 安装、更新、卸载一律通过 [skills CLI](https://github.com/vercel-labs/skills)（`npx skills`）执行，不手工复制目录。
- 安装实体统一落在项目级 `.agents/skills/` 或用户级 `~/.agents/skills/`（skills CLI 的 canonical 目录）；Codex 直接读取该目录，Claude Code 经软链读取。
- 仓库公开：自建 Skill 内容不得包含内网地址、密钥等敏感信息。
- 用户未明确范围时默认项目级；明确说"用户级""全局"时加 `-g`。

## 安装、更新、卸载

```bash
# 安装第三方 Skill（README 收藏表格附有来源）
npx skills add <owner/repo> --skill <name> [-g] -y

# 安装自建 Skill
npx skills add AFreeCoder/my-skills --skill <name> [-g] -y

# 更新 / 卸载
npx skills update [<name>] [-g|-p]
npx skills remove <name>
```

全局安装不要传 `-a codex`：Codex 的全局目录就是 `~/.agents/skills`，传了反而会写入已弃用的 `~/.codex/skills`。

安装记录（lock）分范围各存一份：全局在 `~/.agents/.skill-lock.json`，项目级在 `<project>/skills-lock.json`（无时间戳、可随项目提交）。没有跨范围的汇总命令——用户想总览已装 Skill 时，执行 `npx skills list -g` 和 `npx skills list` 两条命令并合并汇报。

## 修改或新建自建 Skill（核心闭环）

修改自建 Skill 的任务默认包含推送远程和刷新本机安装；完成修改后按顺序执行，无需逐步询问：

1. 在 my-skills 仓库按规范使用独立 feature 分支和 worktree 修改，禁止直接在 `main` 开发。
2. 自检：目录名与 frontmatter `name` 一致（只用小写字母、数字、连字符）；`description` 描述真实触发场景；脚本与参考资料在本 Skill 目录内；新增或删除 Skill 时同步 README 自建表格与数量声明。
3. 合入 `main` 并推送远程。不推送就不算完成——npx 安装的是远程内容，本地不推送则安装项停留在旧版。
4. 推送后刷新本机安装。npx 装的是复制的实体，不会自动跟随远程，每个安装位置都要显式跑一次 update——本闭环代为执行，用户无需手动操作：全局安装必刷 `npx skills update <name> -g -y`；当前项目也装有该 Skill 时，再执行一次 `npx skills update <name> -p -y`。其他项目里的安装本次触达不到，留待下次在该项目中操作 Skill 时刷新。
5. 汇报：修改内容、合入的 commit、已刷新的安装范围。

## 收藏第三方 Skill

把新条目加进 README 收藏表格（Skill 名、来源、一句话说明），不复制上游源码进仓库。移除收藏只删表格行，不卸载任何已安装目录。

## 开发期高频调试（可选）

反复调试某个自建 Skill 时，可临时把安装项换成指向仓库源码的软链，改动即时生效：

```bash
ln -sfn ~/project/my-skills/skills/<name> ~/.agents/skills/<name>
```

定稿后走上面的闭环（推送，再用 `npx skills add AFreeCoder/my-skills --skill <name> -g -y` 恢复正式安装）。

## 汇报

说明：操作的 Skill 与范围、执行的命令、推送的 commit、已刷新或未刷新的安装、遗留事项。
