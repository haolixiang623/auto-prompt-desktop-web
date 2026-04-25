# Auto-Prompt 开发环境部署规范（后续统一执行）

本文档固化当前项目已验证的部署方式，作为后续在开发环境发布 `auto-prompt` 的统一要求。  
目标：**只更新本应用，不影响其他业务系统；保留 SQLite 与用户数据；可回滚；可审计。**

---

## 1. 适用范围

- 目标主机：`192.168.204.126`
- 应用目录：`/opt/auto-prompt`
- 数据目录：`/opt/auto-prompt/data`（必须持久化保留）
- 对外端口：`8089`
- 部署形态：Docker Compose（开发环境专用 `docker-compose.dev.yml`）

---

## 2. 强制约束（必须遵守）

- 仅允许操作 `auto-prompt` 相关容器与文件。
- 禁止变更、重启、停止其他业务服务。
- 任何发布前必须可回滚（镜像可恢复、数据有备份）。
- 数据目录必须使用宿主机绑定挂载，不得切换为临时卷。
- 发布后必须做健康检查与日志检查，确认无启动错误。

---

## 3. 标准部署方式（唯一推荐）

### 3.1 本地构建镜像（`linux/amd64`）

```bash
docker buildx build --platform linux/amd64 -t auto-prompt-app:dev --load .
```

说明：
- 必须指定 `linux/amd64`，避免开发机出现 `exec format error`。

### 3.2 导出并传输镜像

```bash
docker save auto-prompt-app:dev -o /tmp/auto-prompt-app-dev.tar
gzip -f /tmp/auto-prompt-app-dev.tar
scp /tmp/auto-prompt-app-dev.tar.gz root@192.168.204.126:/opt/auto-prompt/
```

### 3.3 开发机加载镜像并仅更新 app

```bash
ssh root@192.168.204.126
docker load -i /opt/auto-prompt/auto-prompt-app-dev.tar.gz
cd /opt/auto-prompt
docker-compose -f docker-compose.dev.yml up -d --no-build app
docker-compose -f docker-compose.dev.yml ps
```

说明：
- 必须使用 `up -d --no-build app`，只更新 `app` 服务。
- 不执行全量 `up`，避免误触其他服务。

---

## 4. Compose 基线要求（开发环境）

`docker-compose.dev.yml` 需满足以下要求：

- `app.image = auto-prompt-app:dev`
- `network_mode: "host"`（解决容器内 DNS/外网解析问题）
- 数据挂载：`/opt/auto-prompt/data:/data`
- 日志挂载：`./logs:/app/logs`
- 端口/命令统一监听 `8089`

必须保证应用环境变量包含：

- `AUTO_PROMPT_DATA_DIR=/data`
- `AUTO_PROMPT_REPO_ROOT=/app`
- `AUTO_PROMPT_SKILLS_DIR=/app/skills`
- `AUTO_PROMPT_WEB_DIST=/app/dist`
- `PORT=8089`

---

## 5. 发布前检查清单

- [ ] 确认本次仅涉及 `auto-prompt` 需求。
- [ ] 确认代码变更已在本地通过基础验证。
- [ ] 确认目标主机 `/opt/auto-prompt/data` 存在且可读写。
- [ ] 确认 `docker-compose.dev.yml` 未引入其他服务变更。
- [ ] 如涉及高风险变更，先执行数据备份：
  ```bash
  tar czvf /root/auto-prompt-data-backup-$(date +%F-%H%M%S).tgz -C /opt/auto-prompt data
  ```

---

## 6. 发布后验收（必须完成）

### 6.1 健康检查

```bash
curl -sS http://127.0.0.1:8089/api/health
```

预期：返回 `status=healthy`。

### 6.2 容器日志检查

```bash
cd /opt/auto-prompt
docker-compose -f docker-compose.dev.yml logs --tail=100 app
```

预期：
- `Application startup complete`
- 无持续异常栈（尤其是网络解析、模型调用初始化、文件权限错误）

### 6.3 功能冒烟

- 登录可用
- 目录上传可用
- 分类/生成流程可进入并返回明确结果（成功或可解释错误）

---

## 7. 回滚规范

若发布后异常，按以下顺序回滚：

1. 回滚镜像（加载上一个稳定镜像包）。
2. 仅重启 `app` 服务：
   ```bash
   cd /opt/auto-prompt
   docker-compose -f docker-compose.dev.yml up -d --no-build app
   ```
3. 若数据异常，停服务后用备份包恢复 `data/`。

---

## 8. 常见问题与处理（经验固化）

- `exec format error`
  - 原因：镜像架构不匹配。
  - 处理：重新按 `--platform linux/amd64` 构建。

- 容器内调用外部 LLM 失败（DNS 解析异常）
  - 处理：开发环境使用 `network_mode: "host"`。

- 分类报“待分类材料目录不存在”
  - 当前兼容目录名：`待分类材料` 与 `待分类`。
  - 发布后若仍报错，优先检查工作区目录结构与上传内容。

- 上传失败但后端无请求日志
  - 常见为前端网络层/XHR 问题，先看浏览器端错误与重试逻辑。

---

## 9. 变更记录要求

每次发布后，至少记录以下信息（可写入发布日志或工单）：

- 发布时间、执行人
- 镜像标签与镜像 ID
- 部署命令（含 compose 文件）
- 健康检查结果
- 是否影响用户操作
- 回滚信息（如有）

---

## 10. 禁止项

- 禁止使用会影响其他业务的命令（如全局重启 Docker、批量清理容器）。
- 禁止在未确认情况下执行破坏性操作（如删除 `data`、`docker system prune -a`）。
- 禁止绕过验收直接宣告部署完成。

