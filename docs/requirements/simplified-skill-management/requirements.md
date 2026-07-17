# Skill 管理体系收敛需求

日期：2026-07-17

## 背景

`my-skills` 目前同时承担自建 Skill 源码、第三方来源收藏、项目链接 CLI 和插件市场清单等职责，
`skill-manage` 又依赖仓库根目录的 `my-skills` CLI 执行管理操作。职责重复，且用户级安装仍可能落到
`~/.codex/skills` 等非目标目录。

Codex 当前使用 `.agents/skills` 作为项目级和用户级 Skill 入口；Claude Code 使用
`.claude/skills`。用户希望 Codex 与 Claude Code 看到同一份受管 Skill，因此需要统一实际安装目录。

## 目标

- 将 `my-skills` 收敛为自建 Skill 源码和第三方 Skill 来源清单的唯一事实源。
- 将安装、更新、卸载、目录初始化和审计能力全部放入 `skill-manage`。
- 用户级和项目级均以 `.agents/skills` 为实际安装目录。
- 用户级和项目级均使用 `.claude/skills -> ../.agents/skills` 让 Claude Code 复用同一目录。
- 所有第三方 Skill 必须先登记到 `external/skills.json`，才能安装。
- 冲突路径默认失败关闭，不静默覆盖、迁移或删除。

## 非目标

- 不建立新的 `catalog/` 目录；`external/skills.json` 就是第三方 Skill 清单。
- 不维护 lock、state、安装数据库或已安装版本历史。
- 不把 `my-skills` 发布成 Codex 或 Claude Code 插件。
- 不保留 `plugin.json` 或 `marketplace.json` 作为库存清单。
- 不让 `my-skills` 成为通用包管理器，也不管理 MCP、Agent、Hook 或插件。
- 本次不迁移真实用户目录和任何业务项目中的已有 Skill。

## 业务规则

1. 自建 Skill 源码只存在于 `my-skills/skills/<name>/`。
2. 第三方 Skill 的上游来源和具体 Skill 路径记录在 `external/skills.json`，第三方源码不进入本仓库。
3. 用户没有明确范围时默认项目级；用户级操作必须显式指定。
4. 自建 Skill 通过软链安装，安装项直接指向本仓库源码。
5. 第三方 Skill 从登记的上游临时获取后复制到目标 `.agents/skills/<name>/`。
6. 安装命令不接受未登记的原始 URL 或 `owner/repo`；应先维护第三方清单。
7. 第三方更新不依赖安装状态文件，而是重新获取清单中的上游内容并与目标目录比较。
8. `.claude/skills` 已是普通目录、断链或错误软链时停止并报告，不自动覆盖。
9. 更新和卸载第三方普通目录必须显式确认；自建 Skill 只允许移除指向权威源码的软链。
10. 清单维护不自动执行 Git commit、push 或合并。

## 验收方向

- 仓库根目录不再包含承担管理职责的 `bin/my-skills`。
- `skill-manage` 自带确定性的管理脚本和使用说明，不依赖旧 CLI。
- 项目级和用户级初始化都能建立正确目录与 Claude Code 软链，并保持幂等。
- 自建 Skill 可安装到项目级或用户级，且目标是指向权威源码的软链。
- 第三方 Skill 只能通过 `external/skills.json` 中的具体条目安装。
- 第三方清单可新增来源、刷新上游 Skill 列表和移除来源。
- 审计不再依赖插件 marketplace，也不产生 lock/state 文件。
- 自动化测试覆盖成功、幂等、冲突、范围、清单门禁、更新和卸载。
