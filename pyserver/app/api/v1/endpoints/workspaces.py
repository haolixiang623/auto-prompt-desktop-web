"""
工作空间相关 API 端点
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form

from ....core.auth import AuthStore
from ....models.schemas import ApiResponse, UserProfile, UploadedBlob
from ....services.workspace import WorkspaceService, WorkspaceSummary

router = APIRouter(prefix="/api/workspaces", tags=["工作空间"])


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


@router.post("", response_model=ApiResponse)
async def create_workspace(
    name: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
    user: UserProfile = Depends(get_current_user)
):
    """创建工作空间（带文件上传）"""
    workspace_service = WorkspaceService()
    
    # 处理上传的文件
    uploads = []
    for file in files:
        content = await file.read()
        uploads.append(UploadedBlob(
            original_name=file.filename or "",
            relative_path=file.filename or "",
            content=content
        ))
    
    # 创建工作空间
    summary = workspace_service.create_workspace(
        user_id=user.id,
        name=name,
        uploads=uploads
    )
    
    return ApiResponse(data=summary.model_dump())


@router.get("/{workspace_id}", response_model=ApiResponse)
async def get_workspace(
    workspace_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """获取工作空间信息"""
    workspace_service = WorkspaceService()
    
    try:
        summary = workspace_service.get_workspace(user.id, workspace_id)
        return ApiResponse(data=summary.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
