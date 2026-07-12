# Deployment Document Template

Use this template for a repository's `docs/deployment.md`. Replace placeholders with project-specific facts from the repository and deployment environment. Do not include secrets, tokens, private keys, passwords, or sensitive customer data.

## Release Target

- Release remote:
- Release branch:
- Canonical published baseline:
- Integration or release-candidate branch, if any:
- Release environments:
- Production URL or health endpoint:
- Staging URL or health endpoint:
- Owner or escalation contact:

## Trigger

- Deployment trigger:
- CI/CD workflow, platform, or command:
- Manual inputs, if any:
- Expected deployment duration:
- Concurrency or deploy-lock behavior:

## Runtime Architecture

- Runtime units:
- Reverse proxy or edge layer:
- Databases and persistent stores:
- Caches, queues, workers, scheduled jobs, or background processors:
- Important ports, domains, or internal endpoints:
- Runtime config files:

## Pre-Deploy Checks

Run these before push or deployment:

```bash
# Add project-specific checks here.
```

If any check is intentionally skipped, record the reason and risk.

Also document how to fetch the release remote and audit the exact remote-baseline-to-candidate commit range before push.

## Deployment-Critical Files

Read these before each deployment:

- `README.md`
- `docs/deployment.md`
- Add CI/CD workflows, deploy scripts, compose files, platform config, migration scripts, rollback tools, and release notes here.

## Backup Requirements

- Backup trigger:
- Backup artifact or metadata:
- Backup location:
- Sanity check:
- Retention policy:
- What failure means:

Deployment must stop if required backup creation or validation fails.

## Rollback and Recovery

- Fastest service recovery path:
- Previous-version or artifact rollback path:
- Database restore path:
- Migration rollback path:
- Actions requiring explicit confirmation:
- Verification after recovery:

Prefer service restoration first. Use database restore only when persisted data or schema state requires it.

## Monitoring During Deployment

- CI/CD status command or dashboard:
- Runtime version check:
- Health check:
- Log checks:
- Resource checks:
- Business or admin checks:

## Success Criteria

A deployment is complete only when all required criteria are true:

- Target environment runs the expected commit, version, or artifact.
- The released commit range contains only the approved scope and explicit dependencies.
- CI/CD or deployment session completed successfully.
- Required backup exists and passes sanity checks.
- Rollback metadata or previous-version reference is ready.
- Runtime health checks pass.
- Critical logs and resources are clean enough for the release risk.
- Required business or admin checks pass.

## Failure Handling

- Failure before live impact:
- Failure after live impact:
- When to stop and ask:
- When to recover immediately:
- Evidence to collect:

## Post-Deploy Documentation

If the real process differs from this document, update this file after the service is stable.

## Git Reconciliation

- Local release branch synchronization policy:
- Feature/release worktree cleanup policy:
- Branch retention and deletion policy:
