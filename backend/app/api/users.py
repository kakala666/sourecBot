"""
用户管理 API
用户列表和详情查询
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.database import get_db
from app.models import User, UserSession, InviteLink
from app.api.auth import get_current_admin


router = APIRouter()


# ---------- Schema ----------

class UserResponse(BaseModel):
    """用户响应"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    invite_code: Optional[str]
    invite_link_name: Optional[str] = None
    first_seen: Optional[datetime]
    last_active: Optional[datetime]
    # 会话信息
    current_page: Optional[int] = None
    wait_count: Optional[int] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


# ---------- API ----------

@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索用户名/名字"),
    invite_code: Optional[str] = Query(None, description="按来源链接筛选"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取用户列表"""
    # 构建查询
    query = select(User).options(
        selectinload(User.session),
        selectinload(User.invite_link)
    )
    
    # 搜索条件
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.username.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern)
            )
        )
    
    # 来源链接筛选
    if invite_code:
        query = query.where(User.invite_code == invite_code)
    
    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    query = query.order_by(User.last_active.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # 构建响应
    items = []
    for user in users:
        # 获取来源链接名称
        invite_link_name = None
        if user.invite_link:
            invite_link_name = user.invite_link.name
        
        # 获取会话信息
        current_page = None
        wait_count = None
        if user.session:
            current_page = user.session.current_page
            wait_count = user.session.wait_count
        
        items.append(UserResponse(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            invite_code=user.invite_code,
            invite_link_name=invite_link_name,
            first_seen=user.first_seen,
            last_active=user.last_active,
            current_page=current_page,
            wait_count=wait_count
        ))
    
    return UserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{telegram_id}", response_model=UserResponse)
async def get_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取单个用户详情"""
    result = await db.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(
            selectinload(User.session),
            selectinload(User.invite_link)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 获取来源链接名称
    invite_link_name = None
    if user.invite_link:
        invite_link_name = user.invite_link.name
    
    # 获取会话信息
    current_page = None
    wait_count = None
    if user.session:
        current_page = user.session.current_page
        wait_count = user.session.wait_count
    
    return UserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        invite_code=user.invite_code,
        invite_link_name=invite_link_name,
        first_seen=user.first_seen,
        last_active=user.last_active,
        current_page=current_page,
        wait_count=wait_count
    )
