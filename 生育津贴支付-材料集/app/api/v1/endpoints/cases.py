"""
案例和审查规则相关 API 端点
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header

from ....core.auth import AuthStore
from ....models.schemas import (
    ApiResponse,
    CaseImportJsonRequest,
    CaseImportTxtRequest,
    UserProfile,
    UserRole,
)
from ....services.ops import OpsService
from ....core.config import SettingsStore

router = APIRouter(tags=["案例和审查规则"])


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


# ==================== 案例相关端点 ====================

@router.get("/api/cases", response_model=ApiResponse)
async def get_cases(
    user: UserProfile = Depends(get_current_user),
    settings_store: SettingsStore = Depends()
):
    """获取所有案例"""
    ops_service = OpsService(settings_store)
    cases = ops_service.get_cases()
    return ApiResponse(data=cases)


@router.post("/api/cases/import-json", response_model=ApiResponse)
async def import_cases_json(
    req: CaseImportJsonRequest,
    admin: UserProfile = Depends(require_admin),
    settings_store: SettingsStore = Depends()
):
    """从JSON导入案例（仅管理员）"""
    ops_service = OpsService(settings_store)
    count = ops_service.import_cases_from_json(req.source_path, req.overwrite)
    return ApiResponse(data={"imported_count": count})


@router.post("/api/cases/import-txt", response_model=ApiResponse)
async def import_cases_txt(
    req: CaseImportTxtRequest,
    admin: UserProfile = Depends(require_admin),
    settings_store: SettingsStore = Depends()
):
    """从TXT导入案例（仅管理员）"""
    # TODO: 实现从提示词文件解析案例
    return ApiResponse(success=False, error="功能未实现")


@router.delete("/api/cases/{case_id}", response_model=ApiResponse)
async def delete_case(
    case_id: str,
    admin: UserProfile = Depends(require_admin),
    settings_store: SettingsStore = Depends()
):
    """删除案例（仅管理员）"""
    ops_service = OpsService(settings_store)
    success = ops_service.delete_case(case_id)
    if not success:
        raise HTTPException(status_code=404, detail="案例不存在")
    return ApiResponse()


# ==================== 审查规则相关端点 ====================

@router.get("/api/review-rules", response_model=ApiResponse)
async def get_review_rules(
    user: UserProfile = Depends(get_current_user),
    settings_store: SettingsStore = Depends()
):
    """获取审查规则"""
    ops_service = OpsService(settings_store)
    rules = ops_service.get_review_rules()
    return ApiResponse(data=rules)


@router.put("/api/review-rules", response_model=ApiResponse)
async def update_review_rules(
    rules: List[dict],
    admin: UserProfile = Depends(require_admin),
    settings_store: SettingsStore = Depends()
):
    """更新审查规则（仅管理员）"""
    ops_service = OpsService(settings_store)
    success = ops_service.update_review_rules(rules)
    return ApiResponse(data={"success": success})


@router.delete("/api/review-rules", response_model=ApiResponse)
async def clear_review_rules(
    admin: UserProfile = Depends(require_admin),
    settings_store: SettingsStore = Depends()
):
    """清除审查规则（仅管理员）"""
    ops_service = OpsService(settings_store)
    success = ops_service.clear_review_rules()
    return ApiResponse(data={"success": success})
