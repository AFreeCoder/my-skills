# My Skills

AFreeCoder 自建 AI Agent Skills 的集中源码仓库。

本仓库只维护自建 Skill，不收录或复制官方、第三方以及宿主管理的 Skill。第三方 Skill 在具体项目需要时，按照其上游说明安装到项目级 Skill 目录。

## 目录结构

```text
my-skills/
├── .claude-plugin/
│   └── marketplace.json   # 4 个自建 Skill 的兼容清单
├── bin/
│   └── my-skills          # 项目级 Skill 链接命令
├── external/
│   └── skills.json
├── skills/                # 自建 Skill 的权威源码
│   └── <skill-name>/
│       └── SKILL.md
├── tests/
│   └── test-my-skills.sh
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

在需要使用 Skill 的具体项目中，使用 `my-skills` 命令创建项目级目录和软链。
不要把整个 `skills/` 目录链接到用户级全局目录。

查看当前仓库维护的自建 Skill 和收藏的第三方 Skill：

```bash
my-skills list
```

```bash
my-skills init
my-skills add push-deploy
```

一次启用多个自建 Skill 时，显式列出需要的名称：

```bash
my-skills link apipool-sync-upstream webpage-clipper
```

为其他项目配置时，可以指定项目路径：

```bash
my-skills init --project /path/to/project
my-skills add --project /path/to/project push-deploy
```

命令会创建：

```text
.agents/skills/
.claude/skills -> ../.agents/skills
```

项目不再需要某个自建 Skill 时，只删除项目中的软链，不删除本仓库中的源码：

```bash
my-skills unlink push-deploy
```

命令是幂等的，但不会覆盖已有普通目录、普通文件或指向其他位置的软链；遇到冲突会
停止并报告具体路径。

## 本机命令安装

本机推荐通过 PATH 中的用户级软链调用仓库内脚本：

```bash
mkdir -p "$HOME/bin"
ln -s "$HOME/project/my-skills/bin/my-skills" "$HOME/bin/my-skills"
```

如果仓库不在默认位置，可设置：

```bash
export MY_SKILLS_HOME=/path/to/my-skills
```

## 第三方 Skill

官方和第三方 Skill 不进入本仓库，也不通过 CC Switch 或用户级全局目录统一同步。需要时在具体项目中按照上游安装说明安装，并把生效范围限制在该项目的 `.agents/skills/`。

第三方 Skill 的更新、版本固定和运行时依赖由使用它的项目自行负责；`my-skills`
命令只管理本仓库 `skills/` 下的自建 Skill。

本仓库可以维护第三方 Skill 仓库地址收藏清单：

```json
{
  "third_party": [
    {
      "name": "vercel-agent-skills",
      "source": "vercel-labs/agent-skills",
      "scope": "project",
      "description": "Vercel Labs Agent Skills collection"
    },
    {
      "name": "emilkowalski-skills",
      "source": "emilkowalski/skills",
      "scope": "project",
      "description": "Emil Kowalski design and animation skills collection"
    }
  ]
}
```

新增收藏项使用命令维护，避免手写 JSON：

```bash
my-skills external add emilkowalski-skills emilkowalski/skills --description "Emil Kowalski design and animation skills collection"
my-skills external add some-global-skill owner/repo --scope global --description "Installed globally by default"
```

默认写入本仓库的 `external/skills.json` 时，命令会自动执行 `git add`、`git commit`
和 `git push`，提交信息为 `chore: add external skill <name>`。如果只想修改本地
JSON，不提交和推送，可传 `--no-git`；如果要提交但暂不推送，可传 `--no-push`。

`my-skills add` 会先查本仓库自建 Skill，找不到再查收藏清单；也可以直接传入上游
来源：

```bash
my-skills add push-deploy
my-skills add vercel-agent-skills --list
my-skills add vercel-agent-skills --skill vercel-optimize --yes
my-skills add vercel-labs/agent-skills --skill vercel-optimize --yes
my-skills add emilkowalski-skills --list
my-skills add emilkowalski-skills --skill apple-design --yes
```

收藏清单命中的第三方 Skill 会包装为 `npx skills@latest add <source>`。默认保留上游
确认提示；需要跳过确认时显式传 `--yes`。清单中的 `scope` 为 `global` 时会自动追加
`--global`，临时改为项目级安装可传 `--scope project`。

同一个外部仓库包含多个子 Skill 时，本清单只收藏仓库 source，不拆成多个重复条目。
安装具体子 Skill 时把 `--skill <name>` 透传给 `skills@latest`；查看子 Skill 清单时
使用 `--list`。

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
4. 修改 `bin/my-skills` 时运行 `bash tests/test-my-skills.sh`。
5. 完成验证后提交、合入 `main` 并推送远程。
