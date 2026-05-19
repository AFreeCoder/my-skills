#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  collect_upstream_sync_context.sh [--upstream-ref upstream/main] [--base-ref HEAD] [--output PATH] [--no-fetch]

Collect the current sync context between the current work and upstream/main:
- repo and branch info
- current working tree status
- merge-base
- version chain context
- local-only and upstream-only commits
- changed files on both sides
- overlap files
- high-risk overlap files

Keep this script aligned with the repository. When new long-lived customization
areas or high-risk overlap patterns appear, update the high-risk matcher in the
same sync turn.
EOF
}

UPSTREAM_REF="upstream/main"
BASE_REF="HEAD"
OUTPUT=""
NO_FETCH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream-ref)
      UPSTREAM_REF="${2:?missing value for --upstream-ref}"
      shift 2
      ;;
    --base-ref)
      BASE_REF="${2:?missing value for --base-ref}"
      shift 2
      ;;
    --output)
      OUTPUT="${2:?missing value for --output}"
      shift 2
      ;;
    --no-fetch)
      NO_FETCH=1
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

if [[ "$NO_FETCH" -eq 0 ]]; then
  if git remote get-url upstream >/dev/null 2>&1; then
    git fetch upstream main --tags >/dev/null
  else
    echo "error: remote 'upstream' is not configured" >&2
    exit 1
  fi
fi

git rev-parse --verify "$BASE_REF" >/dev/null 2>&1 || {
  echo "error: base ref not found: $BASE_REF" >&2
  exit 1
}
git rev-parse --verify "$UPSTREAM_REF" >/dev/null 2>&1 || {
  echo "error: upstream ref not found: $UPSTREAM_REF" >&2
  exit 1
}

MERGE_BASE="$(git merge-base "$BASE_REF" "$UPSTREAM_REF")"
HEAD_SHA="$(git rev-parse "$BASE_REF")"
UPSTREAM_SHA="$(git rev-parse "$UPSTREAM_REF")"
CURRENT_BRANCH="$(git branch --show-current || true)"
STATUS_OUTPUT="$(git status -sb)"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

LOCAL_FILES="$TMPDIR/local_files.txt"
UPSTREAM_FILES="$TMPDIR/upstream_files.txt"
OVERLAP_FILES="$TMPDIR/overlap_files.txt"
HIGH_RISK_FILES="$TMPDIR/high_risk_overlap.txt"
HIGH_RISK_UPSTREAM_FILES="$TMPDIR/high_risk_upstream.txt"

git diff --name-only "$MERGE_BASE..$BASE_REF" | LC_ALL=C sort -u > "$LOCAL_FILES"
git diff --name-only "$MERGE_BASE..$UPSTREAM_REF" | LC_ALL=C sort -u > "$UPSTREAM_FILES"
grep -Fxf "$LOCAL_FILES" "$UPSTREAM_FILES" | LC_ALL=C sort -u > "$OVERLAP_FILES" || true

HIGH_RISK_PATTERN='^(backend/internal/service/openai_.*|backend/internal/service/ratelimit_service\.go|backend/internal/service/token_refresh_service\.go|backend/internal/handler/admin/.*|backend/internal/config/.*|backend/internal/server/routes/admin\.go|frontend/src/components/layout/AppHeader\.vue|frontend/src/components/layout/AppSidebar\.vue|frontend/src/i18n/locales/.*|frontend/src/views/admin/SettingsView\.vue|frontend/src/views/admin/BackupView\.vue|frontend/src/views/user/PurchaseSubscriptionView\.vue|frontend/src/views/docs/.*|frontend/src/docs/.*|frontend/src/views/HomeView\.vue|deploy/.*|\.github/workflows/deploy\.yml|README\.md|backend/cmd/server/VERSION)$'
if [[ -s "$OVERLAP_FILES" ]]; then
  grep -E "$HIGH_RISK_PATTERN" "$OVERLAP_FILES" || true
else
  true
fi > "$HIGH_RISK_FILES"

if [[ -s "$UPSTREAM_FILES" ]]; then
  grep -E "$HIGH_RISK_PATTERN" "$UPSTREAM_FILES" || true
else
  true
fi > "$HIGH_RISK_UPSTREAM_FILES"

VERSION_FILE_PATH="backend/cmd/server/VERSION"
RELEASE_TAG_REGEX='^v?[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$'

normalize_release_tag() {
  local value="${1:-}"
  value="${value#v}"
  printf '%s\n' "$value"
}

