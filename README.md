# My Skills

AFreeCoder 的 Skill 唯一事实源。

本仓库保存两类信息：自建 Skill 的完整源码，以及允许安装的第三方 Skill 来源清单。目录初始化、
安装、更新、卸载和审计统一由仓库内的 `skill-manage` Skill 负责，仓库根目录不再提供独立管理 CLI。

## 目录结构

```text
my-skills/
├── external/
│   └── skills.json                 # 第三方来源和具体 Skill 清单
├── skills/
│   ├── skill-manage/               # Skill 管理控制面
│   │   ├── scripts/skill_manage.py
│   │   └── SKILL.md
│   └── <skill-name>/               # 自建 Skill 权威源码
│       └── SKILL.md
├── tests/
│   └── test_skill_manage.py
└── README.md
```

本仓库不使用 `catalog/`、lock/state、`plugin.json` 或 `marketplace.json`。`external/skills.json`
就是唯一的第三方 Skill 清单。

## 当前收录

当前共收录 `7` 个自建 Skill。

| Skill | 说明 |
| --- | --- |
| `apipool-push-deploy` | 审查 APIPool 生产发布风险，验证 GitHub Actions 自动部署链路、备份、回滚和线上状态。 |
| `apipool-sync-upstream` | 审慎同步 APIPool 的 `upstream/main`，评估上游变更对本地长期定制的影响并完成合入验证。 |
| `classic-to-default-sync` | 审计 `new-api` 的 classic 前端提交，并把缺失功能同步到 default 前端。 |
| `i18n-translate` | 维护 `new-api` default 前端六种语言的翻译完整性与一致性。 |
| `push-deploy` | 通用发布门禁：审计发布历史、监控 CI/CD、核查备份与回滚准备并验证线上服务。 |
| `skill-manage` | 维护本仓库事实源，并管理用户级和项目级 Skill 的完整生命周期。 |
| `webpage-clipper` | 将网页剪裁为本地 Markdown 并下载图片，用于笔记与资料归档。 |

第三方具体 Skill 由 `external/skills.json` 中各来源的 `skills` 数组表达，不在本仓库复制上游源码。

## 统一安装目录

Codex 使用 `.agents/skills`；Claude Code 通过软链复用同一目录。

用户级：

```text
~/.agents/skills/
~/.claude/skills -> ../.agents/skills
```

项目级：

```text
<project>/.agents/skills/
<project>/.claude/skills -> ../.agents/skills
```

`~/.codex/skills` 不属于本体系，不会被初始化、写入或清理。

## 管理入口

通常直接在 Codex 或 Claude Code 中调用 `skill-manage`。需要手工执行或排障时，使用 Skill 自带脚本：

```bash
MANAGER="$HOME/project/my-skills/skills/skill-manage/scripts/skill_manage.py"
python3 "$MANAGER" list
python3 "$MANAGER" audit
```

仓库位于其他位置时，可设置 `MY_SKILLS_HOME`，或者在命令最前面传入 `--repo <path>`。

## 首次自举

在尚未安装 `skill-manage` 时，可直接运行仓库内脚本完成用户级初始化和安装：

```bash
python3 "$MANAGER" init --scope user
python3 "$MANAGER" install skill-manage --scope user
```

第二条命令会在 `~/.agents/skills/skill-manage` 创建指向本仓库源码的软链。之后 Codex 和
Claude Code 都从同一位置加载它。

## 安装与维护

未明确范围时默认为当前项目。也可以显式指定项目：

```bash
python3 "$MANAGER" install push-deploy
python3 "$MANAGER" install push-deploy --project /path/to/project
python3 "$MANAGER" install push-deploy --scope user
```

第三方 Skill 必须先存在于 `external/skills.json`。安装命令只接受具体 Skill 名称，不接受未登记的
`owner/repo` 或 URL：

```bash
python3 "$MANAGER" install apple-design --project /path/to/project
python3 "$MANAGER" install vercel-optimize --scope user
```

更新与卸载：

```bash
python3 "$MANAGER" update apple-design --project /path/to/project
python3 "$MANAGER" update apple-design --project /path/to/project --yes
python3 "$MANAGER" uninstall apple-design --project /path/to/project --yes
```

第三方更新第一次运行会展示文件变化；只有显式传入 `--yes` 才会替换目录。自建 Skill 通过软链
直接读取权威源码，不需要重新安装。

## 第三方 Skill 清单

每个来源保存来源别名、Git 来源、说明以及扫描得到的具体 Skill 名称、相对路径和说明。清单不保存
默认安装范围，也不保存本机安装状态。

新增来源时会立即获取上游并发现其中的 `SKILL.md`：

```bash
python3 "$MANAGER" external add owner-skills owner/repo \
  --description "第三方 Skill 来源说明"
```

来源包含重复副本或只希望信任其中一部分时，明确选择一个或多个相对路径：

```bash
python3 "$MANAGER" external add owner-skills owner/repo \
  --description "第三方 Skill 来源说明" \
  --skill-path skills/selected-skill
```

刷新一个来源或全部来源：

```bash
python3 "$MANAGER" external refresh owner-skills
python3 "$MANAGER" external refresh
```

刷新默认只更新已经获准的 Skill 元数据，不会自动扩大可信清单。只有在人工确认希望吸收上游新增
Skill 时，才显式重新发现全部内容：

```bash
python3 "$MANAGER" external refresh owner-skills --discover-new
```

从清单移除来源不会卸载已经复制到项目或用户目录的 Skill：

```bash
python3 "$MANAGER" external remove owner-skills --yes
```

清单维护只修改 JSON，不自动执行 Git commit、push 或合并。

## 安全边界

- `.claude/skills` 已是普通目录、断链或错误软链时停止，不覆盖。
- 自建 Skill 只创建和移除指向本仓库源码的软链。
- 第三方首次安装不覆盖已有文件或目录。
- 第三方更新和卸载需要显式确认。
- 发现未登记 Skill、名称冲突或上游路径变化时停止并报告。
- 真实目录迁移必须先做独立只读审计，不属于 `init` 的隐式行为。

## 开发与验证

所有改动使用独立 feature 分支和 worktree。完成修改后运行：

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 skills/skill-manage/scripts/skill_manage.py audit
python3 -m py_compile skills/skill-manage/scripts/skill_manage.py
jq empty external/skills.json
git diff --check
```

过程文档遵循 `docs/requirements|design|plan|dev|test/<feature>/` 目录规范。
