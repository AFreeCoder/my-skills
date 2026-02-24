# My Skills

集中管理的 AI Agent Skills 仓库，供多端共享使用。

## 目录结构

```
my-skills/
├── shared/          ← 所有端共享的 Skills
├── openclaw/        ← OpenClaw 专属 Skills
├── claude-code/     ← Claude Code 专属 Skills
└── codex/           ← Codex 专属 Skills
```

## 接入方式

### OpenClaw (VPS)

在 `openclaw.json` 中配置 `skills.load.extraDirs`：

```json
{
  "skills": {
    "load": {
      "extraDirs": ["/home/work/.openclaw/my-skills/shared"]
    }
  }
}
```

### Claude Code (本地 Mac)

将 shared skills 目录链接到 Claude Code 的项目 skills 目录。

### Codex (本地 Mac)

类似 Claude Code 的处理方式。

## Git 工作流

- 创建/修改 Skill → git commit + push
- 其他端 git pull → 自动生效
- OpenClaw 有 watcher，检测到变化后下次会话自动加载

## Skill 规范

遵循 [AgentSkills](https://agentskills.io) 规范：

```
skill-name/
├── SKILL.md          ← 必需：frontmatter + 指令
├── references/       ← 可选：参考文档（按需加载）
├── scripts/          ← 可选：可执行脚本
└── assets/           ← 可选：模板、图片等资源
```