read_version_file_at_ref() {
  local ref="$1"
  git show "${ref}:${VERSION_FILE_PATH}" 2>/dev/null | tr -d '\r\n' || true
}

latest_release_tag_for_ref() {
  git tag --merged "$1" --sort=-version:refname | grep -E "$RELEASE_TAG_REGEX" | head -1 || true
}

BASE_VERSION="$(read_version_file_at_ref "$BASE_REF")"
UPSTREAM_VERSION="$(read_version_file_at_ref "$UPSTREAM_REF")"
BASE_LATEST_TAG="$(latest_release_tag_for_ref "$BASE_REF")"
UPSTREAM_LATEST_TAG="$(latest_release_tag_for_ref "$UPSTREAM_REF")"
BASE_LATEST_TAG_VERSION="$(normalize_release_tag "$BASE_LATEST_TAG")"
UPSTREAM_LATEST_TAG_VERSION="$(normalize_release_tag "$UPSTREAM_LATEST_TAG")"

VERSION_ALIGNMENT_NOTES="$TMPDIR/version_alignment_notes.txt"
{
  if [[ -n "$UPSTREAM_LATEST_TAG" && -n "$UPSTREAM_VERSION" && "$UPSTREAM_LATEST_TAG_VERSION" != "$UPSTREAM_VERSION" ]]; then
    echo "upstream latest release tag is ${UPSTREAM_LATEST_TAG}, but ${UPSTREAM_REF}:${VERSION_FILE_PATH} is ${UPSTREAM_VERSION}"
  fi
  if [[ -n "$UPSTREAM_LATEST_TAG" && -n "$BASE_VERSION" && "$UPSTREAM_LATEST_TAG_VERSION" != "$BASE_VERSION" ]]; then
    echo "current ${BASE_REF}:${VERSION_FILE_PATH} (${BASE_VERSION}) does not match upstream latest release tag ${UPSTREAM_LATEST_TAG}"
  fi
} > "$VERSION_ALIGNMENT_NOTES"

render_file_list() {
  local path="$1"
  if [[ -s "$path" ]]; then
    sed 's/^/- /' "$path"
  else
    echo "- (none)"
  fi
}

render_commit_list() {
  local range="$1"
  local output
  output="$(git log --oneline --decorate --no-merges "$range" | sed -n '1,50p')"
  if [[ -n "$output" ]]; then
    printf '%s\n' "$output" | sed 's/^/- /'
  else
    echo "- (none)"
  fi
}

REPORT="$(cat <<EOF
# Upstream Sync Context

## Repository
- root: $ROOT
- branch: ${CURRENT_BRANCH:-"(detached)"}
- base ref: $BASE_REF
- base sha: $HEAD_SHA
- upstream ref: $UPSTREAM_REF
- upstream sha: $UPSTREAM_SHA
- merge-base: $MERGE_BASE

## Working Tree
\`\`\`
$STATUS_OUTPUT
\`\`\`

## Version Chain
- ${BASE_REF} ${VERSION_FILE_PATH}: ${BASE_VERSION:-"(missing)"}
- ${BASE_REF} latest merged release tag: ${BASE_LATEST_TAG:-"(none)"}
- ${UPSTREAM_REF} ${VERSION_FILE_PATH}: ${UPSTREAM_VERSION:-"(missing)"}
- ${UPSTREAM_REF} latest merged release tag: ${UPSTREAM_LATEST_TAG:-"(none)"}

## Version Alignment Notes
$(render_file_list "$VERSION_ALIGNMENT_NOTES")

## Local-only commits
$(render_commit_list "$UPSTREAM_REF..$BASE_REF")

## Upstream-only commits
$(render_commit_list "$BASE_REF..$UPSTREAM_REF")

## Files changed on local side since merge-base
$(render_file_list "$LOCAL_FILES")

## Files changed on upstream side since merge-base
$(render_file_list "$UPSTREAM_FILES")

## High-risk files changed on upstream side since merge-base
$(render_file_list "$HIGH_RISK_UPSTREAM_FILES")

## Overlap files
$(render_file_list "$OVERLAP_FILES")

## High-risk overlap files
$(render_file_list "$HIGH_RISK_FILES")
EOF
)"

if [[ -n "$OUTPUT" ]]; then
  mkdir -p "$(dirname "$OUTPUT")"
  printf '%s\n' "$REPORT" > "$OUTPUT"
else
  printf '%s\n' "$REPORT"
fi
