# Upstream Sync Testing Matrix

对 upstream 同步，默认使用“完整回归优先”的策略。不要只因为改动看起来小，就跳过跨层验证。

这份矩阵不是静态文档。只要仓库的测试入口、CI、构建方式、部署链路或高风险模块发生变化，就要在当轮同步里一起更新它。

## 默认回归基线

以下命令是本技能的默认测试基线：

```bash
cd backend && go test -tags=unit ./...
cd backend && make test-unit
cd backend && go test -tags=integration ./...
cd backend && make test-integration
cd backend && golangci-lint run ./...
pnpm --dir frontend run lint:check
pnpm --dir frontend run typecheck
```

补充说明：

- `make test-unit` / `make test-integration` 是当前仓库 CI 使用的包装入口，分别对应 `go test -tags=unit ./...` 和 `go test -tags=integration ./...`。
- upstream 同步评审里，至少记录你实际跑的是直接 `go test -tags=...` 还是 `make test-*`，不要只写“后端测试已过”。

## 需要追加的测试

### 前端逻辑或界面受影响

命中以下任一情况时，追加：

- `frontend/src/**`
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- 路由、文案、组件、视图、store、composable 改动

执行：

```bash
pnpm --dir frontend run test:run
```

如果命中表格分页默认值或相关 composable（`usePersistedPageSize`、`useTableLoader`、`Pagination.vue`），额外确认系统默认值不会被旧 localStorage 覆盖：

```bash
pnpm --dir frontend run test:run -- src/composables/__tests__/usePersistedPageSize.spec.ts
```

### 构建、部署或版本链路受影响

命中以下任一情况时，追加：

- `deploy/**`
- `.github/workflows/deploy.yml`
- `backend/cmd/server/VERSION`
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`

执行：

```bash
git tag --merged upstream/main --sort=-version:refname | head -1
cat backend/cmd/server/VERSION
make build
docker compose -f deploy/docker-compose.deploy.yml config -q
docker compose -f deploy/docker-compose.local.yml config -q
bash deploy/version_resolver.sh resolve .
bash scripts/collect_upstream_sync_context.sh --no-fetch
```

补充说明：

- 如果 Compose 文件使用了 `${VAR:?message}` 这类必填环境变量校验，做 `config -q` 语法检查时要显式提供最小占位值，例如 `POSTGRES_PASSWORD=dummy docker compose ... config -q`，或使用能满足校验的 `--env-file`。
- 若 `config -q` 失败，先区分是 YAML/Compose 语法错误，还是仅仅因为当前 shell 缺少必填环境变量；评审文档里要把两者分开记录。

核对点：

- 最新 upstream release tag 是否已纳入当前 merge 结果
- `backend/cmd/server/VERSION` 是否符合当前项目希望对外展示的版本号
- 如果上游 tag 已推进但 `VERSION` 未推进，是否需要单独补一个版本对齐提交，而不是修改 merge commit
- 若已完成部署，至少再核对一次 `docker exec sub2api /app/sub2api --version` 或等价的线上版本输出

### 配置或后台设置受影响

命中以下任一情况时，追加人工核对：

- `backend/internal/config/**`
- `deploy/.env.example`
- `deploy/config.example.yaml`
- `frontend/src/views/admin/SettingsView.vue`

核对点：

- 配置默认值是否一致
- 新增配置是否同时出现在样例文件、后端读取逻辑和前端表单中
- 配置校验与错误提示是否仍匹配

### OpenAI OAuth / Codex / 网关链路受影响

命中以下任一情况时，额外关注：

- `backend/internal/service/openai_*`
- `backend/internal/handler/openai_*`
- `backend/internal/service/token_refresh_service.go`
- `backend/internal/service/ratelimit_service.go`

建议至少补做：

- 相关模块测试再次单独跑一遍，便于快速定位失败
- 检查是否需要更新 API contract 测试、handler 测试或服务层测试
- 检查前端账号管理和设置页是否仍能表达新增/变化的后端行为

### Kiro / OpenClaw 本地扩展受影响

命中以下任一情况时，额外关注：

- `backend/internal/service/kiro_*`
- `backend/internal/service/gateway_service_kiro.go`
- `backend/internal/handler/admin/kiro_oauth_handler.go`
- `backend/internal/server/routes/admin.go`
- `backend/internal/handler/wire.go`
- `backend/internal/service/wire.go`
- `frontend/src/api/admin/kiro.ts`
- `frontend/src/composables/useKiroOAuth.ts`
- `frontend/src/utils/openclawConfig.ts`
- 前端账号创建/编辑、credentials builder、account type capability 相关文件

建议至少补做：

- `go test -tags=unit ./internal/service -run 'Kiro|GatewayServiceKiro|AccountTestService'`
- `go test -tags=unit ./internal/handler/admin -run Kiro`
- `pnpm --dir frontend run test:run -- openclawConfig`
- 复核 wire 生成结果里 Kiro provider 与 upstream 新增 provider 是否同时存在

## 测试结果记录要求

评审文档里不要只写“已测试”。至少写清楚：

- 运行了哪些命令
- 哪些命令通过
- 哪些命令因环境限制未运行
- 额外做了哪些人工验证
- 剩余风险与建议观察点是什么

若 integration 依赖 Docker daemon、testcontainers 或外部探针服务（例如 TLS 指纹抓取站点），还要额外写清：

- 失败是否由本地环境/外部服务引起，而不是代码断言失败
- 是否通过启动 Docker、重跑失败包、或在 merge 前基线 worktree 复跑做过归因
