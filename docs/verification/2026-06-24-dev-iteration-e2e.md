# multi-agent-dev-iteration 端到端验证记录(Task 13 · happy-path)

日期:2026-06-24 · 环境:codex-cli 0.142.0(已登录) · throwaway 仓库实跑

## 验证目标
拿 `multi-agent-dev-iteration` skill 真跑一遍完整 happy-path:从冻结 DESIGN + 计划,经 Codex 主笔 TDD 实现、独立 Claude 评审、收敛判定,到合并检查点。

## 场景
throwaway 仓库,DESIGN 冻结一个小功能 `to_snake_case(s)`(camel/Pascal/kebab/空格 → snake;折叠分隔;首尾不留 `_`;仅标准库),功能×验证矩阵 6 行;计划单 step(TDD 实现)。

## 各阶段结果
- **阶段 0**:`codex login status` 预检、`DESIGN 已冻结` 校验、`git worktree add -b dev/snake-case`、建 `.author/`/`.review/` 状态目录、记录 `STEP_BASE` —— 全部按 orchestration.md 执行成功。
- **阶段 1(Codex 主笔,看门狗子 agent 包裹)**:
  - **首次尝试诚实失败**:环境缺 `pytest`,Codex 停在 TDD 红灯、**拒绝写实现/拒绝伪造绿**;看门狗如实报 FAILURE(CODEX_EXIT=0 但无产物),未当成通过。→ 反作弊纪律 + 看门狗存活监控的真实正例。
  - **修环境后重试一次**(改用标准库 `unittest`):Codex 写测试→红→写实现→`Ran 6 tests OK`→提交 `ceeec78`,自证未改 DESIGN。SUCCESS。
- **阶段 2(独立 Claude 评审)**:读 `git diff STEP_BASE..HEAD` + DESIGN + 测试结果,产出结构化 JSON 写入 `.review/step-1-round-1.json`;经母本 `review-schema.json` 校验**合法**;verdict=`approve`(0 blocker / 0 major / 2 minor),并提出一条有价值 open_question(连续大写缩写 `HTMLParser`→`htmlparser` vs `parseHTML`→`parse_html` 的不对称)。
- **阶段 4(收敛判定)**:`progress-check.py --rounds … --k 2 --m 5` → `complete`。
- **阶段 5(合并检查点)**:合回 main、合并后 `unittest` 仍 6 绿、`git worktree remove` 清理。

## 结论
happy-path 全链路打通,真实 Codex 主笔 + 真实独立 Claude 评审 + schema 校验 + 收敛判定 + 合并均按设计工作;并顺带实证了"缺依赖时不伪造通过、看门狗如实失败、重试一次"的失败兜底。

## 尚未覆盖(后续如需)
主动注入 Codex 被信号杀死(137/143)、主笔↔评审 blocker 分歧上交人类、连续 N 轮无净进展触发 K=2/硬上限 M=5 这三条异常路径的真实回路(其判定逻辑已由 `progress-check.py` 单元测试覆盖;此处未做真实端到端注入)。
