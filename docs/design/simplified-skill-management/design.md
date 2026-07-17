# Skill 管理体系收敛设计

日期：2026-07-17

## 总体结构

```text
my-skills/
├── skills/
│   ├── skill-manage/
│   │   ├── SKILL.md
│   │   └── scripts/skill_manage.py
│   └── <self-built-skill>/
├── external/
│   └── skills.json
└── README.md
```

- `skills/<name>/`：自建 Skill 权威源码。
- `external/skills.json`：第三方来源及其中允许安装的具体 Skill。
- `skills/skill-manage/`：管理控制面，包含编排说明和确定性脚本。
- README：由实际源码和第三方清单表达的人类可读说明，不承担机器注册职责。

## 运行时目录

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

`skill-manage` 先检查 `.agents/skills` 和 `.claude/skills` 的现状，再执行创建。任何普通文件、
普通目录、断链或指向其他位置的软链都视为冲突。真实用户目录与项目迁移不属于初始化命令的隐式职责。

## 第三方清单模型

`external/skills.json` 以来源为分组单位，每个来源保存可安装的具体 Skill：

```json
{
  "third_party": [
    {
      "name": "upstream-alias",
      "source": "owner/repo",
      "description": "来源说明",
      "skills": [
        {
          "name": "skill-name",
          "path": "skills/skill-name",
          "description": "来自上游 SKILL.md 的说明"
        }
      ]
    }
  ]
}
```

`name` 是来源别名，不是安装范围。安装范围永远由当前命令决定。`skills` 是允许安装的具体条目；
安装时按 Skill 名称全局查找，名称与自建 Skill或其他第三方 Skill 冲突时审计失败。

`external add` 获取一次上游并生成 `skills`；`external refresh` 重新发现上游 `SKILL.md`，更新路径和
说明。清单不保存本机安装状态、解析后的 commit 或内容哈希。

## 管理脚本

入口为：

```bash
python3 skills/skill-manage/scripts/skill_manage.py <command>
```

主要命令：

| 命令 | 职责 |
| --- | --- |
| `list` | 合并展示自建和第三方具体 Skill |
| `init` | 初始化项目级或用户级共享目录 |
| `install` | 安装已登记的自建或第三方 Skill |
| `update` | 检查并更新指定 Skill |
| `uninstall` | 安全移除指定范围内的安装项 |
| `external add` | 新增第三方来源并发现 Skill |
| `external refresh` | 刷新一个或全部第三方来源 |
| `external remove` | 从清单移除来源，不触碰已安装目录 |
| `audit` | 审计仓库库存；可选审计用户级或项目级目录 |

脚本通过自身路径解析仓库，也允许 `MY_SKILLS_HOME` 或 `--repo` 覆盖。测试通过
`SKILL_MANAGE_USER_HOME` 隔离用户级目录。

## 安装实现

### 自建 Skill

目标为 `.agents/skills/<name>`，内容是指向 `my-skills/skills/<name>` 的绝对软链。正确软链重复安装
视为成功；其他软链、普通文件或普通目录视为冲突。

### 第三方 Skill

1. 从清单定位来源与相对路径。
2. 在临时目录克隆 Git 来源；本地路径仅用于受控开发和测试。
3. 验证目标目录存在 `SKILL.md`，且 frontmatter `name` 与清单一致。
4. 将完整 Skill 目录复制到目标 `.agents/skills/<name>`。
5. 首次安装不覆盖已有目标；更新使用同目录临时副本和原子替换，失败时恢复原目录。

不在目标目录写入管理标记。更新和卸载依靠用户明确指定的 Skill 名称、清单门禁以及目标类型检查。

## 审计模型

仓库审计检查：

- 自建目录名、frontmatter 名称和说明。
- README 自建数量及表格完整性。
- 第三方来源别名、来源地址、具体 Skill 名称、路径和说明。
- 自建与第三方以及不同第三方来源之间的名称冲突。
- 仓库不存在 `.claude-plugin/marketplace.json`、`.codex-plugin/plugin.json`、`skills-lock.json` 等非目标文件。

范围审计检查：

- `.agents/skills` 是真实目录。
- `.claude/skills` 是指向该目录的正确软链。
- 自建安装项是正确源码软链。
- 第三方安装项是包含有效 `SKILL.md` 的普通目录。
- 目标中不存在事实源未登记的 Skill。

## 安全边界

- `install` 不覆盖任何现有冲突路径。
- `update` 和 `uninstall` 对第三方目录要求 `--yes`。
- `external remove` 要求 `--yes`，但只修改清单。
- Git 获取失败、上游路径变化或 frontmatter 不一致时不修改目标。
- 脚本不执行 Git commit、push、merge，也不修改 `~/.codex/skills`。
