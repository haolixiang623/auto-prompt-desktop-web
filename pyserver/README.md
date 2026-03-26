# Python 后端版本

这是 Auto Prompt 的 Python/FastAPI 后端版本，替代了原来的 Rust 后端。

## 技术栈

- **后端框架**: FastAPI 0.109+
- **Python 版本**: 3.11+
- **认证**: JWT + SQLite (argon2 密码哈希)
- **任务系统**: 内存 + 文件持久化
- **API 文档**: 自动生成 (Swagger/OpenAPI)

## 项目结构

```
pyserver/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── auth.py          # 认证相关 API
│   │           ├── tasks.py         # 任务管理 API
│   │           ├── workspaces.py    # 工作空间 API
│   │           ├── files.py         # 文件操作 API
│   │           ├── settings.py      # 设置管理 API
│   │           └── cases.py         # 案例和审查规则 API
│   ├── core/
│   │   ├── paths.py                 # 路径管理
│   │   ├── config.py                # 配置管理
│   │   ├── auth.py                  # 用户认证
│   │   └── tasks.py                 # 任务存储
│   ├── models/
│   │   └── schemas.py               # Pydantic 模型
│   └── services/
│       ├── ops.py                   # 业务逻辑 (调用 skills)
│       └── workspace.py             # 工作空间服务
│   └── main.py                      # FastAPI 主应用
├── requirements.txt                  # Python 依赖
└── tests/                            # 测试目录
```

## 部署方式

### 方式 1: Docker (推荐)

```bash
# 使用 Python 版本的 Dockerfile
docker build -f Dockerfile.python -t auto-prompt-py:latest .

# 运行容器
docker run -d \
  --name auto-prompt-py \
  -p 3000:3000 \
  -v app-data:/data \
  auto-prompt-py:latest
```

### 方式 2: Docker Compose

```bash
# 使用 Python 版本的 compose 文件
docker-compose -f docker-compose.python.yml up -d --build
```

### 方式 3: 直接运行 (开发)

```bash
cd pyserver
pip install -r requirements.txt

# 开发模式启动 (热重载)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
```

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| PORT | 3000 | 服务端口 |
| HOST | 0.0.0.0 | 绑定地址 |
| AUTO_PROMPT_REPO_ROOT | /app | 项目根目录 |
| AUTO_PROMPT_SKILLS_DIR | /app/skills | Skills 脚本目录 |
| AUTO_PROMPT_WEB_DIST | /app/dist | 前端构建目录 |
| AUTO_PROMPT_DATA_DIR | /data | 数据存储目录 |

## API 文档

启动服务后访问:
- Swagger UI: `http://localhost:3000/docs`
- ReDoc: `http://localhost:3000/redoc`

## 与 Rust 后端的差异

| 特性 | Rust 版本 | Python 版本 |
|------|-----------|-------------|
| 启动速度 | 快 | 较慢 |
| 内存占用 | 低 | 较高 |
| 开发效率 | 较低 | 较高 |
| AI 生态集成 | 需外部调用 | 直接集成 |
| 类型安全 | 编译期检查 | 运行时检查 |

## 默认账户

- **用户名**: `admin`
- **密码**: `admin123`

**注意**: 生产环境请立即修改默认密码！

## 开发说明

### 添加新的 API 端点

1. 在 `app/api/v1/endpoints/` 创建端点文件
2. 在 `app/main.py` 注册路由
3. 在 `app/models/schemas.py` 添加数据模型

### 测试

```bash
cd pyserver
pytest
```

## 迁移指南

从 Rust 后端迁移到 Python 后端:

1. 备份 `/data` 目录数据
2. 停止旧容器
3. 使用新的 `Dockerfile.python` 构建
4. 恢复数据目录
5. 启动新容器

注意: 认证数据库和设置文件格式兼容，可以直接迁移。
