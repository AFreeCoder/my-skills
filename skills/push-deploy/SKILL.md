---
name: push-deploy
description: Use when releasing code to production or staging, auditing unpublished or mixed-scope branch/worktree history, pushing deployment commits, monitoring CI/CD, verifying backups and rollback readiness, handling deployment failures, or restoring live service during a release.
---

# Push Deploy

## Overview

Use this skill when code is ready to release and the user wants the agent to push, trigger deployment, monitor rollout, and verify recovery safeguards. The skill defines release discipline only; project-specific facts must come from the target repository.

## Core Rule

Do not hardcode project names, service names, host names, workflow names, backup filenames, paths, ports, or rollback commands. Read them from the repository's deployment documentation and current deploy files.

The canonical project deployment document is `docs/deployment.md`. If it is missing or clearly stale, stop before deploying and create or update it first. Use `references/deployment-doc-template.md` as the template.

After fetching, the remote-tracking release branch is the published baseline. A newer local release branch is only a release candidate; it must never be treated as an implicit integration branch or proof of deployed state.

## Release Lineage Rules

| Change relationship | Required development baseline |
|---|---|
| Independent feature | Current remote-tracking release branch |
| Feature with an unmerged prerequisite | The explicit prerequisite feature branch |
| Features approved for one release batch | A named integration or release branch |

If a candidate inherited unpublished commits from a local release branch, every inherited commit is part of the release candidate. The full range is valid only when those commits were explicitly approved before the release audit as one named release batch. Otherwise, rebuild a clean candidate from the remote release baseline with only the previously approved changes. Never hide inherited commits behind the newest feature name or grant retroactive batch approval during the audit.

## Release Red Flags

| Rationalization | Required response |
|---|---|
| "Local main is newer" | Treat it only as a candidate; audit from the fetched remote release baseline. |
| "Those inherited commits will ship soon anyway" | They remain out of scope unless already approved in a named release batch. |
| "All tests pass, so approve the mixed range now" | Tests do not define release authorization; rebuild a clean candidate. |
| "The dirty files will not be staged" | Use a clean release worktree so the release evidence is isolated and auditable. |

## Workflow

### 1. Build Release Context

- Confirm the release remote and target release branch from `docs/deployment.md`, then fetch that remote with pruning.
- Record the remote baseline SHA, candidate SHA, current branch, all linked worktrees, worktree status, and ahead/behind relationship.
- Audit the exact `<remote>/<release-branch>..candidate` log and diff. Prove that every commit and file in the range belongs to the approved release scope.
- Confirm whether the candidate came from the remote release baseline, an explicit prerequisite feature branch, or a named integration/release branch.
- Identify whether the diff affects high-risk areas: auth, payment, billing, permissions, database, migrations, data deletion, routing removals, deploy scripts, rollback scripts, infrastructure, or public API contracts.
- Record the pre-existing approval source for each included feature or release batch, such as the current release request, approved review, or release plan. Do not create approval evidence during the audit.
- If the audit finds any unapproved or unrelated commit, stop. In a clean release worktree created from the fetched remote release baseline, rebuild the candidate with only changes that have pre-existing approval evidence and rerun every required check there. Do not push the local release branch as-is or retroactively expand the release batch.
- If the current worktree is dirty even though the history scope is approved, perform release verification in the same kind of clean release worktree.
- Uncommitted files are not part of a commit range. Preserve them, but never count them as released or let them enter the release candidate.

### 2. Read Deployment Facts

- Read `README.md`.
- Read `docs/deployment.md`.
- Read every deployment-critical file listed by `docs/deployment.md`, such as CI/CD workflows, deploy scripts, compose or platform config, migration scripts, rollback tools, or release notes.
- If the documented process contradicts the current files, stop and resolve the documentation mismatch before production deployment.

### 3. Make the Pre-Deploy Judgment Explicit

Before pushing or triggering a production deployment, explain in Chinese:

- what online behavior may change
- what high-risk areas are touched
- what local checks were run or skipped
- why backup and rollback safeguards are expected to work
- the fastest safe recovery path declared by the project

Ask for confirmation before push or production deployment unless the user has already explicitly delegated that action for this release.

### 4. Verify Locally

- Run the checks declared by `docs/deployment.md`.
- Use broader validation for broad, risky, or cross-cutting changes.
- If a check cannot run, state the exact blocker and residual risk before proceeding.
- If deployment files changed, validate the deployment configuration using the project-declared command.

### 5. Push and Locate Deployment

- Fetch the release remote again immediately before push. If the remote release baseline moved, update the candidate and rerun every affected check.
- Reconfirm the exact remote-baseline-to-candidate commit list, diff, clean worktree state, and approval boundary.
- Push only the candidate SHA to the documented release branch or trigger only the documented release action. Do not push a local release branch merely because it is newer.
- Locate the CI/CD run, platform deploy, or custom deploy session declared by `docs/deployment.md`.
- Watch the deployment; never treat a successful push as a successful release.

### 6. Monitor Rollout

Monitor CI/CD and the runtime environment together. Use the commands and success signals declared in `docs/deployment.md` to verify:

- the target environment is running the expected commit or version
- required pre-deploy backups exist and pass the documented sanity check
- rollback metadata, rollback artifact, or previous-version reference is available
- services, containers, processes, or platform instances are healthy
- critical logs do not show boot, migration, auth, permission, network, or resource failures
- host or platform resources are within the documented safe range
- external health endpoints, important user flows, or admin checks pass when documented

### 7. Handle Failures Deliberately

- If deployment fails before affecting live service, stop, collect the failing step, logs, runtime state, and next repair recommendation.
- If the new version is live and user-visible service is degraded, prioritize the fastest recovery path declared by `docs/deployment.md`.
- Do not perform database restore, destructive migration rollback, data deletion, environment rebuild, credential rotation, or other irreversible actions without fresh explicit confirmation.
- After any rollback or recovery action, verify the service is healthy again and record the restored version or artifact.

### 8. Report Outcome

Use `references/report-template.md`. The final report must include concrete current-release facts:

- fetched remote baseline, candidate SHA, and released commit range
- included feature scope and any explicit prerequisite or release-batch relationship
- commit, version, or release identifier
- CI/CD run or deploy session and result
- live runtime version
- health check result
- backup verification result
- rollback readiness or recovery action
- business impact judgment
- remaining risks or watchpoints

Do not say a release is complete from CI/CD success alone. Completion requires runtime, backup, rollback, and health evidence.

### 9. Reconcile Git State

- Fetch the release remote and verify its release branch points to the deployed candidate.
- Synchronize the local release branch only when the update is clean and fast-forward safe. Preserve unrelated local changes; never reset or overwrite them as cleanup.
- Remove only feature/release worktrees that are clean and whose commits are merged or otherwise preserved on an explicit branch.
- Delete only merged branches that are no longer needed, then prune stale worktree metadata.
- Keep active prerequisite, integration, or unreleased branches. Report anything intentionally retained.

### 10. Update Deployment Documentation

After the service is stable, update `docs/deployment.md` when the actual release process differed from the document. Record process, commands, checks, and success criteria only. Do not write secrets, tokens, passwords, private keys, or sensitive customer data.

## Reference Use

- Read `references/deployment-doc-template.md` when creating or repairing `docs/deployment.md`.
- Read `references/report-template.md` when preparing the final release report.
- For project-specific commands, prefer `docs/deployment.md` over memory or assumptions.
