# Skill 管理 Skill 设计

日期：2026-07-16

## 设计目标

`skill-manage` 是管理流程入口，不重新实现安装器。它负责解析操作意图、确定范围与来源，
再调用仓库已有的 `my-skills` 命令或上游 `skills` CLI，并在修改清单后运行一致性审计。

## 操作分类

| 操作 | 目标 | 默认行为 |
| --- | --- | --- |
| 安装 | 自建或第三方 Skill | 未明确范围时使用项目级 |
| 更新源码 | `my-skills/skills/<name>` | 在独立 feature worktree 修改 |
| 更新安装 | 已安装的第三方 Skill | 显式区分项目级和用户级 |
| 维护清单 | 自建清单或第三方收藏清单 | 先审计，修改后再审计 |

## 来源模型

`my-skills list` 提供统一可发现视图：

- `self-built`：源码位于本仓库 `skills/<name>/`。
- `favorite`：来源记录在 `external/skills.json`，仓库只保存元数据。
- 原始来源：用户直接给出 `owner/repo`、URL 或 Git remote，不要求先进入收藏清单。

同名的自建 Skill 与第三方收藏项不允许共存，避免安装路由产生歧义。

## 安装设计

### 项目级自建 Skill

调用：

```bash
my-skills add --project <project-path> <skill-name>
```

该命令创建 `.agents/skills/<name>` 到权威源码的软链，并确保
`.claude/skills -> ../.agents/skills`。已有冲突路径时失败关闭。

### 用户级自建 Skill

只有用户明确要求用户级安装时，调用：

```bash
npx --yes skills@latest add /Users/afreecoder/project/my-skills \
  --skill <skill-name> --global
```

是否跳过安装器确认由用户授权决定；完成后用 `skills list --global --json` 验证。

### 第三方 Skill

收藏项通过 `my-skills add <alias>` 转交给 `skills@latest`。项目级安装必须把当前目录切换到
目标项目后执行；用户级安装显式传 `--scope global`。原始来源可以直接交给同一命令。

## 自建清单维护

自建 Skill 的库存由三处共同表达：

1. `skills/<name>/SKILL.md`：权威实体。
2. `.claude-plugin/marketplace.json`：仓库级可安装清单。
3. `README.md`：人工可读数量与说明表。

新增、重命名或删除自建 Skill 时必须同步三处。内容更新但名称不变时无需修改注册表；若说明
发生实质变化，应同步 README 展示文案。

## 第三方清单维护

`external/skills.json` 的每个条目包含稳定别名、上游来源、默认范围和说明。新增条目优先调用：

```bash
my-skills external add <name> <source> --scope project \
  --description <description> --no-git
```

`--no-git` 让清单变更留在当前 feature worktree，与其余修改统一评审和提交。修改或移除条目
使用结构化补丁完成。每个上游仓库只保留一个收藏项，具体子 Skill 在安装时用 `--skill` 选择。

## 一致性审计

`skills/skill-manage/scripts/audit_inventory.py` 对以下约束做只读校验：

- 自建 Skill 目录名、frontmatter `name` 与 marketplace 注册名一致。
- 每个 `SKILL.md` 都有非空 `description`。
- README 声明数量和自建 Skill 表格完整。
- 第三方条目名称合法且唯一，来源、范围和说明有效。
- 自建名称与第三方别名不冲突。

审计失败只报告问题，不自动修复或删除。

## 安全边界

- 安装前读取目标项目规则并检查目标路径；冲突时停止。
- 用户级安装、删除、批量迁移、覆盖和远程推送均需明确授权。
- 修改自建源码或仓库清单时遵循独立 feature 分支和独立 worktree。
- 不把第三方源码复制进本仓库，不把已安装副本反向当作权威源码。
