"""
广告管理 API
广告组和赞助商广告 CRUD
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.database import get_db
from app.models import AdGroup, Sponsor, InviteLink, InviteLinkAdGroup
from app.api.auth import get_current_admin


router = APIRouter()


# ---------- Schema ----------

class AdGroupCreate(BaseModel):
    """创建广告组请求"""
    name: str


class AdGroupUpdate(BaseModel):
    """更新广告组请求"""
    name: Optional[str] = None


class SponsorCreate(BaseModel):
    """创建广告请求"""
    ad_group_id: int
    title: str
    description: Optional[str] = None
    media_type: Optional[str] = None  # photo/video/none
    telegram_file_id: Optional[str] = None
    button_text: Optional[str] = None
    button_url: Optional[str] = None
    is_active: bool = True
    display_order: int = 0


class SponsorUpdate(BaseModel):
    """更新广告请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    media_type: Optional[str] = None
    telegram_file_id: Optional[str] = None
    button_text: Optional[str] = None
    button_url: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class SponsorResponse(BaseModel):
    """广告响应"""
    id: int
    ad_group_id: int
    title: str
    description: Optional[str]
    media_type: Optional[str]
    telegram_file_id: Optional[str]
    button_text: Optional[str]
    button_url: Optional[str]
    is_active: bool
    display_order: int
    
    class Config:
        from_attributes = True


class AdGroupResponse(BaseModel):
    """广告组响应"""
    id: int
    name: str
    sponsors: List[SponsorResponse] = []
    linked_invite_links: List[int] = []
    
    class Config:
        from_attributes = True


class LinkAdGroupRequest(BaseModel):
    """绑定广告组请求"""
    invite_link_id: int
    ad_group_id: int


# ---------- 广告组 API ----------

