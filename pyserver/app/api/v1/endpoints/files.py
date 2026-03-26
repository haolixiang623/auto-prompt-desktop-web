"""
文件相关 API 端点
"""
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import FileResponse, PlainTextResponse

from ....core.auth import AuthStore
from ....models.schemas import ApiResponse, FileWriteRequest, UserProfile

router = APIRouter(prefix="/api/files", tags=["文件"])


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


@router.get("/content")
async def read_file_content(
    path: str = Query(..., description="文件路径"),
    user: UserProfile = Depends(get_current_user)
):
    """读取文件内容"""
    file_path = Path(path)
    
    # 安全检查：确保文件在允许的目录内
    if ".." in str(file_path):
        raise HTTPException(status_code=403, detail="非法路径")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return PlainTextResponse(content)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件不是文本文件")


@router.put("/content", response_model=ApiResponse)
async def write_file_content(
    req: FileWriteRequest,
    user: UserProfile = Depends(get_current_user)
):
    """写入文件内容"""
    file_path = Path(req.path)
    
    # 安全检查
    if ".." in str(file_path):
        raise HTTPException(status_code=403, detail="非法路径")
    
    # 确保父目录存在
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(req.content)
    
    return ApiResponse()


@router.get("/download")
async def download_file(
    path: str = Query(..., description="文件路径"),
    user: UserProfile = Depends(get_current_user)
):
    """下载文件"""
    file_path = Path(path)
    
    if ".." in str(file_path):
        raise HTTPException(status_code=403, detail="非法路径")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(file_path, filename=file_path.name)


@router.get("/browse", response_model=ApiResponse)
async def browse_path(
    path: str = Query(..., description="目录路径"),
    user: UserProfile = Depends(get_current_user)
):
    """浏览目录内容"""
    dir_path = Path(path)
    
    if ".." in str(dir_path):
        raise HTTPException(status_code=403, detail="非法路径")
    
    if not dir_path.exists():
        raise HTTPException(status_code=404, detail="路径不存在")
    
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")
    
    items = []
    for entry in os.scandir(dir_path):
        stat = entry.stat()
        items.append({
            "name": entry.name,
            "path": str(Path(entry.path)),
            "is_dir": entry.is_dir(),
            "size": stat.st_size,
            "modified": stat.st_mtime
        })
    
    items.sort(key=lambda x: (not x["is_dir"], x["name"]))
    
    return ApiResponse(data=items)
