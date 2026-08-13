---
name: push-deploy
description: Use when releasing code to production or staging, auditing unpublished or mixed-scope branch/worktree history, pushing deployment commits, monitoring CI/CD, verifying backups and rollback readiness, handling deployment failures, or restoring live service during a release.
---

# Push Deploy

## Overview

Use this skill when code is ready to release and the user wants the agent to push, trigger deployment, monitor rollout, and verify recovery safeguards. The skill defines release discipline only; project-specific facts must come from the target repository.

## Core Rules

- Do not hardcode project names, service names, host names, workflow names, backup filenames, paths, ports, or rollback commands. Read them from the repository's deployment documentation and current deploy files. The canonical deployment document is `docs/deployment.md`; if it is missing or clearly stale, stop before deploying and create or repair it first using `references/deployment-doc-template.md`.
- After fetching, the remote-tracking release branch is the published baseline. A newer local release branch is only a release candidate; being newer, or passing tests, never makes it deployable by itself.
- Release scope is defined by pre-existing approval evidence only: the current release request, an approved review, a release plan, or an explicitly named release batch. Approval evidence is never created or expanded during the release audit. Every commit in `<remote>/<release-branch>..candidate` must belong to that scope.
- Choose the development baseline by change relationship: an independent feature starts from the current remote-tracking release branch; a feature with an unmerged prerequisite starts from that explicit prerequisite branch; features approved to ship together use a named integration or release branch.
- If the audited range contains unapproved or unrelated commits, or the worktree is dirty, stop and follow `references/release-audit.md` before any push.

## Workflow

### 1. Build Release Context

- Read `README.md` and `docs/deployment.md`, then every deployment-critical file it lists, such as CI/CD workflows, deploy scripts, compose or platform config, migration scripts, rollback tools, or release notes. If the documented process contradicts the current files, stop and resolve the mismatch before production deployment.
- Fetch the release remote with pruning. Record the remote baseline SHA, candidate SHA, current branch, all linked worktrees, worktree status, and ahead/behind relationship.
- Audit the exact `<remote>/<release-branch>..candidate` log and diff. Confirm the candidate's development baseline and the pre-existing approval source for every included feature or release batch. Uncommitted files are not part of the range: preserve them, but never count them as released.
- Identify whether the diff affects high-risk areas: auth, payment, billing, permissions, database, migrations, data deletion, routing removals, deploy scripts, rollback scripts, infrastructure, or public API contracts.
- On any scope violation or dirty worktree, switch to `references/release-audit.md`.

### 2. Make the Pre-Deploy Judgment Explicit

Before pushing or triggering a production deployment, explain:

- what online behavior may change
- what high-risk areas are touched
- what local checks were run or skipped
- why backup and rollback safeguards are expected to work
- the fastest safe recovery path declared by the project

Ask for confirmation before push or production deployment unless the user has already explicitly delegated that action for this release.

### 3. Verify Locally

- Run the checks declared by `docs/deployment.md`; use broader validation for broad, risky, or cross-cutting changes.
- If a check cannot run, state the exact blocker and residual risk before proceeding.
- If deployment files changed, validate the deployment configuration using the project-declared command.

### 4. Push and Locate Deployment

- Fetch the release remote again immediately before push. If the baseline moved, update the candidate, reconfirm the audited commit range and clean worktree state, and rerun every affected check.
- Push only the audited candidate SHA to the documented release branch, or trigger only the documented release action.
- Locate the CI/CD run, platform deploy, or custom deploy session declared by `docs/deployment.md` and watch it; never treat a successful push as a successful release.

### 5. Monitor Rollout

Monitor CI/CD and the runtime environment together, using the commands and success signals declared in `docs/deployment.md`, to verify:

- the target environment is running the expected commit or version
- required pre-deploy backups exist and pass the documented sanity check
- rollback metadata, rollback artifact, or previous-version reference is available
- services, containers, processes, or platform instances are healthy
- critical logs do not show boot, migration, auth, permission, network, or resource failures
- host or platform resources are within the documented safe range
- external health endpoints, important user flows, or admin checks pass when documented

### 6. Handle Failures Deliberately

- If deployment fails before affecting live service, stop, collect the failing step, logs, runtime state, and next repair recommendation.
- If the new version is live and user-visible service is degraded, prioritize the fastest recovery path declared by `docs/deployment.md`.
- Do not perform database restore, destructive migration rollback, data deletion, environment rebuild, credential rotation, or other irreversible actions without fresh explicit confirmation.
- After any rollback or recovery action, verify the service is healthy again and record the restored version or artifact.

### 7. Report Outcome

Write the release report from `references/report-template.md`. Do not declare a release complete from CI/CD success alone; completion requires runtime, backup, rollback, and health evidence.

### 8. Reconcile Git State

- Fetch the release remote and verify its release branch points to the deployed candidate.
- Synchronize the local release branch only when the update is clean and fast-forward safe. Preserve unrelated local changes; never reset or overwrite them as cleanup.
- Remove only feature/release worktrees that are clean and whose commits are merged or otherwise preserved on an explicit branch; delete only merged branches that are no longer needed, then prune stale worktree metadata.
- Keep active prerequisite, integration, or unreleased branches. Report anything intentionally retained.

### 9. Update Deployment Documentation

After the service is stable, update `docs/deployment.md` when the actual release process differed from the document. Record process, commands, checks, and success criteria only. Do not write secrets, tokens, passwords, private keys, or sensitive customer data.

## Reference Use

- `references/release-audit.md`: handling scope violations, inherited commits, or dirty worktrees found during the audit.
- `references/deployment-doc-template.md`: creating or repairing `docs/deployment.md`.
- `references/report-template.md`: preparing the final release report.
- For project-specific commands, prefer `docs/deployment.md` over memory or assumptions.
