# My Skills

AFreeCoder 的 Skill 唯一事实源：自建 Skill 源码 + 常用第三方 Skill 收藏。

安装、更新、卸载统一使用 [skills CLI](https://github.com/vercel-labs/skills)（`npx -y skills@latest`）；仓库内的 `skill-manage` Skill 负责编排"修改自建 Skill → 推送 → 刷新安装"的闭环。本仓库不再包含管理脚本、准入清单或 lock/state 文件。

## 安装约定

实体目录：项目级 `<project>/.agents/skills/`，用户级 `~/.agents/skills/`（skills CLI 的 canonical 目录）。Codex 直接读取该目录；Claude Code 经 `.claude/skills` 软链读取。

```bash
npx -y skills@latest add <source> --skill <name> -y      # 项目级（默认）
npx -y skills@latest add <source> --skill <name> -g -y   # 用户级
npx -y skills@latest update [<name>] [-g|-p]             # 更新
npx -y skills@latest remove <name>                       # 卸载
```

全局安装不要传 `-a codex`（会写入已弃用的 `~/.codex/skills`；Codex 的全局目录就是 `~/.agents/skills`）。

## 自建 Skill

当前共收录 `9` 个自建 Skill，安装来源均为 `AFreeCoder/my-skills`：

| Skill | 说明 |
| --- | --- |
| `apipool-push-deploy` | 审查 APIPool 生产发布风险，验证 GitHub Actions 自动部署链路、备份、回滚和线上状态。 |
| `apipool-sync-upstream` | 审慎同步 APIPool 的 `upstream/main`，评估上游变更对本地长期定制的影响并完成合入验证。 |
| `classic-to-default-sync` | 审计 `new-api` 的 classic 前端提交，并把缺失功能同步到 default 前端。 |
| `dev-flow` | Issue 驱动的开发流程：小任务全自动直通（创建 issue → 分析 → 实施 → 评审 → 发布），问题排查留档结论、修复与否由用户分流，大需求按阶段独立 issue 留档。 |
| `i18n-translate` | 维护 `new-api` default 前端六种语言的翻译完整性与一致性。 |
| `knowledge-base-manager` | 管理本地 Markdown 知识库与飞书知识库的项目映射和内容双端一致性。 |
| `push-deploy` | 通用发布门禁：审计发布历史、监控 CI/CD、核查备份与回滚准备并验证线上服务。 |
| `skill-manage` | Skill 管理流程：npx 安装约定，以及自建 Skill"修改 → 推送 → 刷新安装"闭环。 |
| `webpage-clipper` | 将网页剪裁为本地 Markdown 并下载图片，用于笔记与资料归档。 |

修改自建 Skill 的流程见 [skills/skill-manage/SKILL.md](skills/skill-manage/SKILL.md)：feature 分支修改 → 合入 `main` → 推送远程 → `npx -y skills@latest update` 刷新本机安装。仓库公开，自建 Skill 内容不放敏感信息。

## 第三方 Skill 收藏

只做记录，不复制上游源码。安装命令：`npx -y skills@latest add <来源> --skill <Skill> [-g] -y`。

| Skill | 来源 | 说明 |
| --- | --- | --- |
| `deploy-to-vercel` | `vercel-labs/agent-skills` | 部署应用到 Vercel 并返回链接。 |
| `vercel-cli-with-tokens` | `vercel-labs/agent-skills` | 用 token 认证操作 Vercel CLI。 |
| `vercel-composition-patterns` | `vercel-labs/agent-skills` | 可扩展的 React 组合模式。 |
| `vercel-optimize` | `vercel-labs/agent-skills` | Vercel 成本与性能优化。 |
| `vercel-react-best-practices` | `vercel-labs/agent-skills` | Vercel 工程的 React/Next.js 性能实践。 |
| `vercel-react-native-skills` | `vercel-labs/agent-skills` | React Native / Expo 最佳实践。 |
| `vercel-react-view-transitions` | `vercel-labs/agent-skills` | React View Transition 动画实现指南。 |
| `web-design-guidelines` | `vercel-labs/agent-skills` | 按 Web 界面规范审查 UI 代码。 |
| `writing-guidelines` | `vercel-labs/agent-skills` | 按写作规范审查文档文风。 |
| `animation-vocabulary` | `emilkowalski/skills` | 动效术语反查词典。 |
| `apple-design` | `emilkowalski/skills` | Apple 风格界面与动效设计。 |
| `emil-design-eng` | `emilkowalski/skills` | Emil Kowalski 的 UI 打磨哲学。 |
| `find-animation-opportunities` | `emilkowalski/skills` | 发现界面中值得添加动效的位置。 |
| `improve-animations` | `emilkowalski/skills` | 动效审计与改进路线图。 |
| `review-animations` | `emilkowalski/skills` | 高标准动效代码评审。 |
| `shipany-page-builder` | `AFreeCoder/shipany-template` | 按简述为 ShipAny 项目创建动态页面。 |
| `shipany-quick-start` | `AFreeCoder/shipany-template` | 新 ShipAny 项目的首轮自动定制。 |
| `supabase-to-d1` | `AFreeCoder/shipany-template` | Supabase PostgreSQL 迁移到 Cloudflare D1。 |
| `ui-ux-pro-max` | `nextlevelbuilder/ui-ux-pro-max-skill` | UI/UX 设计知识库（风格、配色、字体、组件）。 |
| `shadcn` | `shadcn-ui/ui` | shadcn/ui 组件与项目管理。 |

## 开发期调试

高频调试某个自建 Skill 时，可临时软链直连仓库源码（改动即时生效），定稿后恢复 npx 安装：

```bash
ln -sfn ~/project/my-skills/skills/<name> ~/.agents/skills/<name>
```

过程文档遵循 `docs/requirements|design|plan|dev|test/<feature>/` 目录规范。
