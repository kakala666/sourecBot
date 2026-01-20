"""
认证相关 Schema
"""
from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 数据"""
    username: Optional[str] = None


class AdminInfo(BaseModel):
    """管理员信息"""
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str
