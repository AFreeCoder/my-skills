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

## Rollback and Recovery

- Fastest service recovery path:
- Previous-version or artifact rollback path:
- Database restore path:
- Migration rollback path:
- Actions requiring explicit confirmation:
- Verification after recovery:

## Monitoring During Deployment

- CI/CD status command or dashboard:
- Runtime version check:
- Health check:
- Log checks:
- Resource checks:
- Business or admin checks:

## Success Criteria

Project-specific criteria that must all be true for a deployment to count as complete:

- Expected commit, version, or artifact signal:
- Required backup and rollback readiness signals:
- Required health, log, and resource checks:
- Required business or admin checks:

## Failure Handling

- Failure before live impact:
- Failure after live impact:
- When to stop and ask:
- When to recover immediately:
- Evidence to collect:

## Git Reconciliation

- Local release branch synchronization policy:
- Feature/release worktree cleanup policy:
- Branch retention and deletion policy:
