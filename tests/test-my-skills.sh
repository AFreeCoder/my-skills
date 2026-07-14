#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -P "$SCRIPT_DIR/.." && pwd)
CLI=$REPO_DIR/bin/my-skills
TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/my-skills-test.XXXXXX")

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_dir() {
  [ -d "$1" ] || fail "expected directory: $1"
}

assert_symlink() {
  [ -L "$1" ] || fail "expected symlink: $1"
}

assert_not_exists() {
  [ ! -e "$1" ] && [ ! -L "$1" ] || fail "expected path to be absent: $1"
}

assert_link_target() {
  local link=$1 expected=$2 actual
  actual=$(readlink "$link")
  [ "$actual" = "$expected" ] || fail "expected $link -> $expected, got $actual"
}

assert_resolves_to() {
  local link=$1 expected=$2 actual expected_real
  actual=$(cd -P "$link" && pwd)
  expected_real=$(cd -P "$expected" && pwd)
  [ "$actual" = "$expected_real" ] || fail "expected $link to resolve to $expected_real, got $actual"
}

run_cli() {
  MY_SKILLS_HOME=$REPO_DIR "$CLI" "$@"
}

expect_fail() {
  if "$@" >"$TMP_DIR/unexpected.out" 2>"$TMP_DIR/unexpected.err"; then
    fail "expected command to fail: $*"
  fi
}

new_project() {
  local dir
  dir=$(mktemp -d "$TMP_DIR/project.XXXXXX")
  printf '%s\n' "$dir"
}

test_init_creation_and_idempotence() {
  local project
  project=$(new_project)

  run_cli init --project "$project"
  assert_dir "$project/.agents/skills"
  assert_dir "$project/.claude"
  assert_symlink "$project/.claude/skills"
  assert_link_target "$project/.claude/skills" "../.agents/skills"

  run_cli init --project "$project"
  assert_link_target "$project/.claude/skills" "../.agents/skills"
}

test_init_conflicts() {
  local project

  project=$(new_project)
  mkdir -p "$project/.claude/skills"
  expect_fail run_cli init --project "$project"

  project=$(new_project)
  mkdir -p "$project/.claude" "$project/other"
  ln -s ../other "$project/.claude/skills"
  expect_fail run_cli init --project "$project"
}

test_link_single_multiple_and_idempotent() {
  local project
  project=$(new_project)

  run_cli link --project "$project" push-deploy webpage-clipper
  assert_resolves_to "$project/.agents/skills/push-deploy" "$REPO_DIR/skills/push-deploy"
  assert_resolves_to "$project/.agents/skills/webpage-clipper" "$REPO_DIR/skills/webpage-clipper"
  assert_link_target "$project/.claude/skills" "../.agents/skills"

  run_cli link --project "$project" push-deploy webpage-clipper
  assert_resolves_to "$project/.agents/skills/push-deploy" "$REPO_DIR/skills/push-deploy"
}

test_link_source_validation() {
  local project bad_home
  project=$(new_project)

  expect_fail run_cli link --project "$project" missing-skill
  expect_fail run_cli link --project "$project" BadName

  bad_home=$(mktemp -d "$TMP_DIR/bad-home.XXXXXX")
  mkdir -p "$bad_home/skills/no-skill-md"
  expect_fail env MY_SKILLS_HOME="$bad_home" "$CLI" link --project "$project" no-skill-md
}

test_link_batch_preflight_atomic() {
  local project
  project=$(new_project)
  mkdir -p "$project/.agents/skills/push-deploy"

  expect_fail run_cli link --project "$project" push-deploy webpage-clipper
  assert_not_exists "$project/.agents/skills/webpage-clipper"
}

test_unlink_correct_idempotent_and_conflicts() {
  local project
  project=$(new_project)

  run_cli link --project "$project" push-deploy webpage-clipper
  run_cli unlink --project "$project" push-deploy
  assert_not_exists "$project/.agents/skills/push-deploy"
  assert_resolves_to "$project/.agents/skills/webpage-clipper" "$REPO_DIR/skills/webpage-clipper"

  run_cli unlink --project "$project" push-deploy

  mkdir -p "$project/.agents/skills/push-deploy"
  expect_fail run_cli unlink --project "$project" push-deploy
}

test_unlink_batch_preflight_atomic() {
  local project
  project=$(new_project)

  run_cli link --project "$project" push-deploy webpage-clipper
  rm "$project/.agents/skills/webpage-clipper"
  ln -s /tmp "$project/.agents/skills/webpage-clipper"

  expect_fail run_cli unlink --project "$project" push-deploy webpage-clipper
  assert_resolves_to "$project/.agents/skills/push-deploy" "$REPO_DIR/skills/push-deploy"
}

test_project_detection() {
  local git_project nested plain

  git_project=$(new_project)
  git -C "$git_project" init -q
  mkdir -p "$git_project/a/b"
  (
    cd "$git_project/a/b"
    run_cli init
  )
  assert_symlink "$git_project/.claude/skills"

  plain=$(new_project)
  (
    cd "$plain"
    run_cli init
  )
  assert_symlink "$plain/.claude/skills"
}

test_symlink_invocation_resolves_home() {
  local bin_dir project
  bin_dir=$(mktemp -d "$TMP_DIR/bin.XXXXXX")
  project=$(new_project)
  ln -s "$CLI" "$bin_dir/my-skills"

  "$bin_dir/my-skills" link --project "$project" push-deploy
  assert_resolves_to "$project/.agents/skills/push-deploy" "$REPO_DIR/skills/push-deploy"
}

test_init_creation_and_idempotence
test_init_conflicts
test_link_single_multiple_and_idempotent
test_link_source_validation
test_link_batch_preflight_atomic
test_unlink_correct_idempotent_and_conflicts
test_unlink_batch_preflight_atomic
test_project_detection
test_symlink_invocation_resolves_home

printf 'All my-skills tests passed.\n'
