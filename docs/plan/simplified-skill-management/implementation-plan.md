# Skill 管理体系收敛实施计划

日期：2026-07-17

## Task 1：建立新基线

- [x] 只读核对 Codex 与 Claude Code 的官方目录。
- [x] 盘点现有 `my-skills` CLI、`skill-manage`、清单、测试和插件文件。
- [x] 明确 catalog、lock/state 和 plugin marketplace 均不进入目标体系。

## Task 2：收敛 my-skills

- [x] 删除仓库根目录的 `bin/my-skills` 管理入口。
- [x] 删除 `.claude-plugin/marketplace.json`。
- [x] 将 `external/skills.json` 改为来源加具体 Skill 的可信清单。
- [x] 重写 README 的定位、目录结构、安装入口和维护工作流。

## Task 3：改造 skill-manage

- [x] 在 Skill 内实现确定性管理脚本。
- [x] 实现项目级和用户级目录初始化。
- [x] 实现自建与第三方 Skill 的安装、更新和卸载。
- [x] 实现第三方来源新增、刷新、移除和清单门禁。
- [x] 重写库存与范围审计。
- [x] 更新 `SKILL.md` 与 Codex 展示元数据。

## Task 4：测试与验收

- [x] 将旧 CLI 测试迁移为 `skill-manage` 测试。
- [x] 覆盖项目级、用户级、冲突、幂等和破坏性操作确认。
- [x] 用本地模拟第三方仓库验证新增、刷新、安装、更新和卸载。
- [x] 运行仓库真实清单审计和 Python/JSON/Git 静态检查。
- [x] 确认测试不修改真实用户目录或业务项目。

## Task 5：交付

- [x] 审查最终 diff 和历史兼容影响。
- [x] 记录开发偏差与测试结论。
- [x] 提交 feature 分支，不直接修改或合并 `main`。
