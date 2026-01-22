"""
频道资源采集处理器
监听绑定频道的消息，自动采集媒体资源
"""
import asyncio
import logging
from typing import Dict, List
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import InviteLink, Resource, MediaFile

logger = logging.getLogger(__name__)
router = Router()

# 媒体组缓存：media_group_id -> (消息列表, 邀请链接ID, 第一条消息时间)
media_group_cache: Dict[str, tuple[List[Message], int, float]] = {}
# 媒体组处理锁
media_group_locks: Dict[str, asyncio.Lock] = {}


async def get_invite_link_by_channel(channel_id: int) -> InviteLink | None:
    """根据频道ID获取绑定的邀请链接"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(InviteLink).where(
                InviteLink.source_channel_id == channel_id,
                InviteLink.auto_collect_enabled == True,
                InviteLink.is_active == True
            )
        )
        return result.scalar_one_or_none()


async def create_resource_from_message(
    session: AsyncSession,
    invite_link_id: int,
    messages: List[Message],
    media_type: str
):
    """从消息创建资源"""
    # 获取描述文本（从第一条消息的 caption 或 text）
    first_msg = messages[0]
    description = first_msg.caption or first_msg.text or None
    
    # 获取最大排序值
    from sqlalchemy import func
    max_order_result = await session.execute(
        select(func.max(Resource.display_order))
        .where(Resource.invite_link_id == invite_link_id)
    )
    max_order = max_order_result.scalar() or 0
    
    # 创建资源
    resource = Resource(
        invite_link_id=invite_link_id,
        title=None,  # 标题为空
        description=description,
        media_type=media_type,
        is_cover=False,
        display_order=max_order + 1,
    )
    session.add(resource)
    await session.flush()
    
    # 创建媒体文件
    for i, msg in enumerate(messages):
        file_id = None
        file_unique_id = None
        file_type = None
        
        if msg.photo:
            # 获取最大尺寸的图片
            photo = msg.photo[-1]
            file_id = photo.file_id
            file_unique_id = photo.file_unique_id
            file_type = "photo"
        elif msg.video:
            file_id = msg.video.file_id
            file_unique_id = msg.video.file_unique_id
            file_type = "video"
        elif msg.animation:
            file_id = msg.animation.file_id
            file_unique_id = msg.animation.file_unique_id
            file_type = "animation"
        elif msg.document:
            # 检查是否为图片或视频文档
            mime = msg.document.mime_type or ""
            if mime.startswith("image/"):
                file_id = msg.document.file_id
                file_unique_id = msg.document.file_unique_id
                file_type = "photo"
            elif mime.startswith("video/"):
                file_id = msg.document.file_id
                file_unique_id = msg.document.file_unique_id
                file_type = "video"
        
        if file_id and file_type:
            media_file = MediaFile(
                resource_id=resource.id,
                file_type=file_type,
                telegram_file_id=file_id,
                file_unique_id=file_unique_id,  # 保存 file_unique_id 用于备份
                source_channel_id=msg.chat.id if msg.chat else None,  # 保存来源频道
                source_message_id=msg.message_id,  # 保存来源消息 ID
                position=i,
            )
            session.add(media_file)
    
    await session.commit()
    logger.info(f"已采集资源: invite_link_id={invite_link_id}, type={media_type}, files={len(messages)}")
    return resource


async def process_media_group(media_group_id: str):
    """处理媒体组（延迟执行，等待所有消息收集完成）"""
    # 等待 1 秒让所有消息到达
    await asyncio.sleep(1.0)
    
    if media_group_id not in media_group_cache:
        return
    
    messages, invite_link_id, _ = media_group_cache.pop(media_group_id)
    if media_group_id in media_group_locks:
        del media_group_locks[media_group_id]
    
    if not messages:
        return
    
    # 按消息ID排序
    messages.sort(key=lambda m: m.message_id)
    
    async with AsyncSessionLocal() as session:
        await create_resource_from_message(
            session=session,
            invite_link_id=invite_link_id,
            messages=messages,
            media_type="media_group"
        )


@router.channel_post(F.photo | F.video | F.animation | F.document)
async def handle_channel_media(message: Message):
    """处理频道媒体消息"""
    if not message.chat:
        return
    
    channel_id = message.chat.id
    
    # 检查是否有绑定的邀请链接
    invite_link = await get_invite_link_by_channel(channel_id)
    if not invite_link:
        return
    
    logger.info(f"收到频道消息: channel={channel_id}, message_id={message.message_id}")
    
    # 检查是否为媒体组
    if message.media_group_id:
        media_group_id = message.media_group_id
        
        # 初始化锁
        if media_group_id not in media_group_locks:
            media_group_locks[media_group_id] = asyncio.Lock()
        
        async with media_group_locks[media_group_id]:
            if media_group_id not in media_group_cache:
                # 首次收到该媒体组的消息
                media_group_cache[media_group_id] = (
                    [message],
                    invite_link.id,
                    asyncio.get_event_loop().time()
                )
                # 启动延迟处理任务
                asyncio.create_task(process_media_group(media_group_id))
            else:
                # 追加消息到缓存
                messages, link_id, start_time = media_group_cache[media_group_id]
                messages.append(message)
                media_group_cache[media_group_id] = (messages, link_id, start_time)
    else:
        # 单个媒体文件，直接处理
        # 确定媒体类型
        if message.photo:
            media_type = "photo"
        elif message.video:
            media_type = "video"
        elif message.animation:
            media_type = "animation"
        else:
            media_type = "document"
        
        async with AsyncSessionLocal() as session:
            await create_resource_from_message(
                session=session,
                invite_link_id=invite_link.id,
                messages=[message],
                media_type=media_type
            )
