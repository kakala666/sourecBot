"""
认证 API
登录和 Token 管理
"""
from typing import Annotated

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Admin
from app.schemas.auth import Token, AdminInfo
from app.utils.auth import verify_password, create_access_token, decode_access_token


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
logger = logging.getLogger(__name__)


async def get_current_admin(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> Admin:
    """获取当前登录的管理员"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    result = await db.execute(
        select(Admin).where(Admin.username == username)
    )
    admin = result.scalar_one_or_none()
    
    if admin is None or not admin.is_active:
        raise credentials_exception
    
    return admin


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """管理员登录"""
    password_length = len(form_data.password.encode("utf-8"))
    client_host = request.client.host if request.client else "unknown"
    content_type = request.headers.get("content-type")
    content_length = request.headers.get("content-length")
    body_length = None
    try:
        raw_body = await request.body()
        body_length = len(raw_body) if raw_body is not None else 0
    except Exception as exc:
        logger.warning("读取登录请求体长度失败: %s", exc)

    logger.warning(
        "登录请求诊断: 用户名=%s, 密码长度=%s 字节, Content-Type=%s, Content-Length=%s, Body-Length=%s, 来源=%s",
        form_data.username,
        password_length,
        content_type,
        content_length,
        body_length,
        client_host,
    )
    # 查询管理员
    result = await db.execute(
        select(Admin).where(Admin.username == form_data.username)
    )
    admin = result.scalar_one_or_none()
    
    if not admin or not verify_password(form_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )
    
    # 创建 Token
    access_token = create_access_token(data={"sub": admin.username})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=AdminInfo)
async def get_current_admin_info(
    current_admin: Admin = Depends(get_current_admin)
):
    """获取当前管理员信息"""
    return AdminInfo(
        id=current_admin.id,
        username=current_admin.username,
        email=current_admin.email,
        is_active=current_admin.is_active,
    )
