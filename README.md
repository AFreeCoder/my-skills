# My Skills

AFreeCoder 自建 AI Agent Skills 的集中源码仓库。

本仓库只维护自建 Skill，不收录或复制官方、第三方以及宿主管理的 Skill。第三方 Skill 在具体项目需要时，按照其上游说明安装到项目级 Skill 目录。

## 目录结构

```text
my-skills/
├── .claude-plugin/
│   └── marketplace.json   # 4 个自建 Skill 的兼容清单
├── skills/                # 自建 Skill 的权威源码
│   └── <skill-name>/
│       └── SKILL.md
└── README.md
```

## 当前收录

当前共收录 `4` 个自建 Skill。

| Skill | 说明 |
| --- | --- |
| `apipool-push-deploy` | 审查 APIPool 生产发布风险，验证 GitHub Actions 自动部署链路、备份、回滚和线上状态。 |
| `apipool-sync-upstream` | 审慎同步 APIPool 的 `upstream/main`，评估上游变更对本地长期定制的影响并完成合入验证。 |
| `push-deploy` | 通用发布门禁：审计发布历史、监控 CI/CD、核查备份与回滚准备并验证线上服务。 |
| `webpage-clipper` | 将网页剪裁为本地 Markdown 并下载图片，用于笔记与资料归档。 |

## 项目级接入

在需要使用 Skill 的具体项目根目录中，逐个创建软链。不要把整个 `skills/` 目录链接到用户级全局目录。

```bash
MY_SKILLS_HOME="${MY_SKILLS_HOME:-$HOME/project/my-skills}"

mkdir -p .agents/skills
ln -s "$MY_SKILLS_HOME/skills/push-deploy" .agents/skills/push-deploy
```

一次启用多个自建 Skill 时，仍然为每个 Skill 建立独立软链：

```bash
ln -s "$MY_SKILLS_HOME/skills/apipool-sync-upstream" .agents/skills/apipool-sync-upstream
ln -s "$MY_SKILLS_HOME/skills/webpage-clipper" .agents/skills/webpage-clipper
```

Claude Code 可以复用同一个项目级目录：

```bash
mkdir -p .claude
ln -s ../.agents/skills .claude/skills
```

项目不再需要某个 Skill 时，只删除项目中的软链，不删除本仓库中的源码。

## 第三方 Skill

官方和第三方 Skill 不进入本仓库，也不通过 CC Switch 或用户级全局目录统一同步。需要时在具体项目中按照上游安装说明安装，并把生效范围限制在该项目的 `.agents/skills/`。

第三方 Skill 的更新、版本固定和运行时依赖由使用它的项目自行负责。

## 更新自建 Skill

在本仓库更新源码并推送远程后，其他机器只需更新这一份仓库：

```bash
git -C "$MY_SKILLS_HOME" pull --ff-only
```

项目中的软链会直接读取更新后的源码，无需重新复制或同步。

## Skill 规范

遵循 [AgentSkills](https://agentskills.io) 规范：

```text
skill-name/
├── SKILL.md          # 必需：frontmatter + 指令
├── references/       # 可选：参考文档
├── scripts/          # 可选：可执行脚本
├── prompts/          # 可选：提示词模板
└── assets/           # 可选：模板、图片等资源
```

## 编辑工作流

1. 在功能分支和隔离 worktree 中编辑自建 Skill。
2. 检查 `SKILL.md` frontmatter 至少包含 `name` 和 `description`。
3. 新增或删除自建 Skill 时，同步更新 `.claude-plugin/marketplace.json` 和本 README。
4. 完成验证后提交、合入 `main` 并推送远程。