@router.get("/groups", response_model=List[AdGroupResponse])
async def list_ad_groups(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取广告组列表"""
    result = await db.execute(
        select(AdGroup).options(selectinload(AdGroup.sponsors))
    )
    groups = result.scalars().all()
    
    response = []
    for group in groups:
        # 获取绑定的邀请链接
        links_result = await db.execute(
            select(InviteLinkAdGroup.invite_link_id)
            .where(InviteLinkAdGroup.ad_group_id == group.id)
        )
        linked_ids = [row[0] for row in links_result.fetchall()]
        
        response.append(AdGroupResponse(
            id=group.id,
            name=group.name,
            sponsors=[SponsorResponse.model_validate(s) for s in group.sponsors],
            linked_invite_links=linked_ids,
        ))
    
    return response


@router.post("/groups", response_model=AdGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_ad_group(
    data: AdGroupCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """创建广告组"""
    group = AdGroup(name=data.name)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    return AdGroupResponse(
        id=group.id,
        name=group.name,
        sponsors=[],
        linked_invite_links=[],
    )


@router.patch("/groups/{group_id}", response_model=AdGroupResponse)
async def update_ad_group(
    group_id: int,
    data: AdGroupUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """更新广告组"""
    result = await db.execute(
        select(AdGroup).where(AdGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="广告组不存在"
        )
    
    if data.name is not None:
        group.name = data.name
    
    await db.commit()
    await db.refresh(group)
    
    return AdGroupResponse(
        id=group.id,
        name=group.name,
        sponsors=[],
        linked_invite_links=[],
    )


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ad_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """删除广告组"""
    result = await db.execute(
        select(AdGroup).where(AdGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="广告组不存在"
        )
    
    await db.delete(group)
    await db.commit()


# ---------- 广告 API ----------

@router.get("", response_model=List[SponsorResponse])
async def list_sponsors(
    ad_group_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取广告列表"""
    query = select(Sponsor).order_by(Sponsor.display_order)
    
    if ad_group_id:
        query = query.where(Sponsor.ad_group_id == ad_group_id)
    
    result = await db.execute(query)
    sponsors = result.scalars().all()
    
    return sponsors


@router.post("", response_model=SponsorResponse, status_code=status.HTTP_201_CREATED)
async def create_sponsor(
    data: SponsorCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """创建广告"""
    # 检查广告组是否存在
    group_result = await db.execute(
        select(AdGroup).where(AdGroup.id == data.ad_group_id)
    )
    if not group_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="广告组不存在"
        )
    
    sponsor = Sponsor(
        ad_group_id=data.ad_group_id,
        title=data.title,
        description=data.description,
        media_type=data.media_type,
        telegram_file_id=data.telegram_file_id,
        button_text=data.button_text,
        button_url=data.button_url,
        is_active=data.is_active,
        display_order=data.display_order,
    )
    db.add(sponsor)
    await db.commit()
    await db.refresh(sponsor)
    
    return sponsor


@router.patch("/{sponsor_id}", response_model=SponsorResponse)
async def update_sponsor(
    sponsor_id: int,
    data: SponsorUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """更新广告"""
    result = await db.execute(
        select(Sponsor).where(Sponsor.id == sponsor_id)
    )
    sponsor = result.scalar_one_or_none()
    
    if not sponsor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="广告不存在"
        )
    
    if data.title is not None:
        sponsor.title = data.title
    if data.description is not None:
        sponsor.description = data.description
    if data.media_type is not None:
        sponsor.media_type = data.media_type
    if data.telegram_file_id is not None:
        sponsor.telegram_file_id = data.telegram_file_id
    if data.button_text is not None:
        sponsor.button_text = data.button_text
    if data.button_url is not None:
        sponsor.button_url = data.button_url
    if data.is_active is not None:
        sponsor.is_active = data.is_active
    if data.display_order is not None:
        sponsor.display_order = data.display_order
    
    await db.commit()
    await db.refresh(sponsor)
    
    return sponsor


@router.delete("/{sponsor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sponsor(
    sponsor_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """删除广告"""
    result = await db.execute(
        select(Sponsor).where(Sponsor.id == sponsor_id)
    )
    sponsor = result.scalar_one_or_none()
    
    if not sponsor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="广告不存在"
        )
    
    await db.delete(sponsor)
    await db.commit()


# ---------- 绑定 API ----------

@router.post("/link", status_code=status.HTTP_201_CREATED)
async def link_ad_group_to_invite_link(
    data: LinkAdGroupRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """绑定广告组到邀请链接"""
    # 检查邀请链接是否存在
    link_result = await db.execute(
        select(InviteLink).where(InviteLink.id == data.invite_link_id)
    )
    if not link_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请链接不存在"
        )
    
    # 检查广告组是否存在
    group_result = await db.execute(
        select(AdGroup).where(AdGroup.id == data.ad_group_id)
    )
    if not group_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="广告组不存在"
        )
    
    # 检查是否已绑定
    existing = await db.execute(
        select(InviteLinkAdGroup).where(
            InviteLinkAdGroup.invite_link_id == data.invite_link_id,
            InviteLinkAdGroup.ad_group_id == data.ad_group_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已绑定该广告组"
        )
    
    # 创建绑定
    link_ad = InviteLinkAdGroup(
        invite_link_id=data.invite_link_id,
        ad_group_id=data.ad_group_id,
    )
    db.add(link_ad)
    await db.commit()
    
    return {"message": "绑定成功"}


@router.delete("/link", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_ad_group_from_invite_link(
    invite_link_id: int,
    ad_group_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """解除广告组与邀请链接的绑定"""
    result = await db.execute(
        select(InviteLinkAdGroup).where(
            InviteLinkAdGroup.invite_link_id == invite_link_id,
            InviteLinkAdGroup.ad_group_id == ad_group_id
        )
    )
    link_ad = result.scalar_one_or_none()
    
    if not link_ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="绑定关系不存在"
        )
    
    await db.delete(link_ad)
    await db.commit()
