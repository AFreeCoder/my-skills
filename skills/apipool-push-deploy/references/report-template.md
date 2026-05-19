# Report Template

Use this template after push and deployment monitoring complete. Replace every placeholder with concrete values from the current release.

## Short version

```md
本次变更已推送到 `origin/main`，提交是 `<commit>`；本地工作区 `<clean-or-not>`。GitHub Actions 部署任务 `<run-id>` `<success-or-failure>`，我已通过 `ssh digitalocean` 盯到部署结束。

服务器当前代码是 `<live-commit>`，运行版本是 `<live-version>`，`sub2api` 当前状态为 `<container-health>`，容器创建时间/运行时长为 `<container-age>`。

对线上业务的判断是：`<business-impact-summary>`。`<user-visible-change-or-none>`。`<post-deploy-observation>`。

备份和回滚链路方面：`<db-backup-status>`，`<rollback-image-status>`，当前快速回滚路径是 `cd /opt/sub2api/deploy && ./rollback.sh image`。`<db-restore-note-if-needed>`。
```

## Full version

```md
本次变更已推送到 `origin/main`，提交是 `<pushed-commit>`；本地工作区 `<clean-or-not>`。GitHub Actions 的部署任务 `<run-id>` 已 `<run-result>`，我通过 `ssh digitalocean` 全程观察了远端构建、容器切换和健康检查。

当前线上状态：
- 服务器代码提交：`<live-commit>`
- 运行版本：`<live-version>`
- `sub2api` 容器：`<container-status>`
- 当前运行镜像：`<live-image-id>`
- 回退镜像：`<rollback-image-id>`

对线上业务的判断：
- `<business-impact-1>`
- `<business-impact-2>`
- `<watchpoint-or-none>`

部署保障结论：
- 数据库备份：`<db-backup-result>`
- 镜像回退标签：`<rollback-tag-result>`
- 自动化部署链路：`<pipeline-result>`
- 快速回滚方式：`cd /opt/sub2api/deploy && ./rollback.sh image`
- 数据库恢复方式：`cd /opt/sub2api/deploy && ./rollback.sh db-restore --with-image`

部署后观察：
- `<traffic-or-health-observation>`
- `<error-log-observation-or-none>`
- `<remaining-risk-or-none>`
```

## Field guidance

- `<clean-or-not>`: usually `是干净的` or `仍有未提交改动：...`
- `<success-or-failure>` / `<run-result>`: use exact workflow outcome such as `已成功完成` or `失败于 Deploy via SSH`
- `<business-impact-summary>`: summarize the real effect, not the code diff category
- `<user-visible-change-or-none>`: explicitly say if removed routes, removed UI entries, or model behavior changes exist
- `<post-deploy-observation>`: mention successful live traffic, health checks, or any error pattern worth monitoring
- `<db-backup-result>`: include the fresh `pre-deploy-*.sql.gz` filename when available
- `<rollback-tag-result>`: include `last-rollback-image.txt` or `rollback-latest` details when available

## Minimum facts to collect before sending the report

- pushed commit
- workflow run id and conclusion
- live commit and `backend/cmd/server/VERSION`
- `sub2api` health and creation time
- fresh pre-deploy backup filename
- `rollback-latest` image id or rollback metadata
