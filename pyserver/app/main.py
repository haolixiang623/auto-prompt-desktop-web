"""
FastAPI 主应用
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .core.auth import AuthStore
from .core.config import SettingsStore
from .core.paths import AppPaths, get_paths
from .core.tasks import TaskStore
from .api.v1.endpoints import auth, tasks, workspaces, files, settings, cases


#  lifespan 上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    paths = get_paths()
    
    # 初始化认证存储
    auth_store = AuthStore(paths.auth_db_path)
    app.state.auth_store = auth_store
    
    # 初始化设置存储
    settings_store = SettingsStore(
        paths.settings_path,
        paths.repo_root / "auto-prompt.project.json"
    )
    # 尝试迁移旧配置
    settings_store.migrate_legacy_if_needed()
    app.state.settings_store = settings_store
    
    # 初始化任务存储
    task_store = TaskStore(paths.task_root)
    app.state.task_store = task_store
    
    print(f"Server initialized")
    print(f"Data directory: {paths.data_dir}")
    print(f"Web dist: {paths.web_dist}")
    
    yield
    
    # 关闭时清理
    print("Server shutting down")


# 创建 FastAPI 应用
app = FastAPI(
    title="Auto Prompt API",
    description="Auto Prompt 后端 API (Python/FastAPI)",
    version="0.1.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册 API 路由
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(workspaces.router)
app.include_router(files.router)
app.include_router(settings.router)
app.include_router(cases.router)


# 健康检查
@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "backend": "python-fastapi"
    }


# 静态文件服务和前端路由
def setup_static_files():
    """设置静态文件服务"""
    paths = get_paths()
    static_dir = paths.web_dist
    index_file = static_dir / "index.html"
    
    # 如果前端目录存在，挂载静态文件
    if static_dir.exists() and index_file.exists():
        # 挂载 dist 目录
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
        
        # 根路由返回 index.html
        @app.get("/", response_class=HTMLResponse)
        async def root():
            with open(index_file, "r", encoding="utf-8") as f:
                return f.read()
        
        # 前端路由回退
        @app.get("/{path:path}", response_class=HTMLResponse)
        async def catch_all(path: str, request: Request):
            # API 请求不应该到这里
            if path.startswith("api/"):
                return HTMLResponse("Not Found", status_code=404)
            
            # 检查是否是文件
            file_path = static_dir / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            
            # 否则返回 index.html（前端路由）
            with open(index_file, "r", encoding="utf-8") as f:
                return f.read()
    else:
        # 如果没有前端文件，显示 API 信息
        @app.get("/")
        async def root():
            return {
                "message": "Auto Prompt API Server",
                "version": "0.1.0",
                "docs": "/docs"
            }


# 初始化静态文件服务
setup_static_files()


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 3000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)
