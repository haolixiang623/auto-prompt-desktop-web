# 用户认证模块 - 对应 Rust auth.rs
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ..models.schemas import (
    AuthSession, 
    CreateUserRequest, 
    UserInDB, 
    UserProfile, 
    UserRole
)


# 密码哈希器
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """哈希密码"""
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    try:
        ph.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def generate_token() -> str:
    """生成随机令牌"""
    return secrets.token_urlsafe(32)


class AuthStore:
    """认证存储 - 使用 SQLite 存储用户和会话"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._sessions: Dict[str, AuthSession] = {}  # 内存会话缓存
        self.initialize()
    
    def initialize(self) -> None:
        """初始化数据库表"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
        
        # 创建默认管理员账户
        self._create_default_admin()
    
    def _create_default_admin(self) -> None:
        """创建默认管理员账户"""
        try:
            self.create_user(
                CreateUserRequest(
                    name="Administrator",
                    username="admin",
                    password="admin123"  # 生产环境应该修改默认密码
                ),
                role=UserRole.ADMIN
            )
        except Exception:
            # 用户已存在或其他错误，忽略
            pass
    
    def create_user(self, req: CreateUserRequest, role: UserRole = UserRole.USER) -> UserProfile:
        """创建用户"""
        user_id = secrets.token_hex(16)
        password_hash = hash_password(req.password)
        now = datetime.utcnow().isoformat()
        
        with sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    "INSERT INTO users (id, name, username, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, req.name, req.username, password_hash, role.value, 1, now)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise ValueError(f"用户名 '{req.username}' 已存在")
        
        return UserProfile(
            id=user_id,
            name=req.name,
            username=req.username,
            role=role,
            active=True,
            created_at=datetime.fromisoformat(now)
        )
    
    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """通过用户名获取用户"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            
            if row is None:
                return None
            
            return UserInDB(
                id=row["id"],
                name=row["name"],
                username=row["username"],
                role=UserRole(row["role"]),
                active=bool(row["active"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                password_hash=row["password_hash"]
            )
    
    def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """通过ID获取用户"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, name, username, role, active, created_at FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            
            if row is None:
                return None
            
            return UserProfile(
                id=row["id"],
                name=row["name"],
                username=row["username"],
                role=UserRole(row["role"]),
                active=bool(row["active"]),
                created_at=datetime.fromisoformat(row["created_at"])
            )
    
    def list_users(self) -> List[UserProfile]:
        """列出所有用户"""
        users = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, name, username, role, active, created_at FROM users ORDER BY created_at"
            ).fetchall()
            
            for row in rows:
                users.append(UserProfile(
                    id=row["id"],
                    name=row["name"],
                    username=row["username"],
                    role=UserRole(row["role"]),
                    active=bool(row["active"]),
                    created_at=datetime.fromisoformat(row["created_at"])
                ))
        
        return users
    
    def update_user_status(self, user_id: str, active: bool) -> bool:
        """更新用户状态"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "UPDATE users SET active = ? WHERE id = ?",
                (1 if active else 0, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def reset_password(self, user_id: str, new_password: str) -> bool:
        """重置用户密码"""
        password_hash = hash_password(new_password)
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def authenticate(self, username: str, password: str) -> Optional[UserProfile]:
        """验证用户凭据"""
        user = self.get_user_by_username(username)
        if user is None:
            return None
        
        if not user.active:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return UserProfile(
            id=user.id,
            name=user.name,
            username=user.username,
            role=user.role,
            active=user.active,
            created_at=user.created_at
        )
    
    def create_session(self, user: UserProfile) -> str:
        """创建会话并返回令牌"""
        token = generate_token()
        session = AuthSession(
            token=token,
            user_id=user.id,
            created_at=datetime.utcnow()
        )
        self._sessions[token] = session
        return token
    
    def get_session(self, token: str) -> Optional[AuthSession]:
        """获取会话"""
        return self._sessions.get(token)
    
    def delete_session(self, token: str) -> bool:
        """删除会话（登出）"""
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False
    
    def get_user_from_token(self, token: str) -> Optional[UserProfile]:
        """通过令牌获取用户"""
        session = self.get_session(token)
        if session is None:
            return None
        return self.get_user_by_id(session.user_id)
