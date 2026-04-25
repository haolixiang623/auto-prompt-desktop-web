# 开发环境（192.168.204.126）Docker 化迁移部署计划

> **For agentic workers:** 实施时用 checkbox 跟踪；变更开发机前需人工确认窗口，并先完成冷备份。

**Goal:** 在保留现有 SQLite（`app.db`）与 `AUTO_PROMPT_DATA_DIR` 下用户目录数据的前提下，将当前「systemd + 本机 venv + 直连 8089」部署切换为仓库内 `Dockerfile` + `docker-compose.prod.yml` 方案。

**Architecture:** 后端与前端由同一镜像构建（前端 `npm run build` 进镜像，`uvicorn` 提供 API 与静态资源）；`nginx` 容器仅作反向代理。持久化数据通过 **宿主机目录绑定到容器内 `/data`**，与镜像内 `AUTO_PROMPT_DATA_DIR=/data` 对齐。

**Tech Stack:** Docker / Compose、Python 3.11 + FastAPI/Uvicorn、Node 20 构建前端、SQLite 单文件 `app.db`、Nginx Alpine。

---

## 1. 现状评估（只读巡检结论，2026-04-21）

### 1.1 运行方式

| 项目 | 现状 |
|------|------|
| 进程管理 | `systemd` 单元 `auto-prompt.service`，**enabled + running** |
| 工作目录 | `/opt/auto-prompt` |
| 启动命令 | `/opt/auto-prompt/venv/bin/python -m uvicorn pyserver.app.main:app --host 0.0.0.0 --port 8089` |
| 数据目录 | `Environment=AUTO_PROMPT_DATA_DIR=/opt/auto-prompt/data` |

### 1.2 数据落盘（需完整保留）

代码侧（`pyserver/app/core/paths.py`）在 `AUTO_PROMPT_DATA_DIR` 下使用：

- `app.db`：业务数据与认证（`DataStore` + `AuthStore` 共用同一路径，见 `main.py` lifespan）
- `settings.json`
- `workspaces/`、`uploads/`、`tasks/`、`outputs/` 等

**开发机实测路径与体量（约）：**

- `/opt/auto-prompt/data/app.db` ~104K  
- `/opt/auto-prompt/data/settings.json` ~4K  
- `/opt/auto-prompt/data/workspaces/` ~103M（主要体积）  
- `uploads/`、`outputs/` 等为 KB～百 KB 级  

### 1.3 仓库内 Docker 方案与差异

- `Dockerfile`：`AUTO_PROMPT_DATA_DIR=/data`，应用监听 **`PORT` 默认 3000**（镜像内 `ENV PORT=3000`）。
- `docker-compose.prod.yml`：`app` 仅 `expose: 3000`；`nginx` 映射 **`8089:80`**，与当前开发环境对外端口 **8089** 习惯一致。
- `nginx.conf` 中 `proxy_pass http://app:3000`，与 Compose 服务名一致。

**与现状的关键对齐点：**

- 将宿主机 **`/opt/auto-prompt/data` 绑定为容器 `/data`** 即可保留全部 SQLite 与文件型用户数据，无需改应用逻辑。
- 切换前必须 **停止并禁用** `auto-prompt.service`，否则 **8089 端口与数据文件会被占用/并发写入**。

### 1.4 代码版本与数据库迁移

- 新版本 `DataStore` 启动时会执行 `_migrate_legacy`、`_migrate_v3` 等（见 `pyserver/app/core/data.py`），旧库一般可在首次启动时自动升级。
- **风险：** 若新代码与极旧 schema 不兼容，需在**副本**上先启动验证；通过后再切换生产数据路径。

---

## 2. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 双实例同时写 `app.db` | 切换窗口内只保留一种运行方式；先停 systemd 再启 Compose |
| 绑定挂载权限 | 镜像默认 root 运行；若将来改为非 root UID，需 `chown` 数据目录 |
| API Key / 环境变量丢失 | 使用宿主机 `.env` 或 systemd drop-in 等价物传入 Compose `environment` |
| 回滚困难 | 迁移前完整 `tar` 备份 `data`；保留旧 `venv` 与 unit 文件至验证通过 |
| 宿主机已运行 Docker | 本机已有 `docker.service`；仅新增本应用 stack，注意 **8089** 不与旧进程冲突 |

