# 数据模型定义 - 对应 Rust 的各种 struct
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


# ==================== 枚举类型 ====================

class TaskKind(str, Enum):
    """任务类型"""
    GENERATE = "generate"
    CLASSIFY = "classify"
    REVIEW_RULE = "review_rule"
    FACTOR_JSON = "factor_json"
    VERIFY_EXTRACTION = "verify_extraction"
    TEST_CLASSIFY_PROMPT = "test_classify_prompt"
    REGENERATE_KEYPOINT = "regenerate_keypoint"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    USER = "user"


# ==================== 任务相关模型 ====================

class Task(BaseModel):
    """任务模型"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: TaskKind
    status: TaskStatus = TaskStatus.PENDING
    progress: Optional[int] = Field(default=0, ge=0, le=100)
    owner_user_id: str
    workspace_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    result: Optional[Any] = None
    error: Optional[str] = None


class TaskRecord(BaseModel):
    """任务记录（包含日志）"""
    task: Task
    logs: List[str] = Field(default_factory=list)


class TaskQuery(BaseModel):
    """任务查询参数"""
    page: Optional[int] = None
    page_size: Optional[int] = None
    path: Optional[str] = None


# ==================== 用户相关模型 ====================

class UserProfile(BaseModel):
    """用户资料"""
    id: str
    name: str
    username: str
    role: UserRole
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserInDB(UserProfile):
    """数据库中的用户（包含密码哈希）"""
    password_hash: str


class AuthContext(BaseModel):
    """认证上下文"""
    token: str
    user: UserProfile


class AuthSession(BaseModel):
    """认证会话"""
    token: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class CreateUserRequest(BaseModel):
    """创建用户请求"""
    name: str
    username: str
    password: str


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    password: str


class UpdateUserStatusRequest(BaseModel):
    """更新用户状态请求"""
    active: bool


# ==================== API 请求/响应模型 ====================

class TestKeyRequest(BaseModel):
    """测试API密钥请求"""
    api_key: str


class PackagesRequest(BaseModel):
    """安装包请求"""
    packages: List[str]


class FileWriteRequest(BaseModel):
    """文件写入请求"""
    path: str
    content: str


class CaseImportJsonRequest(BaseModel):
    """JSON案例导入请求"""
    source_path: str
    overwrite: bool = False


class CaseImportTxtRequest(BaseModel):
    """TXT案例导入请求"""
    file_paths: List[str]


# ==================== 业务数据模型 ====================

class Factor(BaseModel):
    """要素定义"""
    field_name: str
    field_code: str
    description: str
    required: bool
    data_type: str
    material: str = ""


class GenerateResult(BaseModel):
    """生成结果"""
    output_file: str
    factors_count: int
    images_count: int
    prompt_template: Optional[str] = None


class VerifyResult(BaseModel):
    """验证结果"""
    image_file: str
    extraction_output: str
    success: bool
    error: Optional[str] = None
    elapsed: Optional[str] = None


class MaterialInfo(BaseModel):
    """材料信息"""
    name: str
    path: str
    image_count: int


class FileInfo(BaseModel):
    """文件信息"""
    name: str
    path: str
    size: int


class ClassificationReport(BaseModel):
    """分类报告"""
    run_time: Optional[str] = None
    base_dir: Optional[str] = None
    material_names: Optional[List[str]] = None
    image_count: Optional[int] = None
    iterations_run: Optional[int] = None
    extract_prompt_source: Optional[str] = None
    aggregate_prompt_source: Optional[str] = None
    step1_result: Optional[List[Dict]] = None
    step2_plan: Optional[List[Dict]] = None
    step2_summary: Optional[Dict] = None
    total_files: Optional[int] = None
    categories: Optional[List[str]] = None
    classified_dir: Optional[str] = None
    final_extract_prompt: Optional[str] = None
    final_aggregate_prompt: Optional[str] = None
    extract_template_path: Optional[str] = None
    aggregate_template_path: Optional[str] = None
    extract_template_content: Optional[str] = None
    aggregate_template_content: Optional[str] = None


class TestPromptResult(BaseModel):
    """测试提示词结果"""
    type: str
    pass_: bool = Field(alias="pass")
    issues: List[str]
    attachments: Optional[List[Dict]] = None
    plan: Optional[List[Dict]] = None
    summary: Optional[Dict] = None
    error: Optional[str] = None

    class Config:
        populate_by_name = True


class UploadManifestEntry(BaseModel):
    """上传清单条目"""
    path: str
    size: int
    checksum: Optional[str] = None


class UploadedBlob(BaseModel):
    """上传的文件块"""
    id: str
    filename: str
    size: int
    path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== 通用响应模型 ====================

class ApiResponse(BaseModel):
    """API通用响应"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None


class HealthStatus(BaseModel):
    """健康状态"""
    status: str = "healthy"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
