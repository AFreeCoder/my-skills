---
name: webpage-clipper
description: 将网页 URL 剪裁/保存为本地 Markdown 并下载图片。用于用户请求网页剪裁、网页转 Markdown、保存网页为本地笔记/归档（含图片）或类似需求。
---

# Webpage Clipper

使用该技能把网页内容剪裁为本地 Markdown，并把图片下载到本地资产目录后重写图片链接。剪裁流程参考 SiYuan Chrome 扩展：先做 DOM 预处理，再用 Readability 提取正文，必要时回退到更完整内容以避免列表/图片丢失。

## 快速开始

1. 默认输出到 Obsidian 根目录 `00_Inbox`，图片输出到根目录 `assets`。
2. 运行脚本 `scripts/clip_webpage.py`。
3. 遇到动态页面优先使用 `--engine browser`。

## 依赖安装

优先安装完整依赖：

```bash
python -m pip install requests beautifulsoup4 readability-lxml markdownify
```

可选（动态页面）：

```bash
python -m pip install playwright
playwright install
```

如未安装 `readability-lxml`，脚本会退回到 `article/main/body` 提取。

## 典型用法

```bash
python /Users/afreecoder/.codex/skills/webpage-clipper/scripts/clip_webpage.py \
  --url "https://example.com" \
  --out-dir "/path/to/notes"
```

指定图片目录（适合 Obsidian 统一 assets 目录）：

```bash
python /Users/afreecoder/.codex/skills/webpage-clipper/scripts/clip_webpage.py \
  --url "https://example.com" \
  --out-dir "/path/to/notes/20_Area" \
  --assets-dir "/path/to/notes/assets"
```

动态页面：

```bash
python /Users/afreecoder/.codex/skills/webpage-clipper/scripts/clip_webpage.py \
  --url "https://example.com" \
  --out-dir "/path/to/notes" \
  --engine browser
```

## 输出约定

- Markdown 文件名来自网页标题（去除非法字符）。
- 默认图片目录为 Obsidian 根目录 `assets`（如需其他路径用 `--assets-dir`）。
- 默认写入 YAML frontmatter（`title`/`source`/`clipped_at`）与一级标题。
- 若 Readability 结果缺失列表或图片，会自动回退到 `article/main/body` 以提高内容完整性。
- 对于 `mp.weixin.qq.com` 这类有环境校验的页面，若 requests 返回验证页，将自动切到浏览器引擎再抓取。

## 参数说明

- `--url`：网页地址（必填）。
- `--out-dir`：Markdown 输出目录（默认 `OBSIDIAN_VAULT/00_Inbox`）。
- `--assets-dir`：图片输出目录（默认 `OBSIDIAN_VAULT/assets`）。
- `--title`：标题覆盖。
- `--engine`：`requests` 或 `browser`。
- `--timeout`：请求超时（秒）。
- `--user-agent`：自定义 UA。
- `--no-frontmatter`：不写 frontmatter。
- `--no-heading`：不写一级标题。

## 操作要点

- 动态页面或需要登录时，用 `--engine browser`。
- 图片命名格式为 `YYYY-MM-DD-HHmmss-<md5>`，避免重复与重名冲突。
- `data:` 内联图片、内嵌 SVG 会解码到本地并替换链接。
- 支持常见懒加载属性（`data-src`/`data-original`/`data-srcset` 等）与 `picture/source`。
- 如需统一管理图片，优先使用 `--assets-dir` 指向固定资产目录。
- 可通过环境变量 `OBSIDIAN_VAULT` 覆盖默认根目录。
