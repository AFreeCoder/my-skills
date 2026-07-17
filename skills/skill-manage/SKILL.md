---
name: skill-manage
description: 管理 AFreeCoder 的 Skill 事实源和共享安装目录。用于创建或维护 my-skills 中的自建 Skill、登记或刷新第三方 Skill 清单，以及在用户级或项目级初始化、安装、更新、卸载和审计 Skill。遇到“安装 Skill”“用户级或全局 Skill”“项目级 Skill”“更新 Skill”“维护第三方清单”“检查 Codex 与 Claude Code Skill 是否一致”等请求时使用。
---

# Skill Manage

## 体系边界

- `AFreeCoder/my-skills` 是唯一事实源；本机默认目录为 `/Users/afreecoder/project/my-skills`。
- `skills/<name>/` 保存自建 Skill 源码。
- `external/skills.json` 保存第三方来源及其中允许安装的具体 Skill。
- `.agents/skills` 是用户级和项目级的实际安装目录。
- `.claude/skills` 必须是指向 `../.agents/skills` 的软链。
- 不管理 `~/.codex/skills`，不创建 catalog、lock/state、plugin 或 marketplace 文件。
- 用户未明确范围时默认项目级；只有明确说“用户级”“全局”时才使用用户级。

确定性操作统一由本 Skill 的脚本执行：

```bash
MY_SKILLS_HOME=${MY_SKILLS_HOME:-/Users/afreecoder/project/my-skills}
MANAGER="$MY_SKILLS_HOME/skills/skill-manage/scripts/skill_manage.py"
python3 "$MANAGER" --help
```

## 第一步：建立事实

1. 解析 `MY_SKILLS_HOME` 并读取当前目录、目标项目和仓库生效的 `AGENTS.md`。
2. 运行：

   ```bash
   git -C "$MY_SKILLS_HOME" status --short --branch
   git -C "$MY_SKILLS_HOME" worktree list
   python3 "$MANAGER" audit
   python3 "$MANAGER" list
   ```

3. 区分用户是在维护事实源、改变安装范围，还是迁移已有目录。
4. 修改 `my-skills` 时必须使用独立 feature 分支和 worktree，不直接在 `main` 开发。
5. 迁移真实用户目录或业务项目之前先只读审计；不要把 `init` 当迁移命令。

## 目录初始化

项目级：

```bash
python3 "$MANAGER" init --project <project-path>
```

用户级或全局：

```bash
python3 "$MANAGER" init --scope user
```

预期结构分别为：

```text
<project>/.agents/skills/
<project>/.claude/skills -> ../.agents/skills

~/.agents/skills/
~/.claude/skills -> ../.agents/skills
```

普通目录、普通文件、断链或错误软链均属于冲突。报告精确路径并停止，不覆盖、不删除。

## 安装 Skill

先运行 `list`，确认名称已进入事实源。命令不接受原始 URL 或 `owner/repo`。

项目级：

```bash
python3 "$MANAGER" install <skill-name> --project <project-path>
```

用户级：

```bash
python3 "$MANAGER" install <skill-name> --scope user
```

- 自建 Skill 会软链到 `my-skills/skills/<name>`。
- 第三方 Skill 会从 `external/skills.json` 登记的来源获取并复制到目标目录。
- 首次安装遇到任何已有冲突目标都停止，不尝试判断或覆盖历史内容。

如果用户要求安装的第三方 Skill 尚未登记，先维护清单，再执行安装。不得绕过清单直接调用其他安装器。

## 维护第三方清单

新增来源会扫描上游 `SKILL.md`，把具体名称、路径和说明写入 `external/skills.json`：

```bash
python3 "$MANAGER" external add <source-alias> <owner/repo-or-git-url> \
  --description <description>
```

来源包含重复生成副本，或只希望信任部分 Skill 时，必须显式选择相对路径；该参数可以重复：

```bash
python3 "$MANAGER" external add <source-alias> <owner/repo-or-git-url> \
  --description <description> \
  --skill-path <relative/path/to/skill>
```

刷新默认只更新当前已获准 Skill 的名称、路径和说明，不自动扩大可信清单：

```bash
python3 "$MANAGER" external refresh <source-alias>
```

刷新全部来源：

```bash
python3 "$MANAGER" external refresh
```

只有人工确认要吸收来源中新出现的全部 Skill 时，才运行：

```bash
python3 "$MANAGER" external refresh <source-alias> --discover-new
```

移除来源：

```bash
python3 "$MANAGER" external remove <source-alias> --yes
```

移除来源只修改清单，不卸载任何已安装 Skill。需要同时卸载时，先卸载具体 Skill，再移除来源。
清单命令不自动提交或推送；Git 操作遵循当前任务的明确授权。

## 更新 Skill

自建 Skill 的项目级和用户级安装都是权威源码软链。源码合入后即时生效，运行下面命令只验证软链：

```bash
python3 "$MANAGER" update <self-built-name> [--project <path>|--scope user]
```

第三方更新先获取上游并展示文件变化：

```bash
python3 "$MANAGER" update <third-party-name> --project <path>
```

确认差异后才执行：

```bash
python3 "$MANAGER" update <third-party-name> --project <path> --yes
```

用户级把 `--project <path>` 替换为 `--scope user`。不要把更新单个 Skill 扩大成全部刷新或批量更新。

## 卸载 Skill

```bash
python3 "$MANAGER" uninstall <skill-name> --project <path>
python3 "$MANAGER" uninstall <skill-name> --scope user
```

- 自建 Skill 只移除指向权威源码的软链。
- 第三方 Skill 是普通目录，必须追加 `--yes` 才会删除。
- 目标类型、frontmatter 或来源不符合预期时停止，不强制删除。

## 维护自建 Skill

自建库存只由 `skills/<name>/SKILL.md` 和同目录资产表达，不再同步 marketplace。

新增或修改时检查：

- 名称只使用小写字母、数字和连字符。
- 目录名与 frontmatter `name` 一致。
- `description` 说明真实触发场景。
- 脚本、参考资料和模板位于本 Skill 目录内。
- README 的自建数量和说明表同步更新。
- 相关测试通过。

过程文档遵循 `docs/requirements|design|plan|dev|test/<feature>/`，不要回填已经冻结的历史过程文档。

## 审计与验证

仓库库存：

```bash
python3 "$MANAGER" audit
```

指定范围：

```bash
python3 "$MANAGER" audit --project <project-path>
python3 "$MANAGER" audit --scope user
```

审计会检查事实源格式、名称冲突、README、共享目录拓扑、安装类型和未登记 Skill。它只报告，不自动修复。

修改本仓库后运行：

```bash
python3 -m unittest discover -s "$MY_SKILLS_HOME/tests" -p 'test_*.py' -v
python3 "$MANAGER" audit
python3 -m py_compile "$MANAGER"
jq empty "$MY_SKILLS_HOME/external/skills.json"
git -C "$MY_SKILLS_HOME" diff --check
```

## 最终汇报

明确说明：

- 操作的 Skill、来源和范围。
- 修改或安装到的精确路径。
- 是否创建了 `.claude/skills` 软链。
- 验证命令与结果。
- 冲突、未验证上游和待提交状态。
- 没有执行的迁移、清理、提交、推送或合并动作。
