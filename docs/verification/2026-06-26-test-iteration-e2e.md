# multi-agent-test-iteration 端到端验证(Task 11)

> 日期:2026-06-26 · 分支:`feat/multi-agent-test-iteration`

## 标的与方式

- **标的**:throwaway 仓库 `/tmp/test-iter-e2e` —— `discount` 模块的 `final_price(price, rate)`,**植入已知 bug**(DESIGN 要求 rate∈[0,1] 越界 raise ValueError,实现仅校验 `rate<0`、缺 `rate>1` 上界 → `final_price(100,2)` 返回 -100,违反"越界报错"与"结果非负"两约束)。冻结 DESIGN 含功能×验证矩阵。
- **方式**:Orchestrator(Claude 主)照 `references/orchestration.md` 真实跑阶段 0→1d,派**真实**主笔 / 评审子 agent;收敛用真实 `_adversarial-core/filter-findings.py` + `progress-check.py`。

## 验证结论

| 验证点 | 结果 | 证据 |
|---|---|---|
| 端到端流程跑通 | ✅ | 阶段0 产矩阵 → 主笔写 12 测试 → Orchestrator 复跑(10 过 2 失败)→ 评审产 schema JSON → 分流 → 收敛,全程照 orchestration 可执行 |
| 主笔只写测试不改实现 | ✅ | 主笔发现 rate>1 失败,如实写"疑似实现 bug",未碰 `discount.py` |
| 评审复核 real-bug(非测试错) | ✅ | 评审A 把 rate>1 两失败判 `real-bug`/blocker(实现违反 DESIGN);测试质量 `approve` |
| **real-bug 分流不死锁** | ✅ | `--only-category real-bug` 抽 1 条 → bug 清单;`--exclude-category real-bug` 后 quality 版 blocker/major=**0**;`progress-check` → **`complete`**。若不分流,blocker real-bug 会让 progress-check 永不 complete + 主笔不修实现 → 死锁 |
| **complete ≠ 全绿** | ✅ | 测试 2 红(rate>1),目标仍 `complete`(测试质量达标即收敛) |
| **假绿挡下** | ✅ | 评审B 对 mock 掉 `final_price` 的"全绿"测试标 `fake-green`(2 条),`needs-revision`;并识破 `test_rate_over_one` 的 mock 恰好掩盖了 rate>1 的 real-bug |

## 未端到端覆盖(诚实标注)

- **UI 降级**:本标的无 UI 层级,未真实触发 `unexecuted` 降级路径;逻辑由 `host-adapter.md` / `orchestration.md` 阶段1b / 反作弊纪律规定,留真实 dogfood 验证。
- **无进展 / 分歧上交**:`progress-check.py` 的 `escalate:no-progress` / `escalate:disagreement` 已由 `_adversarial-core/tests/test_progress_check.sh` 单测覆盖,未在本 e2e 重复造多轮。

## 附带发现 + 加固

评审子 agent 输出**偶尔偏离 review-schema**:评审B 输出 `verdict:"REJECT"`(应 `needs-revision`)、`severity:"critical/high/medium"`(应 `blocker/major/minor`)、`open_questions` 为对象数组(应字符串数组)。**语义正确、格式偏离**。

- 与 `multi-agent-dev-iteration-realworld` 第④条一致(评审 JSON 偶不合 schema,Orchestrator「输出校验」环节规整:critical/high/medium→blocker/major/minor、REJECT→needs-revision)。母本「输出校验」本就设计了规整 + 校验,不算"把失败当通过"。
- **加固已落地**:`test-reviewer-prompt.md` 输出要求处新增「字面值硬约束」块——verdict 仅 `approve`/`needs-revision`、severity 仅 `blocker`/`major`/`minor`(禁同义词)、open_questions 为字符串数组。

## 结论

核心机制(对抗式主笔↔评审、real-bug 分流防死锁、complete≠全绿、假绿挡下)**端到端真实成立**,skill 可用。UI 降级路径留真实 dogfood 补验。
