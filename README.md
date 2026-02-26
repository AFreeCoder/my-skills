# My Skills

集中管理的 AI Agent Skills 仓库，供多端共享使用。

## 目录结构

```
my-skills/
├── .claude-plugin/
│   └── marketplace.json   ← CC Switch 发现 skills 的清单
├── skills/                ← 所有 skills 存放于此
│   ├── <skill-name>/
│   │   └── SKILL.md
│   └── ...
└── README.md
```

各端按需加载。

## 接入方式

### Claude Code / Codex（Mac 本地）

通过 CC Switch 添加本仓库，自动发现并同步所有 Skills。

### OpenClaw（VPS）

1. `git clone` 本仓库到服务器
2. 在 `openclaw.json` 中配置 `skills.load.extraDirs` 指向 clone 目录下的 `skills/`
3. 定期 `git pull` 更新

## Skill 规范

遵循 [AgentSkills](https://agentskills.io) 规范：

```
skill-name/
├── SKILL.md          ← 必需：frontmatter + 指令
├── references/       ← 可选：参考文档
├── scripts/          ← 可选：可执行脚本
├── prompts/          ← 可选：提示词模板
└── assets/           ← 可选：模板、图片等资源
```

## 编辑工作流

1. 在本地工作副本中编辑 Skill 文件
2. `git commit && git push`
3. CC Switch 自动同步 / OpenClaw 定期 pull
