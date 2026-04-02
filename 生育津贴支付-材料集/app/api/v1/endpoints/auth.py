"""
认证相关 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from typing import Optional

from ....core.auth import AuthStore
from ....core.paths import get_paths
from ....core.config import SettingsStore
from ....models.schemas import (
    ApiResponse,
    CreateUserRequest,
    LoginRequest,
    ResetPasswordRequest,
    UpdateUserStatusRequest,
    UserProfile,
    UserRole,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


# 依赖注入
def get_auth_store(request: Request) -> AuthStore:
    return request.app.state.auth_store


def get_settings_store(request: Request) -> SettingsStore:
    return request.app.state.settings_store


# 从请求头获取 token
def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


@router.post("/login", response_model=ApiResponse)
async def login(
    req: LoginRequest,
    auth_store: AuthStore = Depends(get_auth_store)
):
    """用户登录"""
    user = auth_store.authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    token = auth_store.create_session(user)
    return ApiResponse(
        data={
            "token": token,
            "user": user.model_dump()
        }
    )


@router.get("/me", response_model=ApiResponse)
async def get_current_user(
    auth_store: AuthStore = Depends(get_auth_store),
    token: Optional[str] = Depends(get_token_from_header)
):
    """获取当前用户信息"""
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    
    user = auth_store.get_user_from_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="无效的认证令牌")
    
    return ApiResponse(data=user.model_dump())


@router.post("/logout", response_model=ApiResponse)
async def logout(
    auth_store: AuthStore = Depends(get_auth_store),
    token: Optional[str] = Depends(get_token_from_header)
):
    """用户登出"""
    if token:
        auth_store.delete_session(token)
    return ApiResponse()


# ==================== 管理员端点 ====================

@router.get("/users", response_model=ApiResponse)
async def list_users(
    auth_store: AuthStore = Depends(get_auth_store),
    token: Optional[str] = Depends(get_token_from_header)
):
    """列出所有用户（仅管理员）"""
    user = auth_store.get_user_from_token(token) if token else None
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    users = auth_store.list_users()
    return ApiResponse(data=[u.model_dump() for u in users])


@router.post("/users", response_model=ApiResponse)
async def create_user(
    req: CreateUserRequest,
    auth_store: AuthStore = Depends(get_auth_store),
    token: Optional[str] = Depends(get_token_from_header)
):
    """创建用户（仅管理员）"""
    user = auth_store.get_user_from_token(token) if token else None
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    new_user = auth_store.create_user(req)
    return ApiResponse(data=new_user.model_dump())


@router.post("/users/{user_id}/password", response_model=ApiResponse)
async def reset_user_password(
    user_id: str,
    req: ResetPasswordRequest,
    auth_store: AuthStore = Depends(get_auth_store),
    token: Optional[str] = Depends(get_token_from_header)
):
    """重置用户密码（仅管理员）"""
    user = auth_store.get_user_from_token(token) if token else None
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    success = auth_store.reset_password(user_id, req.password)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return ApiResponse()


@router.put("/users/{user_id}/status", response_model=ApiResponse)
async def update_user_status(
    user_id: str,
    req: UpdateUserStatusRequest,
    auth_store: AuthStore = Depends(get_auth_store),
    token: Optional[str] = Depends(get_token_from_header)
):
    """更新用户状态（仅管理员）"""
    user = auth_store.get_user_from_token(token) if token else None
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    success = auth_store.update_user_status(user_id, req.active)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return ApiResponse()
