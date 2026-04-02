"""
任务相关 API 端点
"""
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header

from ....core.auth import AuthStore
from ....core.config import SettingsStore
from ....core.tasks import TaskStore
from ....models.schemas import (
    ApiResponse,
    Task,
    TaskKind,
    TaskQuery,
    UserProfile,
    UserRole,
)
from ....services.ops import OpsService

router = APIRouter(prefix="/api/tasks", tags=["任务"])


# 依赖注入函数
def get_auth_store(): raise NotImplementedError
def get_task_store(): raise NotImplementedError
def get_settings_store(): raise NotImplementedError


def get_current_user(
    token: Optional[str] = Header(None, alias="Authorization"),
    auth_store: AuthStore = Depends()
) -> UserProfile:
    """获取当前用户"""
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    
    if token.startswith("Bearer "):
        token = token[7:]
    
    user = auth_store.get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效的认证令牌")
    
    return user


@router.post("/{kind}", response_model=ApiResponse)
async def start_task(
    kind: TaskKind,
    user: UserProfile = Depends(get_current_user),
    task_store: TaskStore = Depends(),
    settings_store: SettingsStore = Depends()
):
    """启动任务"""
    # 创建任务
    task = task_store.create(kind, user.id)
    
    # 根据任务类型启动异步处理
    if kind == TaskKind.GENERATE:
        # 启动生成要素任务
        pass  # TODO: 实现异步任务处理
    elif kind == TaskKind.CLASSIFY:
        # 启动分类任务
        pass
    
    return ApiResponse(data=task.model_dump())


@router.get("/runs/{task_id}", response_model=ApiResponse)
async def get_task(
    task_id: str,
    user: UserProfile = Depends(get_current_user),
    task_store: TaskStore = Depends()
):
    """获取任务状态"""
    task = task_store.get(task_id, user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return ApiResponse(data=task.model_dump())


@router.get("/runs/{task_id}/logs", response_model=ApiResponse)
async def get_task_logs(
    task_id: str,
    user: UserProfile = Depends(get_current_user),
    task_store: TaskStore = Depends()
):
    """获取任务日志"""
    logs = task_store.logs(task_id, user.id)
    if logs is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return ApiResponse(data={"logs": logs})
