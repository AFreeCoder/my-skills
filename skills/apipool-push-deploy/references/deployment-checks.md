# Deployment Checks

## Files to inspect before push

- `.github/workflows/deploy.yml`
- `deploy/rollback.sh`
- `deploy/docker-compose.deploy.yml`
- `deploy/version_resolver.sh`
- `README.md` deployment and rollback section

Read these files every time the current diff touches deployment, rollback, compose, or version logic.

## Release review checklist

- Confirm what the release changes for real users.
- State whether any removed feature, route, or UI entry will now fail or 404.
- State whether billing, quota, auth, OAuth, account scheduling, or model routing behavior changed.
- State whether the live version shown by `backend/cmd/server/VERSION` is expected to change.
- Confirm that the auto-deploy workflow still:
  - creates a `pre-deploy-*.sql.gz` backup before switching code
  - tags the current `deploy-sub2api:latest` image as `rollback-latest`
  - records rollback metadata in `/opt/sub2api/backups/last-rollback-image.txt`
  - waits for `sub2api-postgres`, `sub2api-redis`, and `sub2api` to become healthy

## Local commands

```bash
git status -sb
git branch --show-current
git remote -v
git log --oneline --decorate -n 5
```

Run the relevant validation for the current diff. For upstream sync or larger merges, prefer the broader baseline:

```bash
cd backend && go test ./...
cd backend && golangci-lint run ./...
pnpm --dir frontend run lint:check
pnpm --dir frontend run typecheck
make build
docker compose -f deploy/docker-compose.deploy.yml config -q
```

If `make test-integration` cannot run because Docker is unavailable locally, say so explicitly before pushing.

## Push and locate the workflow

```bash
git push origin main
gh run list -R AFreeCoder/apipool --workflow 'Deploy to DigitalOcean' --limit 3
gh run watch -R AFreeCoder/apipool <run-id> --exit-status
gh run view -R AFreeCoder/apipool <run-id> --json status,conclusion,displayTitle,headSha,jobs
```

Use the workflow name exactly as written above.

## Server monitoring commands

The production host is normally reached with the `digitalocean` SSH alias.

### Quick baseline

```bash
ssh -o BatchMode=yes digitalocean 'hostname && uptime && docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}\t{{.Image}}"'
```

### Repo, version, and backups

```bash
ssh digitalocean 'cd /opt/sub2api && git rev-parse --short=12 HEAD && cat backend/cmd/server/VERSION'
ssh digitalocean 'ls -lt /opt/sub2api/backups | head -6'
ssh digitalocean 'cat /opt/sub2api/backups/last-rollback-image.txt'
```

### Build progress

```bash
ssh digitalocean 'ps -eo pid,etimes,cmd | egrep "docker compose -f docker-compose.deploy.yml build|docker-buildx|buildkitd" | grep -v egrep || true'
```

### Container and image state

```bash
ssh digitalocean 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}\t{{.Image}}" | grep -E "^NAMES|^sub2api|^sub2api-postgres|^sub2api-redis"'
ssh digitalocean 'docker inspect --format "container={{.Id}} image={{.Image}} created={{.Created}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" sub2api'
ssh digitalocean 'docker image inspect deploy-sub2api:latest --format "latest={{.Id}} created={{.Created}}"'
ssh digitalocean 'docker image inspect deploy-sub2api:rollback-latest --format "rollback_latest={{.Id}} created={{.Created}}"'
ssh digitalocean 'docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedSince}}" | grep "^deploy-sub2api" | head -8'
```

### Runtime logs

```bash
ssh digitalocean 'docker logs --since 2m sub2api 2>&1 | tail -120'
```

## Success signals

- The GitHub Actions run finishes with `conclusion=success`.
- The server repo `HEAD` matches the pushed commit.
- `backend/cmd/server/VERSION` on the server matches the expected runtime version.
- A fresh `pre-deploy-*.sql.gz` exists for the current deploy window.
- `/opt/sub2api/backups/last-rollback-image.txt` points to the previous live commit or image.
- `deploy-sub2api:latest` points to a new image id after the build completes.
- `sub2api` has a recent creation time and reaches `healthy`.

## Safe intermediate state

This deployment is not zero-downtime. A short restart window is normal.

During the build phase, this is still an acceptable state:

- the old `sub2api` container remains healthy
- the server repo has already advanced
- build processes are still running
- the new image id has not appeared yet

Keep watching until the new container is recreated and healthy.

## Failure cues

- No fresh `pre-deploy-*.sql.gz` appears.
- `last-rollback-image.txt` is missing or stale.
- `deploy-sub2api:rollback-latest` does not exist.
- The workflow reports success but the server still runs the old container and old image long after build activity stops.
- `sub2api` becomes `unhealthy`, `exited`, or logs show a boot failure.

Also watch for stale renamed containers matching `^[0-9a-f]+_sub2api`, which usually means a previous recreate failed mid-flight.

## Rollback commands

Fast image rollback:

```bash
ssh digitalocean 'cd /opt/sub2api/deploy && ./rollback.sh image'
```

Database restore plus rollback image:

```bash
ssh digitalocean 'cd /opt/sub2api/deploy && ./rollback.sh db-restore --with-image'
```

Use image rollback first unless the incident clearly requires restoring persisted data too.
