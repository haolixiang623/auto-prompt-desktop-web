# Deployment Cleanup Design

**Date:** 2026-04-21

## Goal

Reduce the repository to a single supported deployment path for production:
Docker build via `Dockerfile` and runtime orchestration via `docker-compose.prod.yml`.

## Current Problem

The repository contains multiple deployment scripts, compose files, and Dockerfiles for old or alternate flows. These files create conflicting instructions, stale references, and an increased risk of using the wrong deployment path.

## Approved Direction

Keep one production Docker path only.

### Keep

- `Dockerfile`
- `docker-compose.prod.yml`
- `nginx.conf`
- `deploy-production.sh`
- `DEPLOYMENT-GUIDE.md`
- `test-deploy.sh`

### Delete

- `deploy-simple.sh`
- `deploy-cloud.sh`
- `deploy-server.sh`
- `deploy-native.sh`
- `deploy-baidu.sh`
- `deploy-baidu-source.sh`
- `switch-backend.sh`
- `docker-compose.simple.yml`
- `docker-compose.python.yml`
- `Dockerfile.baidubce`
- `DEPLOY-CLOUD.md`

## Required Follow-Up Changes

- Update `package.json` Docker scripts to reference `docker-compose.prod.yml`.
- Update `README.md` so Docker instructions describe only the production Docker path.
- Update `DEPLOYMENT-GUIDE.md` to be the single authoritative deployment document.
- Keep the existing runtime model unchanged:
  - access via `http://<host>:8089/`
  - Dockerized nginx in front of the app container
  - no host nginx involvement for this application

## Validation

- Add a test that asserts the repository exposes only the approved deployment assets and references.
- Run the new test and watch it fail before implementation.
- Run targeted verification after cleanup:
  - deployment structure test
  - shell syntax check for kept scripts
  - `npm run build`
  - `docker compose -f docker-compose.prod.yml config` when Docker is available
