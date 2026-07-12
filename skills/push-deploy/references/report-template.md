# Release Report Template

Use this template after deployment monitoring completes. Replace every placeholder with concrete facts from the current release.

## Short Report

```md
本次发布基于 `<remote-release-branch>@<baseline-sha>`，发布范围是 `<baseline-sha>..<candidate-sha>`，包含 `<approved-scope>`。发布标识是 `<commit-or-version>`。

本地工作区 `<clean-or-dirty-summary>`；分支和 worktree 收口结果为 `<git-reconciliation-summary>`。

部署流程 `<deploy-run-or-session>` 的结果是 `<result>`；目标环境当前运行版本是 `<live-version>`。

健康检查：`<health-result>`。
备份确认：`<backup-result>`。
回滚准备：`<rollback-result>`。

线上业务判断：`<business-impact>`。
剩余风险或观察项：`<watchpoints-or-none>`。
```

## Full Report

```md
发布结果：`<success-failed-rolled-back-or-blocked>`

发布信息：
- 目标分支或环境：`<target>`
- 远程发布基线：`<remote-release-branch>@<baseline-sha>`
- 候选提交：`<candidate-sha>`
- 发布提交范围：`<baseline-sha>..<candidate-sha>`
- 批准发布范围：`<approved-scope>`
- 前置依赖或同批发布关系：`<dependency-or-release-batch-or-none>`
- 发布标识：`<commit-or-version>`
- 部署流程：`<deploy-run-or-session>`
- 部署结果：`<deploy-result>`
- 本地工作区：`<clean-or-dirty-summary>`
- 本地分支和 worktree 收口：`<git-reconciliation-summary>`

运行态证据：
- 线上实际版本：`<live-version>`
- 运行单元状态：`<runtime-health>`
- 健康检查：`<health-result>`
- 关键日志：`<log-summary>`
- 资源状态：`<resource-summary>`

备份和回滚：
- 备份结果：`<backup-result>`
- 备份校验：`<backup-validation>`
- 回滚准备：`<rollback-readiness>`
- 最快恢复路径：`<fast-recovery-path>`
- 数据恢复说明：`<data-restore-note>`

业务影响：
- `<business-impact-1>`
- `<business-impact-2>`
- `<remaining-risk-or-watchpoint>`

文档复盘：
- 部署文档是否需要更新：`<yes-or-no>`
- 需要更新的点：`<doc-update-summary>`
```

## Minimum Facts

- fetched remote release baseline and candidate SHA
- exact released commit range and approved scope
- prerequisite or release-batch relationship, if any
- pushed or deployed commit, version, or artifact
- CI/CD run, platform deploy, or custom session result
- live runtime version
- runtime health result
- backup artifact or metadata verification
- rollback readiness or recovery result
- local release branch and worktree reconciliation result
- user-visible business impact
- residual risk or watchpoint
