# Deployment Cleanup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove deprecated deployment paths and leave one supported production Docker deployment workflow.

**Architecture:** Keep the production deployment stack unchanged: Docker image build from `Dockerfile`, reverse proxy via the nginx service in `docker-compose.prod.yml`, and external access on port `8089`. Cleanup is limited to repository structure, scripts, and documentation.

**Tech Stack:** Bash, Docker Compose, Node.js tests, Markdown documentation

---

### Task 1: Add Deployment Structure Guardrail

**Files:**
- Create: `tests/deployment-structure.test.mjs`
- Test: `tests/deployment-structure.test.mjs`

- [ ] **Step 1: Write the failing test**

Create a repository-level test that asserts:
- only the approved deployment assets exist
- deprecated deployment files do not exist
- `package.json` Docker scripts reference `docker-compose.prod.yml`

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/deployment-structure.test.mjs`
Expected: FAIL because deprecated files still exist and Docker scripts still point at `docker-compose.python.yml`

- [ ] **Step 3: Write minimal implementation**

Delete deprecated deployment assets and update the active script references.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/deployment-structure.test.mjs`
Expected: PASS

### Task 2: Update Active Deployment Entry Points

**Files:**
- Modify: `package.json`
- Modify: `README.md`
- Modify: `DEPLOYMENT-GUIDE.md`
- Modify: `test-deploy.sh`
- Modify: `deploy-production.sh`

- [ ] **Step 1: Update npm Docker scripts**

Point `docker:up` and `docker:down` at `docker-compose.prod.yml`.

- [ ] **Step 2: Rewrite docs for a single path**

Remove references to deprecated deployment flows and document only the supported production Docker path.

- [ ] **Step 3: Keep deployment behavior stable**

Do not change ports, reverse-proxy topology, or remote runtime assumptions.

- [ ] **Step 4: Verify all active references**

Run: `rg -n "docker-compose\\.simple|docker-compose\\.python|Dockerfile\\.baidubce|deploy-simple|deploy-cloud|deploy-server|deploy-native|deploy-baidu|switch-backend|DEPLOY-CLOUD" .`
Expected: no active references outside historical plan docs or deleted files

### Task 3: Verify End State

**Files:**
- Test: `tests/deployment-structure.test.mjs`

- [ ] **Step 1: Check kept shell scripts**

Run: `bash -n deploy-production.sh test-deploy.sh`
Expected: no output, zero exit status

- [ ] **Step 2: Run the focused test**

Run: `node --test tests/deployment-structure.test.mjs`
Expected: PASS

- [ ] **Step 3: Run the app build**

Run: `npm run build`
Expected: PASS

- [ ] **Step 4: Validate compose file**

Run: `docker compose -f docker-compose.prod.yml config`
Expected: PASS when Docker is available locally
