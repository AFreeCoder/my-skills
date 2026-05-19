---
name: apipool-push-deploy
description: Review APIPool production risk before pushing code to `origin/main`, verify that the GitHub Actions auto-deploy flow will back up the database and previous image correctly, push the prepared commits, and monitor the DigitalOcean rollout until the new `sub2api` container is healthy. Use when Codex needs to “推送代码”“上线”“盯着部署过程”“确认数据库/镜像备份是否正常”“确认能否快速回滚” for the APIPool repository.
---

# APIPool Push Deploy

## Overview

Use this skill after the code changes are ready to go live. Review business impact first, confirm deployment safeguards, push `main`, then watch GitHub Actions and `ssh digitalocean` until the live container is healthy again.

## Workflow

### 1. Build the release context

- Confirm the current branch, worktree status, and remotes.
- Identify the exact commit range being pushed.
- Decide whether the release includes any high-risk areas:
  - upstream sync
  - version alignment
  - deploy or rollback script changes
  - auth, OAuth, billing, model routing, or account scheduling changes
  - feature removal or route removal
- If the work is an upstream sync, open the latest `docs/plans/*-upstream-sync-review.md` first.
- Read the deployment-critical files before pushing:
  - `.github/workflows/deploy.yml`
  - `deploy/rollback.sh`
  - `deploy/docker-compose.deploy.yml`
  - `deploy/version_resolver.sh`
  - the deployment and rollback section in `README.md`
- Open `references/deployment-checks.md` for the exact commands and success signals.

### 2. Make the pre-push judgment explicit

- Before pushing, answer these questions in plain language:
  - What may affect online behavior?
  - Why should the deployment pipeline still create a DB backup and rollback image correctly?
  - If the release goes wrong, what is the fastest safe rollback path?
- Call out user-visible removals or API contract changes directly.
- Treat these as especially high risk:
  - removed routes, UI entries, or model aliases
  - quota, billing, or free-tier behavior changes
  - OAuth or login/session behavior changes
  - deployment, compose, version, or rollback changes
- If a safeguard looks broken, stop before pushing and explain the blocker.

### 3. Verify locally

- Run the relevant local checks for the current diff.
- For upstream sync, default to the broader project regression baseline instead of only targeted tests.
- If deploy files changed, validate the deploy compose config too.
- If some checks cannot run, state the exact blocker and decide whether the remaining evidence is strong enough to proceed.

### 4. Push and find the deployment

- Ensure the worktree only contains intended changes.
- Commit if needed, then push with `git push origin main`.
- Immediately locate the triggered workflow run for `Deploy to DigitalOcean`.
- Watch the workflow instead of assuming success from the push result.

### 5. Monitor GitHub Actions and the server in parallel

- Keep GitHub Actions and the DigitalOcean server under observation at the same time.
- On the server, verify four things in order:
  1. the repo `HEAD` has advanced to the pushed commit
  2. a fresh `pre-deploy-*.sql.gz` exists
  3. `last-rollback-image.txt` points to the previous live commit or image
  4. the `sub2api` container is recreated and becomes healthy
- A repo reset alone is not enough. Wait until the new container is up and healthy.
- While the image is still building, treat “old container healthy, build in progress” as a safe intermediate state and keep watching.

### 6. Handle failure modes deliberately

- If the workflow fails, collect:
  - the failing Actions step
  - current server repo/version state
  - container and image state
  - recent `sub2api` logs
- If the new app container becomes unhealthy after the switch, prioritize fast service recovery:
  - first choice: `cd /opt/sub2api/deploy && ./rollback.sh image`
  - use `db-restore --with-image` only when the problem is data-related or persisted state clearly needs to be restored
- Execute database restore only with explicit confirmation unless the user has already delegated incident recovery end-to-end.
- After rollback, confirm the service is healthy again and report the rollback tag or restored commit.

### 7. Report the outcome

- Draft the final update with `references/report-template.md`.
- Fill in every section with concrete values from the actual push and deploy, not estimates.
- Always state:
  - pushed commit and whether the local worktree is clean
  - deployment run id and result
  - live commit, live version, and container health
  - whether DB backup and rollback image tagging actually happened
  - any remaining business risk or watchpoint after release

## Reference Use

- Open `references/deployment-checks.md` for the concrete commands, acceptance criteria, and rollback cues.
- Open `references/report-template.md` when preparing the final deployment summary.
- Re-read the repo deployment files if the current diff touches them. Do not rely on stale assumptions.
