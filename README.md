# Auto-Prompt Web 管理台

Auto-Prompt Web 管理台是对原 `Tauri + Vue` 桌面应用的 Web 化改造版本。当前版本保留原有 `Vue 3 + Vite + Router` 前端交互，并新增 Rust HTTP 服务，统一负责文件上传、工作区管理、后台任务轮询、设置持久化、案例库与审查规则库存储，以及 Python skills 的调用编排。

首版覆盖四条核心链路：

- 提示词生成
- 材料分类
- 要素 JSON 生成
- 审查规则生成

## 架构说明

```text
浏览器
  └─ Vue 3 Web 管理台
       └─ /api/* 调用
            └─ Rust Web Server (Axum)
                 ├─ 工作区 / 上传 / 任务 / 日志 / 设置
                 ├─ 案例库 / 审查规则库持久化
                 └─ Python skills runner
                      ├─ skills/doc-extract-prompt-gen
                      ├─ skills/material-classifier
                      ├─ skills/factor-json-generator
                      ├─ skills/review-rule-generator
                      └─ skills/case-import
```

上传后的文件会落到服务端工作区，前端只保存工作区路径和任务状态，不再依赖本地 Finder 或 Tauri 文件系统能力。

## 项目结构

```text
auto-prompt-desktop-web/
├─ src/           # Vue Web 前端
├─ server/        # Rust Web API / 任务编排服务
├─ skills/        # Python skills
├─ src-tauri/     # 原桌面端实现，保留作迁移参考
├─ Dockerfile
└─ README.md
```

## 环境要求

本地开发需要：

- Node.js 18+
- Rust 1.75+
- Python 3.9+

Python 依赖：

- `openai`
- `openpyxl`
- `pymupdf`

## 本地启动

### 1. 安装依赖

```bash
npm install
pip install openai openpyxl pymupdf
```

### 2. 启动前端开发服务器

```bash
npm run dev:web
```

### 3. 启动 Rust Web 服务

```bash
npm run dev:server
```

默认访问地址：

- 前端开发页：[http://127.0.0.1:5173](http://127.0.0.1:5173)
- Web API 服务：[http://127.0.0.1:3000](http://127.0.0.1:3000)

Vite 已代理 `/api` 到 `http://127.0.0.1:3000`。

### 4. 构建生产版本

```bash
npm run build:all
```

启动生产服务（会先刷新当前前端构建，再启动 Rust Web 服务）：

```bash
npm run start
```

## Docker 部署

仓库内已提供单镜像部署所需的 `Dockerfile`。镜像会包含：

- 构建后的前端静态资源
- Rust Web 服务二进制
- Python 运行时
- `skills/` 目录

构建镜像：

```bash
docker build -t auto-prompt-web .
```

运行容器：

```bash
docker run --rm -p 3000:3000 -v "$(pwd)/.runtime-data:/data" auto-prompt-web
```

容器内默认数据目录：

- `/data/workspaces`
- `/data/uploads`
- `/data/tasks`
- `/data/settings.json`
- `/data/case_library.json`
- `/data/review_rule_library.json`

## 关键 API

- `POST /api/workspaces` 创建工作区并上传文件夹
- `GET /api/workspaces/:id` 查询工作区详情
- `POST /api/tasks/:kind` 提交后台任务
- `GET /api/task-runs/:id` 查询任务状态
- `GET /api/task-runs/:id/logs` 拉取任务日志
- `GET /api/settings` / `PUT /api/settings`
- `GET /api/cases` / `POST /api/cases/import-json` / `POST /api/cases/import-txt`
- `GET /api/review-rules` / `PUT /api/review-rules` / `DELETE /api/review-rules`
- `GET /api/health`

## 环境变量

- `AUTO_PROMPT_DATA_DIR`：服务端数据目录
- `AUTO_PROMPT_REPO_ROOT`：仓库根目录，服务端用来定位 `skills/`
- `AUTO_PROMPT_SKILLS_DIR`：Python skills 目录
- `AUTO_PROMPT_WEB_DIST`：前端静态资源目录
- `AUTOPROMPT_PYTHON`：显式指定 Python 可执行文件
- `PORT`：服务端监听端口，默认 `3000`
- `DASHSCOPE_API_KEY`：可作为默认模型密钥来源

## 测试

运行全部测试：

```bash
npm test
```

其中包含：

- 前端任务轮询单测
- Rust 服务单测

## 说明

- 原 `src-tauri/` 仍保留，方便迁移期对照和复用逻辑，但 Web 版已作为默认运行形态。
- 当前版本按单用户内网使用场景设计，未引入账号、权限和多租户。
