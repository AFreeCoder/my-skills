# APIPool Local Customizations

将这份清单当作“高风险语义覆盖提醒”，不要把它当作完整真相来源。实际同步时始终重新运行 `scripts/collect_upstream_sync_context.sh`，再结合当前 diff 做判断。

这份文件需要持续维护。每次 upstream 同步完成后，都要反问一次：本轮是否出现了新的长期定制点、已失效的旧定制点，或新的高风险语义覆盖区域；如果有，立刻更新本文件。

## 长期定制主线

### 1. 品牌与文档体验

以下文件属于品牌与文档体验高风险区域；其中部分长期偏离上游，部分是仍待 APIPool 品牌改写的债务。合入时必须确认它们没有被上游重新拉回到 Sub2API 默认行为，也不要把未改写的债务误判成已完成定制：

- `README.md`
- `README_CN.md`
- `README_JA.md`
- `frontend/public/logo.svg`
- `frontend/src/i18n/locales/`
- `frontend/src/components/layout/`
- `frontend/src/views/HomeView.vue`
- `frontend/src/views/docs/`
- `frontend/src/docs/`

重点检查：

- 名称是否仍为 APIPool，而不是 Sub2API
- 多语言文案、占位符、引导文案、品牌提示是否仍保留 APIPool 语义
- 首页、帮助文档、导航入口是否仍指向当前项目的文档体验
- 管理台和用户侧展示文案是否仍符合当前站点定位
- `README_CN.md` / `README_JA.md` 是已知品牌债务：截至 2026-05-11，这两个文件仍主要保留 upstream Sub2API 文案。本地同步时不要默认认为它们已经完成 APIPool 品牌改写；若上游再次修改这两个文件，应明确判断是继续接受 upstream 文档、只吸收链接修复，还是另起独立改写任务。

### 2. 部署、回滚与版本链路

以下文件承载了当前项目的生产部署假设：

- `.github/workflows/deploy.yml`
- `deploy/rollback.sh`
- `deploy/version_resolver.sh`
- `deploy/docker-compose.deploy.yml`
- `deploy/docker-compose.local.yml`
- `deploy/docker-compose.yml`
- `deploy/ROLLBACK_CN.md`
- `backend/cmd/server/VERSION`

重点检查：

- 仍然面向 DigitalOcean 单实例 Compose 部署
- 仍然保留部署前数据库备份与镜像回退标签逻辑
- 版本解析、构建参数与 release/deploy 语义保持一致
- 不要只看 `upstream/main` 上的 `backend/cmd/server/VERSION`；还要同时看 `git tag --merged upstream/main --sort=-version:refname | head -1`
- 若 upstream release tag 已推进而 `VERSION` 文件未推进，APIPool 如需让左上角和运行时版本与发布号一致，应在纯 upstream merge 后追加独立 `chore(version)` 提交，而不是混进 merge commit
- 左上角展示版本来自公开设置里的运行时版本，不会因为 merge commit 或 release tag 自动变化

### 3. OpenAI OAuth / Codex 兼容逻辑

这是当前项目最容易出现“无冲突但语义回退”的区域之一：

- `backend/internal/handler/admin/openai_oauth_handler.go`
- `backend/internal/service/openai_*`
- `backend/internal/handler/openai_gateway_handler.go`
- `backend/internal/service/openai_gateway_service.go`
- `backend/internal/service/token_refresh_service.go`
- `backend/internal/service/ratelimit_service.go`

重点检查：

- Codex/OpenAI OAuth 请求兼容是否还在
- reasoning / transcript item 归一化逻辑是否还在
- 403、限流、停用账号、并发获取失败等映射是否仍符合当前项目语义
- plan type 同步、账号状态判断、回退逻辑是否被上游新实现覆盖

### 4. Kiro / OpenClaw 本地扩展

Kiro 账号、OAuth、token refresh、网关转发与前端配置导入是 APIPool 本地长期扩展；`upstream/main` 通常没有这条链路，合入时要避免因为上游 provider set、handler、router、account type 或前端账号表单重排而被“无冲突删除”。

- `backend/internal/service/kiro_*`
- `backend/internal/service/gateway_service_kiro.go`
- `backend/internal/handler/admin/kiro_oauth_handler.go`
- `backend/internal/handler/admin/account_handler_kiro_test.go`
- `backend/internal/handler/dto/account_kiro_test.go`
- `frontend/src/api/admin/kiro.ts`
- `frontend/src/composables/useKiroOAuth.ts`
- `frontend/src/utils/openclawConfig.ts`
- `frontend/src/utils/__tests__/openclawConfig.spec.ts`

重点检查：

