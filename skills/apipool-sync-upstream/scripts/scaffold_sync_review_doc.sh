#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scaffold_sync_review_doc.sh [--output PATH] [--upstream-ref upstream/main] [--base-ref HEAD] [--force]

Create a review summary document for an upstream/main sync.

Keep this template aligned with current review expectations. When a sync uncovers
missing sections, risk fields, or validation items, update this scaffold in the
same turn.
EOF
}

OUTPUT=""
UPSTREAM_REF="upstream/main"
BASE_REF="HEAD"
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT="${2:?missing value for --output}"
      shift 2
      ;;
    --upstream-ref)
      UPSTREAM_REF="${2:?missing value for --upstream-ref}"
      shift 2
      ;;
    --base-ref)
      BASE_REF="${2:?missing value for --base-ref}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "error: not inside a git repository" >&2
  exit 1
}
cd "$ROOT"

git rev-parse --verify "$BASE_REF" >/dev/null 2>&1 || {
  echo "error: base ref not found: $BASE_REF" >&2
  exit 1
}
git rev-parse --verify "$UPSTREAM_REF" >/dev/null 2>&1 || {
  echo "error: upstream ref not found: $UPSTREAM_REF" >&2
  exit 1
}

TODAY="$(date +%F)"
CURRENT_BRANCH="$(git branch --show-current || true)"
BASE_SHA="$(git rev-parse "$BASE_REF")"
UPSTREAM_SHA="$(git rev-parse "$UPSTREAM_REF")"
MERGE_BASE="$(git merge-base "$BASE_REF" "$UPSTREAM_REF")"
BASE_VERSION="$(git show "${BASE_REF}:backend/cmd/server/VERSION" 2>/dev/null | tr -d '\r\n' || true)"
UPSTREAM_VERSION="$(git show "${UPSTREAM_REF}:backend/cmd/server/VERSION" 2>/dev/null | tr -d '\r\n' || true)"
UPSTREAM_LATEST_TAG="$(git tag --merged "$UPSTREAM_REF" --sort=-version:refname | grep -E '^v?[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$' | head -1 || true)"

if [[ -z "$OUTPUT" ]]; then
  OUTPUT="$ROOT/docs/plans/${TODAY}-upstream-sync-review.md"
fi

if [[ -e "$OUTPUT" && "$FORCE" -ne 1 ]]; then
  echo "error: output already exists: $OUTPUT" >&2
  echo "hint: pass --force to overwrite it" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

cat > "$OUTPUT" <<EOF
# 上游同步评审记录（${TODAY}）

## 基线

- 当前分支：\`${CURRENT_BRANCH:-"(detached)"}\`
- 合入前基线：\`$BASE_REF\`
- 合入前 SHA：\`$BASE_SHA\`
- 上游引用：\`$UPSTREAM_REF\`
- 上游 SHA：\`$UPSTREAM_SHA\`
- merge-base：\`$MERGE_BASE\`
- 同步方式：\`git merge $UPSTREAM_REF\`
- 当前运行时版本：\`${BASE_VERSION:-"(missing)"}\`
- upstream/main 版本文件：\`${UPSTREAM_VERSION:-"(missing)"}\`
- upstream 最新 release tag：\`${UPSTREAM_LATEST_TAG:-"(none)"}\`

## 上游更新摘要

- [ ] 概述上游这次新增/修复了什么
- [ ] 标出命中的高风险模块
- [ ] 标出需要额外吸收但不能覆盖本地逻辑的实现
- [ ] 若 tag 与 VERSION 不一致，说明版本链路差异

## 本地定制保护点

- [ ] 品牌/APIPool 文案与入口
- [ ] 部署、回滚、版本链路
- [ ] OpenAI OAuth / Codex 兼容逻辑
- [ ] 管理后台行为与默认配置

## 冲突与取舍

- [ ] 记录显式 Git 冲突文件
- [ ] 记录无冲突但发生语义审查的文件
- [ ] 说明最终保留了哪些 APIPool 行为，吸收了哪些 upstream 修复
- [ ] 若补了版本对齐提交，记录为何拆成独立提交以及对应 commit

## 测试记录

- [ ] \`cd backend && go test -tags=unit ./...\`
- [ ] \`cd backend && make test-unit\`
- [ ] \`cd backend && go test -tags=integration ./...\`
- [ ] \`cd backend && make test-integration\`
- [ ] \`cd backend && golangci-lint run ./...\`
- [ ] \`pnpm --dir frontend run lint:check\`
- [ ] \`pnpm --dir frontend run typecheck\`
- [ ] \`pnpm --dir frontend run test:run\`（如前端逻辑受影响）
- [ ] \`git tag --merged upstream/main --sort=-version:refname | head -1\`（如版本链路受影响）
- [ ] \`cat backend/cmd/server/VERSION\`（如版本链路受影响）
- [ ] \`make build\`（如构建/发布链路受影响）
- [ ] \`docker compose -f deploy/docker-compose.deploy.yml config -q\`（如部署链路受影响）
- [ ] \`docker compose -f deploy/docker-compose.local.yml config -q\`（如部署链路受影响）
- [ ] \`bash deploy/version_resolver.sh resolve .\`（如版本链路受影响）
- [ ] \`bash scripts/collect_upstream_sync_context.sh --no-fetch\`
- [ ] 部署后版本输出 / 页面版本人工核对：
- [ ] 其他专项验证：

## 剩余风险与观察点

- [ ] 记录尚未完全验证的风险
- [ ] 记录是否需要灰度、额外监控或回滚预案

## 结论

- [ ] 是否建议合入/保留当前 merge 结果
- [ ] 如已提交，记录 merge commit / tag / PR / 备注
EOF

printf '%s\n' "$OUTPUT"
