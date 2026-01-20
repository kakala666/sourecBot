"""
文件上传 API
处理文件上传请求
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models import Resource, MediaFile, InviteLink
from app.api.auth import get_current_admin
from app.services.upload import get_upload_service
from app.config import settings


router = APIRouter()


class UploadResponse(BaseModel):
    """上传响应"""
    file_id: str
    file_type: str
    file_size: int
    resource_id: Optional[int] = None
    media_file_id: Optional[int] = None


@router.post("/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    invite_link_id: int = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_cover: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """
    上传单个文件
    
    - 自动检测文件类型 (photo/video)
    - 上传到 Telegram 私有频道获取 file_id
    - 创建资源和媒体文件记录
    """
    # 检查邀请链接是否存在
    from sqlalchemy import select
    link_result = await db.execute(
        select(InviteLink).where(InviteLink.id == invite_link_id)
    )
    if not link_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="邀请链接不存在")
    
    # 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)
    
    # 确定文件类型
    content_type = file.content_type or ""
    if content_type.startswith("image/"):
        file_type = "photo"
        max_size = settings.MAX_IMAGE_SIZE
    elif content_type.startswith("video/"):
        file_type = "video"
        max_size = settings.MAX_VIDEO_SIZE
    else:
        raise HTTPException(status_code=400, detail="不支持的文件类型,仅支持图片和视频")
    
    # 验证文件大小
    if file_size > max_size:
        max_mb = max_size / 1024 / 1024
        raise HTTPException(status_code=400, detail=f"文件过大,{file_type} 最大 {max_mb:.0f}MB")
    
    # 生成唯一文件名
    ext = file.filename.split(".")[-1] if "." in file.filename else ""
    unique_filename = f"{uuid.uuid4()}.{ext}"
    
    # 上传到 Telegram
    upload_service = get_upload_service()
    try:
        telegram_file_id = await upload_service.upload_and_get_file_id(
            file_content=file_content,
            filename=unique_filename,
            file_type=file_type,
            caption=title,
            delete_after=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传到 Telegram 失败: {str(e)}")
    
    # 创建资源记录
    # 获取最大排序值
    from sqlalchemy import func
    max_order_result = await db.execute(
        select(func.max(Resource.display_order))
        .where(Resource.invite_link_id == invite_link_id)
    )
    max_order = max_order_result.scalar() or 0
    
    # 如果设置为封面,取消其他封面
    if is_cover:
        existing_covers = await db.execute(
            select(Resource).where(
                Resource.invite_link_id == invite_link_id,
                Resource.is_cover == True
            )
        )
        for cover in existing_covers.scalars():
            cover.is_cover = False
    
    resource = Resource(
        invite_link_id=invite_link_id,
        title=title,
        description=description,
        media_type=file_type,
        is_cover=is_cover,
        display_order=max_order + 1,
    )
    db.add(resource)
    await db.flush()
    
    # 创建媒体文件记录
    media_file = MediaFile(
        resource_id=resource.id,
        file_type=file_type,
        telegram_file_id=telegram_file_id,
        file_size=file_size,
        position=0,
    )
    db.add(media_file)
    await db.commit()
    
    return UploadResponse(
        file_id=telegram_file_id,
        file_type=file_type,
        file_size=file_size,
        resource_id=resource.id,
        media_file_id=media_file.id,
    )


@router.post("/media-group", response_model=list[UploadResponse])
async def upload_media_group(
    files: list[UploadFile] = File(...),
    invite_link_id: int = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """
    上传媒体组 (2-10 个文件)
    
    - 创建一个资源,包含多个媒体文件
    - 第一个文件的 caption 包含标题和描述
    """
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="媒体组至少需要 2 个文件")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="媒体组最多 10 个文件")
    
    # 检查邀请链接
    from sqlalchemy import select
    link_result = await db.execute(
        select(InviteLink).where(InviteLink.id == invite_link_id)
    )
    if not link_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="邀请链接不存在")
    
    upload_service = get_upload_service()
    uploaded_files = []
    
    # 获取最大排序值
    from sqlalchemy import func
    max_order_result = await db.execute(
        select(func.max(Resource.display_order))
        .where(Resource.invite_link_id == invite_link_id)
    )
    max_order = max_order_result.scalar() or 0
    
    # 创建资源
    resource = Resource(
        invite_link_id=invite_link_id,
        title=title,
        description=description,
        media_type="media_group",
        is_cover=False,
        display_order=max_order + 1,
    )
    db.add(resource)
    await db.flush()
    
    # 上传每个文件
    for i, file in enumerate(files):
        file_content = await file.read()
        file_size = len(file_content)
        
        content_type = file.content_type or ""
        if content_type.startswith("image/"):
            file_type = "photo"
            max_size = settings.MAX_IMAGE_SIZE
        elif content_type.startswith("video/"):
            file_type = "video"
            max_size = settings.MAX_VIDEO_SIZE
        else:
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 类型不支持")
        
        if file_size > max_size:
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 过大")
        
        ext = file.filename.split(".")[-1] if "." in file.filename else ""
        unique_filename = f"{uuid.uuid4()}.{ext}"
        
        try:
            telegram_file_id = await upload_service.upload_and_get_file_id(
                file_content=file_content,
                filename=unique_filename,
                file_type=file_type,
                caption=title if i == 0 else None,
                delete_after=True,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
        
        # 创建媒体文件记录
        media_file = MediaFile(
            resource_id=resource.id,
            file_type=file_type,
            telegram_file_id=telegram_file_id,
            file_size=file_size,
            position=i,
        )
        db.add(media_file)
        
        uploaded_files.append(UploadResponse(
            file_id=telegram_file_id,
            file_type=file_type,
            file_size=file_size,
            resource_id=resource.id,
            media_file_id=None,  # 稍后更新
        ))
    
    await db.commit()
    
    return uploaded_files