- `handler.AdminHandlers`、`handler.ProvideAdminHandlers`、`backend/internal/server/routes/admin.go` 仍包含 Kiro OAuth 路由
- `service.ProviderSet`、`TokenRefreshService`、`KiroTokenProvider`、`AccountTestService` 仍能同时接入 Kiro 与 upstream 新增的 token/channel/monitor provider
- 前端账号创建/编辑、OAuth 授权流程、OpenClaw 配置导入仍保留 Kiro 类型与字段映射
- 上游删除或重排 account capability、credentials builder、provider set 时，不要把 Kiro 当作“已被 upstream 删除的旧代码”一起移除

### 5. 管理后台行为与项目默认值

以下区域承载了 APIPool 的后台行为差异：

- `frontend/src/views/admin/SettingsView.vue`
- `frontend/src/router/index.ts`
- `frontend/src/components/layout/AppSidebar.vue`
- `frontend/src/views/user/PurchaseSubscriptionView.vue`
- `frontend/src/views/user/PaymentView.vue`
- `frontend/src/views/user/PaymentResultView.vue`
- `frontend/src/views/user/AirwallexPaymentView.vue`
- `frontend/src/views/admin/BackupView.vue`
- `frontend/src/views/admin/AccountsView.vue`
- `backend/internal/config/`
- `backend/internal/server/routes/admin.go`
- `backend/internal/service/setting_service.go`
- `backend/internal/handler/admin/`

重点检查：

- 是否保留了当前项目对备份、设置项、帮助入口、账号筛选等行为的取舍
- `/purchase` 是否仍然指向 APIPool 现有的 iframe 充值页，而不是被 upstream 内建支付页替换
- `purchase_subscription_enabled` / `purchase_subscription_url` 这组系统设置字段是否仍然贯通到公开设置、侧边栏入口和用户路由
- 内建支付的 `/orders`、支付设置、支付迁移可以保留，但不能接管既有 purchase iframe 充值入口
- upstream 新增支付 provider、支付结果页、支付 SDK 或多币种逻辑时，要同时复核 `/purchase` iframe 订阅购买入口、`/payment/*` 内建支付入口和支付回调路由是否仍是并存关系
- 是否意外重新暴露了已被 APIPool 禁用的后台入口，例如备份恢复路由
- 默认值是否仍与当前生产约定一致
- 新增配置是否需要同步补到 `deploy/.env.example`、`deploy/config.example.yaml` 和后台表单
- 表格分页默认值仍然由后台 `table_default_page_size` / `table_page_size_options` 统一控制，不要重新引入全局 `table-page-size` localStorage 持久化覆盖系统默认值

## 高风险重叠模式

只要上游更新命中以下任一模式，就不要满足于“能编译通过”：

- `backend/internal/service/openai_*`
- `backend/internal/service/ratelimit_service.go`
- `backend/internal/service/token_refresh_service.go`
- `backend/internal/service/kiro_*`
- `backend/internal/service/gateway_service_kiro.go`
- `backend/internal/handler/admin/`
- `backend/internal/config/`
- `backend/internal/server/routes/admin.go`
- `frontend/src/components/layout/AppHeader.vue`
- `frontend/src/components/layout/AppSidebar.vue`
- `frontend/src/composables/usePersistedPageSize.ts`
- `frontend/src/composables/useTableLoader.ts`
- `frontend/src/components/common/Pagination.vue`
- `frontend/src/i18n/locales/.*`
- `frontend/src/views/admin/SettingsView.vue`
- `frontend/src/views/user/PurchaseSubscriptionView.vue`
- `frontend/src/views/user/PaymentView.vue`
- `frontend/src/views/user/PaymentResultView.vue`
- `frontend/src/views/user/AirwallexPaymentView.vue`
- `frontend/src/views/admin/BackupView.vue`
- `frontend/src/api/admin/kiro.ts`
- `frontend/src/composables/useKiroOAuth.ts`
- `frontend/src/utils/openclawConfig.ts`
- `frontend/src/views/docs/`
- `frontend/src/docs/`
- `deploy/`
- `.github/workflows/deploy.yml`
- `README.md`
- `README_CN.md`
- `README_JA.md`
- `backend/cmd/server/VERSION`

## 审查问题

在高风险文件上，至少回答下面 5 个问题：

1. 上游这次改变的“行为”是什么，而不只是改了哪些行？
2. 这个行为会不会覆盖 APIPool 已有的品牌、部署或网关语义？
3. 如果保留本地逻辑，是否还需要手动吸收上游修复中的一部分实现？
4. 这次改动会不会要求同步调整配置样例、文档、前端表单或测试基线？
5. 即使没有 Git 冲突，最终代码是否仍满足当前项目的生产假设？
6. 如果命中了版本链路，最新 upstream release tag、upstream/main 上的 `VERSION`、本地最终 `VERSION` 是否彼此一致；若不一致，差异是否是有意保留的？