---

## 3. 前置条件（执行前检查清单）

- [ ] 确认维护窗口，通知依赖 8089 的客户端。
- [ ] 在开发机具备项目**新版本**源码（或 CI 构建产物策略）：`/opt/auto-prompt` 建议改为 git 克隆目录或发布包解压目录，便于 `docker compose build`。
- [ ] 准备 `DASHSCOPE_API_KEY`、`OPENAI_API_KEY` 等与当前非 Docker 部署一致的密钥（按需）。
- [ ] **冷备份**（示例，路径可调）：  
  `tar czvf /root/auto-prompt-data-backup-$(date +%F).tgz -C /opt/auto-prompt data`

---

## 4. 推荐 Compose 数据卷策略（保留数据）

**推荐：** 不用匿名命名卷 `app-data:`，改为 **bind mount**，例如：

```yaml
volumes:
  - /opt/auto-prompt/data:/data
```

并保留或调整 `./logs` 映射，避免日志写满容器层。

实施时在仓库中**新增或覆盖**一份面向开发机的 `docker-compose` 变体（例如 `docker-compose.dev-126.yml`）仅改 `volumes` 与 `env_file`，**不修改业务代码**。

---

## 5. 迁移步骤（有序执行）

### Task A：准备与备份

- [ ] **Step 1:** SSH 登录开发机，确认 `auto-prompt.service` 仍为唯一占用 8089 的后端（`ss -lntp | grep 8089`）。
- [ ] **Step 2:** 执行 `data` 目录完整备份（见 §3）。
- [ ] **Step 3:** 将目标版本代码同步到 `/opt/auto-prompt`（或并列目录如 `/opt/auto-prompt-docker`，避免覆盖时误删 `data`）。

### Task B：镜像与配置

- [ ] **Step 4:** 在代码目录创建/确认 `.env`（Compose 读取 `DASHSCOPE_API_KEY` 等）。
- [ ] **Step 5:** 使用 bind mount 的 compose 文件：`docker compose -f docker-compose.dev-126.yml build`。
- [ ] **Step 6:** **干跑**（可选）：用备份复制到临时目录，挂载到测试 compose 项目，验证 `/api/health` 与登录。

### Task B：切换流量

- [ ] **Step 7:** `systemctl stop auto-prompt.service` && `systemctl disable auto-prompt.service`（防止重启机器后旧服务抢占）。
- [ ] **Step 8:** `docker compose -f docker-compose.dev-126.yml up -d`。
- [ ] **Step 9:** 验证：`curl -sS http://127.0.0.1:8089/api/health`；浏览器访问历史 URL；抽查用户登录与关键业务只读接口。

### Task D：收尾

- [ ] **Step 10:** 配置开机自启：`docker compose` 服务 `restart: always` 已具备；确认 Docker 服务本机已 enable。
- [ ] **Step 11:** 文档化：记录实际 compose 文件名、数据路径、备份位置与回滚命令。

---

## 6. 回滚步骤

1. `docker compose -f <file> down`（停止容器）。
2. `systemctl enable --now auto-prompt.service`（若 unit 未删除）。
3. 若数据已损坏：从 §3 的 `tgz` 解压恢复 `data`（在停服务状态下操作）。

---

## 7. 验收标准

- [ ] `8089` 仅由本应用 Docker stack 占用。
- [ ] 原用户可登录，历史 workspace / 上传与输出文件可访问。
- [ ] `app.db` 与 `settings.json` 仍在 `/opt/auto-prompt/data` 且时间戳随操作更新合理。
- [ ] 健康检查通过（Compose `healthcheck` 与手工 `curl` 一致）。

---

## 8. 后续可选优化（非必须）

- 将 `nginx` 的 `server_name` 从硬编码 IP 改为可配置，与 `engine.bridge.ts`「少硬编码、多环境变量」原则一致（独立变更）。
- 数据目录定期快照与监控磁盘（`workspaces` 已占 ~100M+）。
