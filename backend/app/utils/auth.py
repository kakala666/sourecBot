"""
认证工具模块
密码加密和 JWT Token 处理
"""
from datetime import datetime, timedelta
from typing import Optional

import logging

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import settings


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """对密码进行哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    password_length = len(plain_password.encode("utf-8"))
    if password_length > 72:
        logger.warning("登录密码长度超出 bcrypt 限制: %s 字节", password_length)
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError as exc:
        logger.warning("密码校验异常: %s (长度: %s 字节)", exc, password_length)
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码 JWT Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
