"""
邀请链接 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
import secrets
import string

from app.database import get_db
from app.models import InviteLink, User
from app.api.auth import get_current_admin


router = APIRouter()


# ---------- Schema ----------

class InviteLinkCreate(BaseModel):
    """创建邀请链接请求"""
    name: str
    code: Optional[str] = None  # 可选,不提供则自动生成


class InviteLinkUpdate(BaseModel):
    """更新邀请链接请求"""
    name: Optional[str] = None
    is_active: Optional[bool] = None


class InviteLinkResponse(BaseModel):
    """邀请链接响应"""
    id: int
    code: str
    name: str
    is_active: bool
    deep_link: str
    resource_count: int = 0
    user_count: int = 0
    
    class Config:
        from_attributes = True


# ---------- API ----------

def generate_invite_code(length: int = 8) -> str:
    """生成邀请码"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


@router.get("", response_model=List[InviteLinkResponse])
async def list_invite_links(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取邀请链接列表"""
    result = await db.execute(
        select(InviteLink)
        .options(selectinload(InviteLink.resources))
        .order_by(InviteLink.created_at.desc())
    )
    links = result.scalars().all()
    
    response = []
    for link in links:
        # 统计用户数
        user_count_result = await db.execute(
            select(func.count()).select_from(User).where(User.invite_code == link.code)
        )
        user_count = user_count_result.scalar() or 0
        
        response.append(InviteLinkResponse(
            id=link.id,
            code=link.code,
            name=link.name,
            is_active=link.is_active,
            deep_link=f"https://t.me/YourBot?start={link.code}",  # TODO: 替换为实际 Bot 用户名
            resource_count=len(link.resources),
            user_count=user_count,
        ))
    
    return response


@router.post("", response_model=InviteLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_invite_link(
    data: InviteLinkCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """创建邀请链接"""
    # 生成或使用提供的邀请码
    code = data.code or generate_invite_code()
    
    # 检查邀请码是否已存在
    existing = await db.execute(
        select(InviteLink).where(InviteLink.code == code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"邀请码 '{code}' 已存在"
        )
    
    # 创建邀请链接
    link = InviteLink(code=code, name=data.name)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    
    return InviteLinkResponse(
        id=link.id,
        code=link.code,
        name=link.name,
        is_active=link.is_active,
        deep_link=f"https://t.me/YourBot?start={link.code}",
        resource_count=0,
        user_count=0,
    )


@router.get("/{link_id}", response_model=InviteLinkResponse)
async def get_invite_link(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取单个邀请链接"""
    result = await db.execute(
        select(InviteLink)
        .options(selectinload(InviteLink.resources))
        .where(InviteLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请链接不存在"
        )
    
    # 统计用户数
    user_count_result = await db.execute(
        select(func.count()).select_from(User).where(User.invite_code == link.code)
    )
    user_count = user_count_result.scalar() or 0
    
    return InviteLinkResponse(
        id=link.id,
        code=link.code,
        name=link.name,
        is_active=link.is_active,
        deep_link=f"https://t.me/YourBot?start={link.code}",
        resource_count=len(link.resources),
        user_count=user_count,
    )


@router.patch("/{link_id}", response_model=InviteLinkResponse)
async def update_invite_link(
    link_id: int,
    data: InviteLinkUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """更新邀请链接"""
    result = await db.execute(
        select(InviteLink).where(InviteLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请链接不存在"
        )
    
    if data.name is not None:
        link.name = data.name
    if data.is_active is not None:
        link.is_active = data.is_active
    
    await db.commit()
    await db.refresh(link)
    
    return InviteLinkResponse(
        id=link.id,
        code=link.code,
        name=link.name,
        is_active=link.is_active,
        deep_link=f"https://t.me/YourBot?start={link.code}",
        resource_count=0,
        user_count=0,
    )


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invite_link(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """删除邀请链接"""
    result = await db.execute(
        select(InviteLink).where(InviteLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请链接不存在"
        )
    
    await db.delete(link)
    await db.commit()
