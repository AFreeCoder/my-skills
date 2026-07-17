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

assert_file_content() {
  local file=$1 expected=$2 actual
  actual=$(cat "$file")
  [ "$actual" = "$expected" ] || fail "unexpected content in $file: $actual"
}

assert_file_contains() {
  local file=$1 expected=$2
  grep -F "$expected" "$file" >/dev/null || fail "expected $file to contain: $expected"
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

run_cli_with_external_catalog() {
  MY_SKILLS_HOME=$REPO_DIR MY_SKILLS_EXTERNAL=$1 "$CLI" "${@:2}"
}

fake_npx_path() {
  local script
  script=$TMP_DIR/fake-npx
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'printf "%s\n" "$@" > "$MY_SKILLS_FAKE_NPX_OUTPUT"' \
    > "$script"
  chmod +x "$script"
  printf '%s\n' "$script"
}

test_list_skills() {
  local output expected
  output=$TMP_DIR/list.out
  expected=$(printf '%s\n' \
    'name	type	scope	source	description' \
    "apipool-push-deploy	self-built	project	$REPO_DIR/skills/apipool-push-deploy	-" \
    "apipool-sync-upstream	self-built	project	$REPO_DIR/skills/apipool-sync-upstream	-" \
    "push-deploy	self-built	project	$REPO_DIR/skills/push-deploy	-" \
    "webpage-clipper	self-built	project	$REPO_DIR/skills/webpage-clipper	-" \
    'vercel-agent-skills	favorite	project	vercel-labs/agent-skills	Vercel Labs Agent Skills collection' \
    'emilkowalski-skills	favorite	project	emilkowalski/skills	Emil Kowalski design and animation skills collection')

  run_cli list >"$output"
  assert_file_content "$output" "$expected"
  expect_fail run_cli list push-deploy
}

test_list_with_custom_catalog() {
  local catalog output
  catalog=$TMP_DIR/catalog.json
  output=$TMP_DIR/list-with-catalog.out
  printf '%s\n' \
    '{"third_party":[' \
    '{"name":"project-demo","source":"owner/project-demo","scope":"project","description":"Project demo skill"},' \
    '{"name":"global-demo","source":"owner/global-demo","scope":"global","description":"Global demo skill"}' \
    ']}' \
    > "$catalog"

  run_cli_with_external_catalog "$catalog" list >"$output"
  assert_file_contains "$output" 'project-demo	favorite	project	owner/project-demo	Project demo skill'
  assert_file_contains "$output" 'global-demo	favorite	global	owner/global-demo	Global demo skill'
}

test_external_add_catalog_entry() {
  local catalog output
  catalog=$TMP_DIR/external-add.json
  output=$TMP_DIR/external-add.out

  run_cli_with_external_catalog "$catalog" external add new-skill owner/new-skill --description 'New skill'
  run_cli_with_external_catalog "$catalog" list >"$output"
  assert_file_contains "$output" 'new-skill	favorite	project	owner/new-skill	New skill'

  run_cli_with_external_catalog "$catalog" external add global-skill https://github.com/owner/global-skill --scope global --description 'Global skill'
  run_cli_with_external_catalog "$catalog" list >"$output"
  assert_file_contains "$output" 'global-skill	favorite	global	https://github.com/owner/global-skill	Global skill'

  expect_fail run_cli_with_external_catalog "$catalog" external add new-skill owner/duplicate
  expect_fail run_cli_with_external_catalog "$catalog" external add BadName owner/bad
  expect_fail run_cli_with_external_catalog "$catalog" external add bad-source not-a-source
}

test_external_add_commits_default_catalog() {
  local repo output latest_subject
  repo=$(mktemp -d "$TMP_DIR/git-home.XXXXXX")
  output=$TMP_DIR/git-external-add.out

  mkdir -p "$repo/external"
  printf '%s\n' '{"third_party":[]}' > "$repo/external/skills.json"
  git -C "$repo" init -q
  git -C "$repo" config user.email test@example.com
  git -C "$repo" config user.name 'Test User'
  git -C "$repo" add external/skills.json
  git -C "$repo" commit -q -m 'init external catalog'

  MY_SKILLS_HOME=$repo "$CLI" external add committed-skill owner/committed --description 'Committed skill' --no-push >"$output"
  assert_file_contains "$output" 'added external skill: committed-skill -> owner/committed (project)'
  latest_subject=$(git -C "$repo" log -1 --format=%s)
  [ "$latest_subject" = 'chore: add external skill committed-skill' ] || fail "unexpected commit subject: $latest_subject"

  MY_SKILLS_HOME=$repo "$CLI" list >"$output"
  assert_file_contains "$output" 'committed-skill	favorite	project	owner/committed	Committed skill'
}

test_add_self_built_skill() {
  local project
  project=$(new_project)

  run_cli add --project "$project" push-deploy
  assert_resolves_to "$project/.agents/skills/push-deploy" "$REPO_DIR/skills/push-deploy"
  expect_fail run_cli add --project "$project" push-deploy --yes
}

test_add_catalog_entry() {
  local catalog fake output
  catalog=$TMP_DIR/catalog-add.json
  output=$TMP_DIR/fake-npx.out
  fake=$(fake_npx_path)
  printf '%s\n' \
    '{"third_party":[' \
    '{"name":"project-demo","source":"owner/project-demo","scope":"project","description":"Project demo skill"},' \
    '{"name":"global-demo","source":"owner/global-demo","scope":"global","description":"Global demo skill"}' \
    ']}' \
    > "$catalog"

  MY_SKILLS_FAKE_NPX_OUTPUT=$output MY_SKILLS_NPX=$fake run_cli_with_external_catalog "$catalog" add project-demo --skill alpha --yes
  assert_file_content "$output" 'skills@latest
add
owner/project-demo
--skill
alpha
--yes'

  MY_SKILLS_FAKE_NPX_OUTPUT=$output MY_SKILLS_NPX=$fake run_cli_with_external_catalog "$catalog" add global-demo --yes
  assert_file_content "$output" 'skills@latest
add
owner/global-demo
--global
--yes'

  MY_SKILLS_FAKE_NPX_OUTPUT=$output MY_SKILLS_NPX=$fake run_cli_with_external_catalog "$catalog" add global-demo --scope project --yes
  assert_file_content "$output" 'skills@latest
add
owner/global-demo
--yes'

  MY_SKILLS_FAKE_NPX_OUTPUT=$output MY_SKILLS_NPX=$fake run_cli_with_external_catalog "$catalog" add project-demo
  assert_file_content "$output" 'skills@latest
add
owner/project-demo'
}

test_add_raw_source() {
  local catalog fake output
  catalog=$TMP_DIR/catalog-raw.json
  output=$TMP_DIR/fake-npx-raw.out
  fake=$(fake_npx_path)
  printf '%s\n' '{"third_party":[]}' > "$catalog"

  MY_SKILLS_FAKE_NPX_OUTPUT=$output MY_SKILLS_NPX=$fake run_cli_with_external_catalog "$catalog" add owner/raw-skill --list
  assert_file_content "$output" 'skills@latest
add
owner/raw-skill
--list'

  expect_fail run_cli_with_external_catalog "$catalog" add unknown-alias
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

test_list_skills
test_list_with_custom_catalog
test_external_add_catalog_entry
test_external_add_commits_default_catalog
test_add_self_built_skill
test_add_catalog_entry
test_add_raw_source
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
