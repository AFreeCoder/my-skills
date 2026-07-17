---
name: skill-manage
description: 管理 AFreeCoder 的 Skills。用于用户要求把自建或第三方 Skill 安装到项目级或用户级、更新已安装 Skill、在 AFreeCoder/my-skills 中创建或维护自建 Skill，以及新增、修改、移除或审计第三方 Skills 清单。遇到“安装 skill”“全局/用户级 skill”“项目级 skill”“更新 skill”“维护 skill 清单”“同步 marketplace/README”等请求时使用。
---

# Skill Manage

## 核心边界

- 自建 Skill 的唯一事实源是 `AFreeCoder/my-skills`，本机默认目录为
  `/Users/afreecoder/project/my-skills`。
- 第三方 Skill 只在 `external/skills.json` 保存来源元数据，不把第三方源码复制进本仓库。
- 用户没有明确范围时默认项目级。只有明确说“用户级”“全局”或等价表达时才使用全局安装。
- 安装、更新与清单维护是三类不同任务。先判断用户要改变什么，再选择命令。
- 不自动覆盖冲突路径，不自动删除已有 Skill，不把远程推送视为普通清单编辑的一部分。

## 第一步：建立当前事实

1. 解析权威仓库目录：优先使用 `MY_SKILLS_HOME`，否则使用
   `/Users/afreecoder/project/my-skills`。
2. 读取当前目录和目标项目生效的 `AGENTS.md`。
3. 运行 `git -C "$MY_SKILLS_HOME" status --short --branch` 和
   `git -C "$MY_SKILLS_HOME" worktree list`。
4. 运行 `my-skills list`，区分：
   - `self-built`：本仓库维护的自建 Skill。
   - `favorite`：`external/skills.json` 收藏的第三方来源。
   - 用户直接给出的 `owner/repo`、URL 或 Git remote：未收藏的第三方来源。
5. 如果任务会修改本仓库，必须使用独立 feature 分支和独立 worktree；不要直接在 `main` 开发。

如果名称同时出现在自建库存和第三方清单中，先停止并修复清单冲突，不要猜测用户想安装哪一个。

## 安装路由

### 项目级安装自建 Skill

先确认目标项目路径，再运行：

```bash
my-skills add --project <project-path> <skill-name>
```

预期结果：

- `<project>/.agents/skills/<skill-name>` 指向权威仓库源码。
- `<project>/.claude/skills` 指向 `../.agents/skills`。

命令遇到普通文件、普通目录、断链或指向其他来源的软链时会失败。报告冲突路径，不覆盖、不删除。

### 用户级安装自建 Skill

只在用户明确要求用户级或全局安装时运行：

```bash
npx --yes skills@latest add "$MY_SKILLS_HOME" --skill <skill-name> --global
```

默认保留安装器确认提示。只有用户明确要求无交互执行时才追加 `--yes`；只有用户指定目标 Agent
时才追加 `--agent <agent>`。安装后运行：

```bash
npx --yes skills@latest list --global --json
```

确认目标 Skill 和目标 Agent 均已登记。不要顺手清理其他用户级 Skill。

### 项目级安装第三方 Skill

先切换到目标项目，再通过收藏别名或原始来源安装：

```bash
cd <project-path>
my-skills add <favorite-name-or-owner/repo> [--skill <child-skill>]
```

第三方项目级安装依赖当前工作目录。不要只传 `--project` 后在其他目录执行。安装后用
`npx --yes skills@latest list --project --json` 验证，并检查项目内实际入口。

### 用户级安装第三方 Skill

只有用户明确要求用户级或全局安装时运行：

```bash
my-skills add <favorite-name-or-owner/repo> --scope global [--skill <child-skill>]
```

安装后用 `npx --yes skills@latest list --global --json` 验证。

## 更新路由

先区分“更新权威源码”和“更新已安装副本”。

### 更新自建 Skill 源码

1. 在 `my-skills` 的独立 feature worktree 中修改 `skills/<name>/`。
2. 保持目录名与 `SKILL.md` frontmatter 的 `name` 一致。
3. 新增、重命名或删除 Skill 时，同步 marketplace 和 README；仅修改内容时不要制造无关清单变更。
4. 运行本 Skill 的清单审计和相关功能测试。
5. 只在用户要求时推送远程；不得从已安装副本反向覆盖权威源码。

项目级软链会直接读取更新后的权威源码，不需要重新安装。使用 `skills` CLI 产生的用户级或复制型
安装，按实际安装器状态重新安装或显式更新，并再次验证。

### 更新第三方已安装 Skill

项目级：

```bash
cd <project-path>
npx --yes skills@latest update <skill-name> --project
```

用户级：

```bash
npx --yes skills@latest update <skill-name> --global
```

批量更新前先列出目标范围和变更对象。不要因为更新一个 Skill 而默认更新全部 Skill。

## 维护自建 Skill 清单

自建库存由三处共同表达，新增、重命名或删除时必须一起维护：

1. `skills/<name>/SKILL.md` 和同目录资产。
2. `.claude-plugin/marketplace.json` 的 `plugins[].skills`。
3. README 的自建 Skill 数量与说明表。

新增 Skill 时至少检查：

- 名称为小写字母、数字和连字符，目录名与 frontmatter `name` 一致。
- `description` 说明真实触发场景，而不是只复述标题。
- 需要脚本或参考资料时放在本 Skill 目录内，并从 `SKILL.md` 明确路由。
- 如需 Codex 展示信息，添加 `agents/openai.yaml`。

过程文档遵循仓库 `docs/requirements|design|plan|dev|test/<feature>/` 规范，不把设计决策写进计划。

## 维护第三方 Skill 清单

新增收藏项优先运行：

```bash
my-skills external add <name> <source> \
  --scope project --description <description> --no-git
```

在 feature worktree 中使用 `--no-git`，让清单与其余修改统一评审和提交。不要使用命令的默认自动
提交/推送行为，除非用户明确要求这一动作。

修改或移除 `external/skills.json` 条目前，先核对：

- 上游来源仍存在，名称和所有者没有迁移。
- 别名稳定且不与自建 Skill 重名。
- `scope` 只能是 `project` 或 `global`，默认使用 `project`。
- 一个上游仓库只保留一个收藏项；子 Skill 通过安装参数选择，不重复建条目。
- 删除收藏项不会删除任何已安装 Skill；若用户还要卸载，作为独立操作处理。

来源可联网核实时优先使用上游仓库或官方文档。无法核实时说明未验证，不把推测写进清单。

## 审计与验证

修改本仓库后运行：

```bash
python3 "$MY_SKILLS_HOME/skills/skill-manage/scripts/audit_inventory.py" \
  --repo "$MY_SKILLS_HOME"
bash "$MY_SKILLS_HOME/tests/test-my-skills.sh"
npx --yes skills@latest add "$MY_SKILLS_HOME" --list
git -C "$MY_SKILLS_HOME" diff --check
git -C "$MY_SKILLS_HOME" status --short
```

如果实际修改发生在 feature worktree，把 `MY_SKILLS_HOME` 指向该 worktree 后再运行。审计失败只修复
当前任务引入的问题；发现既有漂移时单独报告，不擅自清理。

## 最终汇报

向用户明确说明：

- 操作类型、Skill 名称、来源与安装范围。
- 修改或安装到了哪些路径。
- 验证命令与结果。
- 是否存在冲突、未验证上游、待提交或待推送状态。
- 没有执行的高影响动作，例如用户级清理、删除、提交或推送。
