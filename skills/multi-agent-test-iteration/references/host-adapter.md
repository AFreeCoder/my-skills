# 宿主适配映射表(Host Adapter)

## 说明

本 skill `multi-agent-test-iteration` 设计为**宿主无关(host-agnostic)**:SKILL.md 与 orchestration.md 正文中使用的均是抽象能力词——"宿主子 agent""宿主提问工具""宿主浏览器能力""宿主命令执行"——不绑定到任何具体工具。执行时，请按本表将这些抽象能力一一映射到当前宿主的真实工具。

**全程不跨工具调外部 CLI。** 本 skill 不调用 `codex exec`，不调用 `claude -p`，不跨工具调任何外部 CLI。所有写测试、跑测试、审测试的操作，均通过当前宿主自身的原生子 agent 能力完成。这是稳定性的来源——测试需要大量真实运行，宿主原生工具最稳；也是通用性的来源——任何支持子 agent 的工具都能照本映射执行。

---

## 抽象能力 → 宿主工具映射表

| 抽象能力 | Claude Code | Codex 桌面端 / 其他 agent 工具 |
|---|---|---|
| 起独立子 agent | `Agent` 工具（`general-purpose`，全新上下文，无对话历史继承） | 该工具的子 agent / 子任务机制；要求全新上下文、可限只读权限 |
| 向用户提问 / 检查点 | `AskUserQuestion` | 该工具的提问 / 确认机制 |
| 跑命令 / 单元·集成测试 | `Bash` | 该工具的 shell 执行 |
| 跑 UI / E2E（起 server + 浏览器） | `preview_*`（`preview_start` / `preview_eval` / `preview_snapshot` / `preview_screenshot` / `preview_console_logs` 等） | 该工具的浏览器驱动；无则按降级处理（见下文） |
| 读写状态文件 | `Read` / `Write` / `Edit` | 该工具的文件读写 |

---

## "写⊥审"在同模型下的独立性约束

本 skill 的主笔 agent（Author）与评审 agent（Reviewer）**全部由宿主子 agent 承担，使用同一底层模型**。独立性不依赖模型差异，而靠以下机制保证：

1. **不同实例**：Author 与 Reviewer 必须是在**不同调用时间点**、通过**不同 `Agent` 工具调用**启动的子 agent 实例。严禁在同一个子 agent 会话中先写后审。

2. **不继承上下文**：Reviewer 启动时使用全新上下文，prompt 中**不传入** Author 的对话历史或中间思考过程——只传入工件文件路径与评审规则。Reviewer 只能看到工件本身，看不到 Author 是"怎么想到这样写的"。

3. **Reviewer 无写权限**：Reviewer 的子 agent 不获得工作区的写权限（在 Claude Code 中，其 prompt 中不传入 `Write`/`Edit` 授权，或使用只读沙箱），只能输出评审 JSON，不能直接修改工件。

这种机制之所以能提供对抗性：**主笔会爱上自己写的测试**——它知道自己的意图，容易对自我逻辑漏洞视而不见；而独立评审者以全新视角介入，没有"这段逻辑我是这么想的"的先入为主，更容易捅破主笔的盲区。纪律上的隔离，弥补了模型相同带来的同质风险。

---

## 降级与诚实

当某项抽象能力在当前宿主**缺失或失败**时（例如宿主无浏览器驱动、dev server 起不来、`preview_start` 返回非零退出码），处理原则如下：

- **如实降级标注，绝不伪造结果。** 不得编造命令输出，不得假设浏览器操作已成功执行。任何声称"已执行"的操作必须有真实的退出码和产物为证（见 `references/adversarial-core.md` 反作弊纪律第②③条）。

- **UI 无法真跑 → 标 `unexecuted`，移入 `open_questions`。** 若 E2E / UI 测试因无浏览器驱动或 server 启动失败而无法执行，相关测试用例在状态文件中标记为 `unexecuted`（而非 `passed` 或 `skipped`），并在当轮评审 JSON 的 `open_questions` 字段中记录：无法执行的原因、缺失的环境条件、需要人类介入验证的具体项目。

- **命令执行失败 → 至多重试一次，仍失败则停止并上报。** 失败后不得将失败结果当作通过继续走流程（见 `references/adversarial-core.md` 看门狗章节的重试策略）。

降级不是失败，它是诚实。诚实标注的 `unexecuted` 结果，比伪造的 `passed` 结果对人类评审者更有价值。
