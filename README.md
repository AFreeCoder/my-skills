# My Skills

AFreeCoder 的 Skill 唯一事实源：自建 Skill 源码 + 常用第三方 Skill 收藏。

安装、更新、卸载、收藏统一由仓库内的 [`skill-manage`](skills/skill-manage/SKILL.md) Skill 编排，底层调用 [skills CLI](https://github.com/vercel-labs/skills)（`npx -y skills@latest`）。命令用法、安装范围约定与"修改自建 Skill → 推送 → 刷新安装"闭环均以该 SKILL.md 为准，本文件只做事实源索引，不复述操作步骤。

安装实体落在 `.agents/skills/`（项目级在 `<project>/` 下，用户级在 `~/` 下）：Codex 直接读取，Claude Code 经 `.claude/skills` 软链读取。本仓库只存源码，不含管理脚本、准入清单或 lock/state 文件。

## 自建 Skill

当前共收录 `6` 个自建 Skill，安装来源均为 `AFreeCoder/my-skills`：

| Skill | 说明 |
| --- | --- |
| `ai-news-collect` | 本地采集 30 组 AI 官网、更新日志与 X 动态，保留原文并合并分类为中文简报。 |
| `dev-flow` | Issue 驱动的开发流程：小任务全自动直通（创建 issue → 分析 → 实施 → 评审 → 发布），问题排查留档结论、修复与否由用户分流，大需求按阶段独立 issue 留档。 |
| `knowledge-base-manager` | 管理本地 Markdown 知识库与飞书知识库的项目映射和内容双端一致性。 |
| `push-deploy` | 通用发布门禁：审计发布历史、监控 CI/CD、核查备份与回滚准备并验证线上服务。 |
| `skill-manage` | Skill 全流程管理：安装、更新、卸载、收藏第三方，以及自建 Skill"修改 → 推送 → 刷新安装"闭环。 |
| `webpage-clipper` | 将网页剪裁为本地 Markdown 并下载图片，用于笔记与资料归档。 |

仓库公开，自建 Skill 内容不放内网地址、密钥等敏感信息。

## 第三方 Skill 收藏

只做记录，不复制上游源码。标注「私有」的来源仓库仅作者可访问，他人无法安装。

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
| `shipany-page-builder` | `AFreeCoder/shipany-template`（私有） | 按简述为 ShipAny 项目创建动态页面。 |
| `shipany-quick-start` | `AFreeCoder/shipany-template`（私有） | 新 ShipAny 项目的首轮自动定制。 |
| `supabase-to-d1` | `AFreeCoder/shipany-template`（私有） | Supabase PostgreSQL 迁移到 Cloudflare D1。 |
| `ui-ux-pro-max` | `nextlevelbuilder/ui-ux-pro-max-skill` | UI/UX 设计知识库（风格、配色、字体、组件）。 |
| `shadcn` | `shadcn-ui/ui` | shadcn/ui 组件与项目管理。 |

## 仓库约定

过程文档遵循 `docs/requirements|design|plan|dev|test/<feature>/` 目录规范。开发期临时软链调试的做法见 [`skill-manage`](skills/skill-manage/SKILL.md)。
