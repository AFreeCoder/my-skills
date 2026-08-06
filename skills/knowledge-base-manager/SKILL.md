---
name: knowledge-base-manager
description: 管理本地 Markdown 知识库与飞书知识库的项目空间，并在用户要求沉淀、同步、校验或初始化项目知识时保持两端项目名称、目录层级、标题和 Markdown 正文一致。
---

# Knowledge Base Manager

用此 Skill 管理一份本地 Markdown 知识库与对应的飞书知识库。适用于：

- 将项目规划、建设记录、项目管理、运营管理和经验沉淀归档；
- 初始化或接入一个项目知识空间；
- 把新增或更新的材料同步到本地与飞书；
- 比对、修复两端内容不一致。

## 核心约定

本地 Markdown 是唯一内容真源；飞书保存同一份原生 Markdown 文件。不要把飞书在线文档的富文本导出再当作真源，因为格式转换会破坏“内容完全一致”的承诺。

“一致”指以下四项：

| 项目 | 本地 | 飞书 |
| --- | --- | --- |
| 项目名称 | 项目根目录名 | 知识空间名 |
| 目录层级 | 子目录 | 同名 Wiki 目录节点 |
| 文档标题 | 文件名去除 `.md` | Wiki 内 Markdown 文件名去除 `.md` |
| 文档正文 | UTF-8 Markdown 正文 | 同字节 UTF-8 Markdown 正文 |

本地的 YAML frontmatter 是 Markdown 正文的一部分，必须原样同步。映射信息、同步日志和远端 token 是运行状态，不属于项目内容；只能放在本地知识库的 `.kb-sync/` 中，并且不得写入公开的 Skill 仓库。

## 先决条件

1. 先读取 `~/.claude/KNOWLEDGE.md`，获取本地知识库位置和其 Git 工作流；不要硬编码路径。
2. 检查 `lark-cli --version`、`lark-cli auth status`。飞书操作始终显式使用 `--as user`。
3. 未授权或用户 token 过期时，执行 `lark-cli auth login --domain wiki,markdown`；生成并展示 CLI 要求的二维码，等待用户完成授权后再继续。
4. 读取 `lark-cli wiki --help`、`lark-cli markdown --help`。在使用不熟悉的参数前先查看对应 `--help` 或 `lark-cli schema`，不要猜 token 或 API 字段。

## 项目模型

每个项目在两端都使用完全相同的项目名，例如本地 `ShipArt/` 对应飞书空间 `ShipArt`。项目内建议但不强制采用下面的目录：

```text
ShipArt/
├── 产品规划/
├── 项目管理/
├── 运营管理/
└── 经验沉淀/
```

不要为“看起来整齐”擅自改名、移动或重组已有材料。目录规划、批量移动、删除和覆盖旧内容均须先给出计划并取得用户明确确认。

## 初始化或接入项目

1. 从本地项目根目录名得到项目名称，先检查飞书是否有同名空间：`lark-cli wiki +space-list --as user --format json`。
2. 只有不存在精确同名空间时，才创建：`lark-cli wiki +space-create --as user --name '<项目名>'`。这是写操作；先向用户说明创建结果是私有团队知识空间。
3. 同名空间多于一个时停止，让用户选择 `space_id`；不得根据描述、可见性或创建时间猜测。
4. 在本地创建 `.kb-sync/<项目名>.json` 映射文件。它至少记录 `project_name`、`local_root`、`space_id`、目录对应的 `wiki_node_token`、文档对应的 `file_token`、`content_sha256` 和 `synced_at`。token 只保存在本地私有知识库，禁止提交到公开仓库或贴入回复。
5. 对每个本地目录，创建一个同名 Wiki `docx` 目录节点：`lark-cli wiki +node-create --as user --space-id '<space_id>' --parent-node-token '<父节点>' --title '<目录名>'`。根目录不另建同名节点，直接使用知识空间。
6. 对每个 Markdown 文件，用 `lark-cli markdown +create --as user --wiki-token '<目录节点>' --file '<本地文件>'` 上传。若 CLI 不能从 `--file` 推导目标名，显式传 `--name '<文件名>.md'`。
7. 上传后使用 `lark-cli markdown +fetch --as user --file-token '<file_token>'` 读取远端正文，计算两端 SHA-256。仅在哈希一致后写入或更新映射。

## 新增或更新材料：双端提交协议

用户说“沉淀”“归档”“记录到知识库”且已指定项目时，按以下顺序处理：

1. 明确项目、目标相对路径、标题、正文和归类；缺少任一项时先提问。除非用户明确要求，不从对话中的零散信息自行扩写成正式记录。
2. 先展示简短摘要、目标位置和拟写 Markdown；新增材料在用户给出内容时可直接执行，覆盖已有材料必须再次确认。
3. 在本地项目根目录写入或更新 Markdown，文件名与飞书文件名保持一致。
4. 新文件调用 `markdown +create`；已有映射文件调用 `markdown +overwrite --file-token '<file_token>' --file '<本地文件>'`。
5. 拉取远端文件并做字节哈希比对；一致后更新映射，并遵循 `KNOWLEDGE.md` 的 Git 流程提交和推送本地知识库。
6. 任何一步失败时停止。不要把“仅本地已写入”或“仅飞书已更新”说成同步完成；报告实际成功的一侧、失败原因和安全恢复方式。

## 冲突与修复

同步前必须比较本地文件哈希、映射中的上次哈希与远端文件哈希：

- 只有本地变更：本地覆盖飞书。
- 只有飞书变更：先下载成候选文件并展示 diff；由用户决定接受飞书版本还是保留本地版本。
- 两端都变更：绝不自动合并或覆盖。生成三方 diff，等待用户选择或提供合并结果。
- 映射缺失：先盘点本地文件和飞书节点/文件，输出候选匹配表。只有文件名、相对路径与正文哈希都能证明对应关系时才补建映射；其余由用户确认。

不要删除任一端的材料来“恢复一致”。删除项目、空间、节点、文件或整个目录属于高风险写操作，必须单独获得明确授权。

## ShipArt 基线

`ShipArt` 是 ShipArt 项目的知识库，主要记录：产品规划与建设、项目管理、运营管理和经验沉淀。它应映射到本地知识库中同名的 `ShipArt` 项目根目录，并使用同名的飞书知识空间。

首次同步前，先盘点两端现状并向用户确认：本地项目根路径、飞书 `space_id`、现有目录树、候选文档映射和是否允许创建缺失的目录/文件。没有这次确认，不执行批量导入。

## 验收与汇报

完成一次同步后，报告：项目名、已同步的相对路径、两端哈希校验结果、本地 Git 提交（如有）、以及未同步或冲突项。不得在报告中披露 access token、refresh token、open_id、file token、node token、space_id、用户邮箱、订单或客户信息。
