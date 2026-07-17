# Skill 管理体系 npx 迁移设计

日期：2026-07-17

## 背景

原体系由 `skills/skill-manage/scripts/skill_manage.py`（957 行）承担准入清单、目录初始化、安装、更新、卸载与审计。方案评审确认两点，使原设计的主要复杂度失去依据：

1. `external/skills.json` 的实际定位是"常用 Skill 收藏"，而非安全准入清单；准入校验、staged 安装、manifest diff、更新确认门禁等约 60% 的脚本代码服务于一个并不需要的门禁模型。
2. 源码查证（vercel-labs/skills、openai/codex）：
   - skills CLI 的 canonical 目录就是 `.agents/skills`（项目级与 `~/.agents/skills` 用户级），采用"单一实体 + 各 agent 软链"分发，与本体系模型同构；其 installer 显式兼容 `.claude/skills -> ../.agents/skills` 目录软链布局（realpath 判同后跳过建链）。
   - Codex 用户级 Skill 目录已是 `~/.agents/skills`；`~/.codex/skills` 在 loader 中标注为 Deprecated，仅向后兼容。

## 决策

1. 安装、更新、卸载全部交给 `npx skills`；`skill_manage.py`、`tests/`、`external/skills.json` 退役删除。
2. 自建 Skill 同样经 npx 安装（来源 `AFreeCoder/my-skills`，公开仓库），不再以软链仓库源码的方式安装。"改完即生效"的损失由 skill-manage 新闭环补偿：修改 → 合入 `main` → 推送远程 → `npx skills update` 刷新本机安装；推送是闭环的默认动作，不逐次询问。
3. `skill-manage` 从"调脚本的控制面"转型为"编排 npx + git 的流程技能"，只保留 SKILL.md 与 `agents/openai.yaml`。
4. 第三方收藏迁入 README 表格（Skill、来源、说明），只记录、不准入、不保存安装状态。
5. 开发期高频调试保留逃生舱：`ln -sfn` 临时直连仓库源码，定稿后恢复 npx 安装。
6. 既有 `.claude/skills -> ../.agents/skills` 目录软链保留；全局安装不传 `-a codex`，避免写入已弃用目录。

## 迁移步骤

1. 仓库改造（本 feature）：删除脚本、测试与第三方清单；重写 README 与 skill-manage SKILL.md。
2. 合入 `main` 并推送远程。
3. 全局规范改写：`~/.codex/AGENTS.md`（即 `~/.claude/CLAUDE.md`）的"Skill 管理"一节替换为 npx 约定与闭环流程。
4. 存量迁移：卸载 `~/.agents/skills/skill-manage` 旧软链后用 npx 重装；各项目历史上手工复制安装的第三方 Skill，后续逐项目删除并用 npx 重装，以获得 `npx skills update` 能力（npx 依赖其自身 lock 记录识别来源）。

## 影响与残留

- 修改自建 Skill 的生效路径变长（需推送 + 刷新），由闭环流程自动执行兜底。
- 仓库公开分发：自建 Skill 内容不得包含敏感信息。
- 历史过程文档按规范冻结不动；本次为唯一新增设计文档。
