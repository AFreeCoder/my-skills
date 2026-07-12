# Skill Source Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除用户确认的 7 个自建 Skill 及失去消费者的共享内核，纳入遗漏的自建 `push-deploy`，并保持仓库清单一致。

**Architecture:** Skill 实体由 `skills/<name>/` 承载，`.claude-plugin/marketplace.json` 是插件注册表，`README.md` 是人工可读目录。删除必须同时更新这三层，并用集合相等校验防止遗漏。

**Tech Stack:** Git、Shell、JSON、Markdown、AgentSkills `SKILL.md`

---

### Task 1: 建立删除前基线

**Files:**
- Read: `skills/_adversarial-core/tests/*`
- Read: `.claude-plugin/marketplace.json`

- [x] **Step 1: 运行现有共享内核测试**

Run:

```bash
bash skills/_adversarial-core/tests/test_check_skill.sh
python3 skills/_adversarial-core/tests/test_schema.py
bash skills/_adversarial-core/tests/test_filter_findings.sh
bash skills/_adversarial-core/tests/test_sync_core.sh
bash skills/_adversarial-core/tests/test_progress_check.sh
```

Expected: 所有测试输出 `ok`，退出码为 0。

- [x] **Step 2: 运行预期失败的目标库存断言**

Run: 用 `jq` 和目录检查断言 7 个删除目标已经不存在，同时 `push-deploy` 已存在并注册。

Expected: 断言失败，因为删除尚未发生且 `push-deploy` 尚未纳入。

### Task 2: 删除已确认的 Skill

**Files:**
- Delete: `skills/content-writing/`
- Delete: `skills/daily/`
- Delete: `skills/git-auto-commit/`
- Delete: `skills/gpt101-dashboard-renew/`
- Delete: `skills/multi-agent-design-review/`
- Delete: `skills/multi-agent-dev-iteration/`
- Delete: `skills/multi-agent-test-iteration/`
- Delete: `skills/_adversarial-core/`

- [x] **Step 1: 确认共享内核没有剩余运行时消费者**

Run:

```bash
rg '_adversarial-core' skills --glob '!_adversarial-core/**' --glob '!multi-agent-*/**'
```

Expected: 无输出。

- [x] **Step 2: 删除目标目录**

Expected: 7 个 Skill 目录和共享内核目录均不存在。

### Task 3: 同步注册表和目录文档

**Files:**
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`

- [x] **Step 1: 从 marketplace 删除 7 个注册项并加入 `push-deploy`**

Expected: JSON 可解析，`plugins[0].skills` 共 35 项。

- [x] **Step 2: 从 README 删除对应目录行、加入 `push-deploy` 并更新总数**

Expected: README 显示 35 个 Skill，不再出现 7 个删除名称，并列出 `push-deploy`。

### Task 4: 纳入自建 `push-deploy`

**Files:**
- Create: `skills/push-deploy/SKILL.md`
- Create: `skills/push-deploy/agents/openai.yaml`
- Create: `skills/push-deploy/references/deployment-doc-template.md`
- Create: `skills/push-deploy/references/report-template.md`

- [x] **Step 1: 复制经过验证的 Codex 全局原件**

Source: `~/.codex/skills/push-deploy/`

Expected: 仓库目录包含上述 4 个文件，不引入 CC Switch 旧副本。

- [x] **Step 2: 验证复制后内容一致**

Run:

```bash
diff -qr ~/.codex/skills/push-deploy skills/push-deploy
```

Expected: 无输出，退出码为 0。

### Task 5: 验证最终状态

**Files:**
- Verify: `.claude-plugin/marketplace.json`
- Verify: `README.md`
- Verify: `skills/*/SKILL.md`

- [x] **Step 1: 重跑删除库存断言**

Expected: PASS。

- [x] **Step 2: 比较 marketplace 与文件系统集合**

Expected: 两个集合完全一致，无缺失或多余项。

- [x] **Step 3: 校验 JSON、frontmatter 和 diff**

Run:

```bash
jq empty .claude-plugin/marketplace.json
git diff --check
git status --short
```

Expected: JSON 合法，`git diff --check` 无输出，状态仅包含本计划批准的文件。
