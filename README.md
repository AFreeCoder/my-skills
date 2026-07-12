# My Skills

集中管理的 AI Agent Skills 仓库，供 Claude Code、Codex、OpenClaw、Hermes 等多端共享使用。

## 目录结构

```
my-skills/
├── .claude-plugin/
│   └── marketplace.json   # CC Switch / 插件发现清单
├── skills/                # 所有 skills 存放于此
│   ├── <skill-name>/
│   │   └── SKILL.md
│   └── ...
└── README.md
```

## 当前收录

当前共收录 `35` 个 skill。

| Skill | 说明 |
| --- | --- |
| `apipool-push-deploy` | Review APIPool production risk before pushing code to `origin/main`, verify that the GitHub Actions auto-deploy flow... |
| `apipool-sync-upstream` | 审慎同步当前 APIPool 仓库的 `upstream/main` 更新，先评估上游新增内容与本地长期定制之间的影响，再执行合入、冲突修复、回归测试与评审总结。用于用户要求“同步上游”“合并 upstream/main”“跟进上游更... |
| `baoyu-article-illustrator` | Analyzes article structure, identifies positions requiring visual aids, generates illustrations with Type × Style two... |
| `chronicle` | Allows you to view the user's screen as well as several hours of history. Use when the user makes a reference to thei... |
| `claude-to-im` | Bridge THIS Claude Code or Codex session to Telegram, Discord, Feishu/Lark, QQ, or WeChat so the user can chat with C... |
| `frontend-design` | Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks... |
| `json-canvas` | Create and edit JSON Canvas files (.canvas) with nodes, edges, groups, and connections. Use when working with .canvas... |
| `lark-approval` | 飞书审批 API：审批实例、审批任务管理。 |
| `lark-attendance` | 飞书考勤打卡：查询自己的考勤打卡记录 |
| `lark-base` | 当需要用 lark-cli 操作飞书多维表格（Base）时调用：搜索 Base、建表、字段管理、记录读写、记录分享链接、视图配置、历史查询，以及角色/表单/仪表盘管理/工作流；也适用于把旧的 +table / +field / +re... |
| `lark-calendar` | 飞书日历（calendar）：提供日历与日程（会议）的全面管理能力。核心场景包括：查看/搜索日程、创建/更新日程、管理参会人、查询忙闲状态及推荐空闲时段、查询/搜索与预定会议室。注意：涉及【预约日程/会议】或【查询/预定会议室】时，必... |
| `lark-contact` | 飞书 / Lark 通讯录,用于按姓名 / 邮箱把员工解析成 open_id,以及按 open_id 反查员工的姓名 / 部门 / 邮箱 / 联系方式。当用户说出某人姓名而下一步需要发消息 / 加群 / 排日程时,先用本 skill... |
| `lark-doc` | 飞书云文档（v2）：创建和编辑飞书文档。使用本 skill 时，docs +create、docs +fetch、docs +update 必须携带 --api-version v2；默认使用 DocxXML 格式（也支持 Markd... |
| `lark-drive` | 飞书云空间：管理云空间中的文件和文件夹。上传和下载文件、创建文件夹、复制/移动/删除文件、查看文件元数据、管理文档评论、管理文档权限、订阅用户评论变更事件、修改文件标题（docx、sheet、bitable、file、folder、w... |
| `lark-event` | Lark/Feishu real-time event listening / subscribing / consuming: stream events as NDJSON via `lark-cli event consume... |
| `lark-im` | 飞书即时通讯：收发消息和管理群聊。发送和回复消息、搜索聊天记录、管理群聊成员、上传下载图片和文件（支持大文件分片下载）、管理表情回复。当用户需要发消息、查看或搜索聊天记录、下载聊天中的文件、查看群成员时使用。 |
| `lark-mail` | 飞书邮箱 — draft, compose, send, reply, forward, read, and search emails; manage drafts, folders, labels, contacts, attac... |
| `lark-markdown` | 飞书 Markdown：查看、创建、上传和编辑 Markdown 文件。当用户需要创建或编辑 Markdown 文件、读取或修改时使用。 |
| `lark-minutes` | 飞书妙记：妙记相关基本功能。1.查询妙记列表（按关键词/所有者/参与者/时间范围）；2.获取妙记基础信息（标题、封面、时长 等）；3.下载妙记音视频文件；4.获取妙记相关 AI 产物（总结、待办、章节）；5.上传音视频生成妙记，也支持... |
| `lark-okr` | 飞书 OKR：管理目标与关键结果。查看和编辑 OKR 周期、目标（Objective）、关键结果（Key Result）、对齐关系、量化指标和进展记录。当用户需要查看或创建 OKR、管理目标和关键结果、查看对齐关系时使用。 |
| `lark-openapi-explorer` | 飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。当用户的需求无法被现有 lark-* skill 或 lark-cli 已注册命令满足，需要查找并调用原生飞书 OpenAP... |
| `lark-shared` | 飞书/Lark CLI 共享基础：应用配置初始化、认证登录（auth login）、身份切换（--as user/bot）、权限与 scope 管理、Permission denied 错误处理、安全规则。当用户需要第一次配置(`la... |
| `lark-sheets` | 飞书电子表格：创建和操作电子表格。创建表格并写入表头和数据、读取和写入单元格、追加行数据、在已知电子表格中查找单元格内容、导出表格文件。当用户需要创建电子表格、批量读写数据、在已知表格中查找内容、导出或下载表格时使用。若用户是想按名称... |
| `lark-skill-maker` | 创建 lark-cli 的自定义 Skill。当用户需要把飞书 API 操作封装成可复用的 Skill（包装原子 API 或编排多步流程）时使用。 |
| `lark-slides` | 飞书幻灯片：创建和编辑幻灯片，接口通过 XML 协议通信。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。 |
| `lark-task` | 飞书任务：管理任务、清单和任务智能体。创建待办任务、查看和更新任务状态、拆分子任务、组织任务清单、分配协作成员、上传任务附件、注册或注销任务智能体、更新任务智能体的主页数据、写入智能体任务记录。当用户需要创建待办事项、查看任务列表、跟... |
| `lark-vc` | 飞书视频会议：查询会议记录、获取会议纪要产物（总结、待办、章节、逐字稿）。1. 查询已经结束的会议数量或详情时使用本技能(如历史日期｜ 昨天 \| 上周 \| 今天已经开过的会议等场景)，查询未开始的会议日程使用 lark-calen... |
| `lark-whiteboard` | 飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用 DSL（转成 OpenAPI 格式）、PlantUML/Mermaid 格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板，或是需... |
| `lark-wiki` | 飞书知识库：管理知识空间、空间成员和文档节点。创建和查询知识空间、查看和管理空间成员、管理节点层级结构、在知识库中组织文档和快捷方式。当用户需要在知识库中查找或创建文档、浏览知识空间结构、查看或管理空间成员、移动或复制节点时使用。 |
| `lark-workflow-meeting-summary` | 会议纪要整理工作流：汇总指定时间范围内的会议纪要并生成结构化报告。当用户需要整理会议纪要、生成会议周报、回顾一段时间内的会议内容时使用。 |
| `lark-workflow-standup-report` | 日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成指定日期的日程与未完成任务摘要。适用于了解今天/明天/本周的安排。 |
| `obsidian-bases` | Create and edit Obsidian Bases (.base files) with views, filters, formulas, and summaries. Use when working with .bas... |
| `obsidian-markdown` | Create and edit Obsidian Flavored Markdown with wikilinks, embeds, callouts, properties, and other Obsidian-specific... |
| `push-deploy` | Use when releasing code to production or staging, auditing release history, monitoring CI/CD, verifying backups and rollback readiness, or restoring live service during a release. |
| `webpage-clipper` | 将网页 URL 剪裁/保存为本地 Markdown 并下载图片。用于用户请求网页剪裁、网页转 Markdown、保存网页为本地笔记/归档（含图片）或类似需求。 |

## 接入方式

### Claude Code / Codex（Mac 本地）

通过 CC Switch 添加本仓库，自动发现并同步所有 Skills。

### OpenClaw / Hermes（VPS）

1. `git clone` 本仓库到服务器
2. 将对应运行时的 extra skill 目录指向 `skills/`
3. 定期 `git pull` 更新

## Skill 规范

遵循 [AgentSkills](https://agentskills.io) 规范：

```
skill-name/
├── SKILL.md          # 必需：frontmatter + 指令
├── references/       # 可选：参考文档
├── scripts/          # 可选：可执行脚本
├── prompts/          # 可选：提示词模板
└── assets/           # 可选：模板、图片等资源
```

## 编辑工作流

1. 在本地工作副本中编辑 Skill 文件
2. 检查 `SKILL.md` frontmatter 至少包含 `name` 和 `description`
3. 同步更新 `.claude-plugin/marketplace.json`
4. `git commit && git push`
5. 各端通过 CC Switch、OpenClaw 或 Hermes 的同步机制拉取更新
