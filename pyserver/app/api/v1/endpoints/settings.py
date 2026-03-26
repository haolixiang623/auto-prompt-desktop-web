"""
设置相关 API 端点
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header

from ....core.auth import AuthStore
from ....core.config import SettingsStore, AppSettings
from ....models.schemas import ApiResponse, TestKeyRequest, UserProfile, UserRole

router = APIRouter(prefix="/api/settings", tags=["设置"])


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


def require_admin(user: UserProfile = Depends(get_current_user)) -> UserProfile:
    """要求管理员权限"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@router.get("", response_model=ApiResponse)
async def get_settings(
    user: UserProfile = Depends(get_current_user),
    settings_store: SettingsStore = Depends()
):
    """获取设置（隐藏敏感信息）"""
    settings = settings_store.get()
    
    # 隐藏API密钥
    data = settings.to_dict()
    if data.get("api_key"):
        data["api_key"] = "***" + data["api_key"][-4:] if len(data["api_key"]) > 4 else "***"
    
    return ApiResponse(data=data)


@router.put("", response_model=ApiResponse)
async def update_settings(
    settings: AppSettings,
    admin: UserProfile = Depends(require_admin),
    settings_store: SettingsStore = Depends()
):
    """更新设置（仅管理员）"""
    settings_store.update(settings)
    return ApiResponse()


@router.get("/default-prompts", response_model=ApiResponse)
async def get_default_prompts(
    user: UserProfile = Depends(get_current_user),
    settings_store: SettingsStore = Depends()
):
    """获取默认提示词"""
    settings = settings_store.get()
    prompts = {
        "extract": settings.default_prompts.extract if hasattr(settings, 'default_prompts') else "",
        "aggregate": settings.default_prompts.aggregate if hasattr(settings, 'default_prompts') else "",
        "review": settings.default_prompts.review if hasattr(settings, 'default_prompts') else "",
        "classify": settings.default_prompts.classify if hasattr(settings, 'default_prompts') else "",
    }
    return ApiResponse(data=prompts)


@router.post("/test-key", response_model=ApiResponse)
async def test_api_key(
    req: TestKeyRequest,
    admin: UserProfile = Depends(require_admin)
):
    """测试API密钥（仅管理员）"""
    # 这里应该实现实际的API密钥测试逻辑
    # 简化实现：只检查密钥格式
    if not req.api_key or len(req.api_key) < 10:
        return ApiResponse(success=False, error="API密钥格式无效")
    
    return ApiResponse(data={"valid": True, "message": "API密钥格式有效"})
