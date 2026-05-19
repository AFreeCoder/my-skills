---
name: apipool-sync-upstream
description: 审慎同步当前 APIPool 仓库的 `upstream/main` 更新，先评估上游新增内容与本地长期定制之间的影响，再执行合入、冲突修复、回归测试与评审总结。用于用户要求“同步上游”“合并 upstream/main”“跟进上游更新”“评估上游变更是否影响 APIPool 业务逻辑”“输出本次上游合入总结/风险说明”等场景。
---

# APIPool Sync Upstream

## 概览

将 `upstream/main` 的同步拆成 6 个阶段：建立基线、审阅上游、评估本地定制影响、执行合入、回归测试、输出评审文档。

把业务兼容性放在第一位。即使 `git merge upstream/main` 没有产生 Git 冲突，也必须继续检查是否存在语义冲突或行为回退。

## 1. 建立基线

- 先执行 `git status -sb`、`git branch --show-current`、`git remote -v`。
- 若存在 merge/rebase/cherry-pick 进行中状态，先停止并报告。
- 若存在用户未明确授权处理的未提交修改，不要擅自 `reset`、`checkout`、`stash` 或覆盖；先说明风险并与用户确认处理方式。
- 建立基线时一并拉取 upstream tags，不要只看 `upstream/main`；上游 release tag 可能已经前进，但 `backend/cmd/server/VERSION` 仍停在旧值。
- 执行 `scripts/collect_upstream_sync_context.sh` 收集当前 `HEAD`、`upstream/main`、`merge-base`、commit 范围、文件重叠和高风险重叠。
- 基线里额外记录版本链路：当前 `backend/cmd/server/VERSION`、`upstream/main` 上的 `backend/cmd/server/VERSION`，以及 `git tag --merged upstream/main --sort=-version:refname | head -1` 的结果。
- 需要安全锚点时，可沿用仓库既有习惯创建分析标记（例如 `analysis/upstream-merge-YYYYMMDD`）；只有在不会干扰用户流程时才这样做。

## 2. 审阅上游更新

- 先看 `HEAD..upstream/main` 的提交列表和 diffstat，再看文件级变更。
- 对新增功能、配置默认值、接口行为、部署流程、文档入口、依赖或版本更新单独标记。
- 将上游改动与 `references/local-customizations.md` 对照，优先识别 APIPool 长期定制区域是否被覆盖。
- 命中版本链路时，不要只看 `backend/cmd/server/VERSION` 文件差异；必须同时对照最新 upstream release tag，判断是否存在“tag 已到新版本、VERSION 文件仍旧”的情况。
- 命中以下任一类时按高风险处理：品牌与文案、部署与回滚、OpenAI OAuth/Codex 兼容、帮助文档与首页入口、管理后台限制与默认配置。

## 3. 形成合入方案

- 在真正合并前，先写清楚需要保留的本地逻辑、准备接受的上游行为、预期冲突点和需要补跑的测试。
- 对“Git 无冲突但可能有业务冲突”的文件保持警惕，尤其是 `AppHeader`、`SettingsView`、`ratelimit_service`、OpenAI OAuth 相关服务、`deploy/` 与 `README.md`。
- 如果上游更新会影响 API contract、配置项、默认值、前端入口或发布流程，必须在方案里单列说明。
- 如果上游 release tag 已推进，而 APIPool 需要把左上角/运行时版本对齐到该发布号，先把它记录为“merge 后单独处理的版本对齐事项”，不要默认混入 upstream merge commit。

## 4. 合入 upstream/main

- 默认执行 `git fetch upstream main` 后再合入 `upstream/main`。
- 除非用户明确要求，不要改用 rebase，不要使用 `git reset --hard`、`git checkout --` 之类的破坏性命令。
- 解决冲突时优先保住 APIPool 的定制行为，再吸收上游修复；不要为了“尽快合并”而回退现有业务逻辑。
- 对高风险重叠文件，即使没有 Git 冲突，也要逐个复查最终代码是否仍满足本项目预期。
- 若本次合入涉及版本号、部署脚本、回滚脚本、文档入口或前端品牌资源，要在合入后再次核对它们是否仍与 APIPool 当前约定一致。
- 默认优先做“纯 upstream sync merge”。如果要把运行时版本号对齐到 upstream release tag，优先在 merge 完成后另起一个只改 `backend/cmd/server/VERSION` 的独立提交，例如 `chore(version): align runtime version to vX.Y.Z`。

## 5. 合入后回顾与测试

- 合入完成后，再次运行 `scripts/collect_upstream_sync_context.sh --no-fetch`，复看剩余分叉点与重叠文件。
- 审查本技能自带资产是否仍然准确：`references/local-customizations.md`、`references/testing-matrix.md`、`scripts/collect_upstream_sync_context.sh`、`scripts/scaffold_sync_review_doc.sh`。
- 当本次同步暴露出新的长期定制点、新测试基线、新高风险重叠模式或新的评审字段时，立即同步更新上述文件，不要把它们留到“以后再整理”。
- 参考 `references/testing-matrix.md` 执行测试。对于 upstream 同步，默认把完整回归作为基线，而不是只跑命中文件的单测。
- 至少覆盖后端测试、前端静态检查，以及前端逻辑测试或部署校验中的相关项。
- 若本轮涉及版本链路，还要核对 4 件事：最新 upstream release tag、当前仓库 `backend/cmd/server/VERSION`、部署时解析出的版本、部署后实际运行的二进制版本/页面展示版本。
- 测试失败时，先判断是上游行为变化、本地定制冲突，还是测试基线本身需要同步更新；修复后重新运行受影响测试。
- 若有无法在本轮完全验证的风险，明确记录，不要模糊表述为“理论上没问题”。

## 6. 输出评审文档

- 执行 `scripts/scaffold_sync_review_doc.sh` 生成 `docs/plans/YYYY-MM-DD-upstream-sync-review.md` 初稿。
- 文档至少覆盖：基线 refs、上游更新摘要、重叠/冲突处理、测试记录、剩余风险、回滚或观察点。
- 只要版本链路被触发，文档里要明确写清：upstream 最新 release tag、upstream/main 上的 `VERSION` 值、本地最终 `VERSION` 值，以及版本对齐是否被拆成独立提交。
- 最终对用户的输出也要包含这四类信息：本次合入了什么、保住了哪些 APIPool 逻辑、跑了哪些测试、还有哪些风险点需要评审关注。

## 7. 维护技能资产

- 将本技能的参考资料和脚本视为可演进资产，而不是一次性模板。
- 每次真实执行 upstream 同步后，都检查下面 4 类资产是否需要随仓库演化而更新：
  - `references/local-customizations.md`
  - `references/testing-matrix.md`
  - `scripts/collect_upstream_sync_context.sh`
  - `scripts/scaffold_sync_review_doc.sh`
- 出现以下任一情况时，直接更新相应文件：
  - APIPool 新增了长期保留的本地定制，或旧定制已失效
  - 默认测试基线、CI、构建方式、部署方式或版本链路发生变化
  - 当前高风险重叠模式新增了新的热点文件或目录
  - 评审文档在本轮同步中暴露出字段缺失、检查项缺失或记录粒度不足
- 更新完技能资产后，重新运行结构校验；若脚本有改动，至少实跑一次。

## 参考资料

- `references/local-customizations.md`：APIPool 长期定制点与高风险区域。
- `references/testing-matrix.md`：回归测试与专项验证矩阵。
