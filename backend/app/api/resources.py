"""
资源管理 API
资源上传、列表、删除等功能
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
import os
import aiofiles

from app.database import get_db
from app.models import InviteLink, Resource, MediaFile
from app.api.auth import get_current_admin
from app.config import settings


router = APIRouter()


# ---------- Schema ----------

class ResourceCreate(BaseModel):
    """创建资源请求"""
    invite_link_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    media_type: str = "photo"  # photo/video/media_group
    is_cover: bool = False


class ResourceUpdate(BaseModel):
    """更新资源请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_cover: Optional[bool] = None


class MediaFileResponse(BaseModel):
    """媒体文件响应"""
    id: int
    file_type: str
    telegram_file_id: str
    position: int
    
    class Config:
        from_attributes = True


class ResourceResponse(BaseModel):
    """资源响应"""
    id: int
    invite_link_id: int
    title: Optional[str]
    description: Optional[str]
    media_type: str
    display_order: int
    is_cover: bool
    media_files: List[MediaFileResponse] = []
    
    class Config:
        from_attributes = True


# ---------- API ----------

@router.get("", response_model=List[ResourceResponse])
async def list_resources(
    invite_link_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取资源列表"""
    query = select(Resource).options(selectinload(Resource.media_files))
    
    if invite_link_id:
        query = query.where(Resource.invite_link_id == invite_link_id)
    
    query = query.order_by(Resource.display_order)
    
    result = await db.execute(query)
    resources = result.scalars().all()
    
    return resources


@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    data: ResourceCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """创建资源"""
    # 检查邀请链接是否存在
    link_result = await db.execute(
        select(InviteLink).where(InviteLink.id == data.invite_link_id)
    )
    if not link_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请链接不存在"
        )
    
    # 如果设置为封面,取消其他封面
    if data.is_cover:
        existing_covers = await db.execute(
            select(Resource).where(
                Resource.invite_link_id == data.invite_link_id,
                Resource.is_cover == True
            )
        )
        for cover in existing_covers.scalars():
            cover.is_cover = False
    
    # 获取最大排序值
    max_order_result = await db.execute(
        select(Resource.display_order)
        .where(Resource.invite_link_id == data.invite_link_id)
        .order_by(Resource.display_order.desc())
        .limit(1)
    )
    max_order = max_order_result.scalar() or 0
    
    # 创建资源
    resource = Resource(
        invite_link_id=data.invite_link_id,
        title=data.title,
        description=data.description,
        media_type=data.media_type,
        is_cover=data.is_cover,
        display_order=max_order + 1,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    
    return resource


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取单个资源"""
    result = await db.execute(
        select(Resource)
        .options(selectinload(Resource.media_files))
        .where(Resource.id == resource_id)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在"
        )
    
    return resource


@router.patch("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: int,
    data: ResourceUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """更新资源"""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在"
        )
    
    if data.title is not None:
        resource.title = data.title
    if data.description is not None:
        resource.description = data.description
    if data.display_order is not None:
        resource.display_order = data.display_order
    if data.is_cover is not None:
        if data.is_cover:
            # 取消其他封面
            existing_covers = await db.execute(
                select(Resource).where(
                    Resource.invite_link_id == resource.invite_link_id,
                    Resource.is_cover == True,
                    Resource.id != resource_id
                )
            )
            for cover in existing_covers.scalars():
                cover.is_cover = False
        resource.is_cover = data.is_cover
    
    await db.commit()
    await db.refresh(resource)
    
    return resource


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """删除资源"""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在"
        )
    
    await db.delete(resource)
    await db.commit()


@router.post("/{resource_id}/media", response_model=MediaFileResponse)
async def add_media_file(
    resource_id: int,
    telegram_file_id: str = Form(...),
    file_type: str = Form(...),  # photo/video
    position: int = Form(0),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """添加媒体文件到资源"""
    # 检查资源是否存在
    resource_result = await db.execute(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = resource_result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在"
        )
    
    # 创建媒体文件记录
    media_file = MediaFile(
        resource_id=resource_id,
        file_type=file_type,
        telegram_file_id=telegram_file_id,
        position=position,
    )
    db.add(media_file)
    await db.commit()
    await db.refresh(media_file)
    
    return media_file


@router.post("/{resource_id}/set-cover", response_model=ResourceResponse)
async def set_as_cover(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """设置资源为封面"""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在"
        )
    
    # 取消其他封面
    existing_covers = await db.execute(
        select(Resource).where(
            Resource.invite_link_id == resource.invite_link_id,
            Resource.is_cover == True
        )
    )
    for cover in existing_covers.scalars():
        cover.is_cover = False
    
    # 设置当前资源为封面
    resource.is_cover = True
    
    await db.commit()
    await db.refresh(resource)
    
    return resource


class ResourceReorderRequest(BaseModel):
    """资源重排序请求"""
    resource_ids: List[int]


@router.patch("/reorder", status_code=status.HTTP_200_OK)
async def reorder_resources(
    data: ResourceReorderRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """重新排序资源"""
    for index, resource_id in enumerate(data.resource_ids):
        result = await db.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        resource = result.scalar_one_or_none()
        if resource:
            resource.display_order = index + 1
    
    await db.commit()
    return {"message": "排序已更新", "count": len(data.resource_ids)}
