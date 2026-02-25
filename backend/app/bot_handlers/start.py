"""
/start 命令处理器
处理 Deep Link 邀请链接
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.database import get_db_context
from app.models import User, UserSession, InviteLink, Resource, MediaFile, Statistics
from app.models.invite_link_button import InviteLinkButton


router = Router()


@router.message(CommandStart(deep_link=True))
async def handle_start_with_deep_link(message: Message, command: CommandObject):
    """处理带参数的 /start 命令 (Deep Link)"""
    invite_code = command.args
    user_id = message.from_user.id
    
    async with get_db_context() as db:
        # 查询邀请链接
        result = await db.execute(
            select(InviteLink).where(InviteLink.code == invite_code, InviteLink.is_active == True)
        )
        invite_link = result.scalar_one_or_none()
        
        if not invite_link:
            await message.answer("❌ 无效的邀请链接")
            return
        
        # 查询或创建用户
        user_result = await db.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            # 新用户,创建记录
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                invite_code=invite_code,
            )
            db.add(user)
            await db.flush()
            
            # 记录统计
            stat = Statistics(
                event_type="user_start",
                user_id=user_id,
                invite_code=invite_code,
            )
            db.add(stat)
        elif user.invite_code != invite_code:
            user.invite_code = invite_code
        
        # 创建或更新用户会话
        session_result = await db.execute(
            select(UserSession).where(UserSession.user_id == user_id)
        )
        session = session_result.scalar_one_or_none()
        
        if session:
            session.invite_code = invite_code
            session.current_page = 0
            session.wait_count = 0
            session.current_ad_index = 0
        else:
            session = UserSession(
                user_id=user_id,
                invite_code=invite_code,
                current_page=0,
                wait_count=0,
                current_ad_index=0,
            )
            db.add(session)
        
        await db.commit()
        
        # 查询封面资源
        cover_result = await db.execute(
            select(Resource)
            .where(Resource.invite_link_id == invite_link.id, Resource.is_cover == True)
            .limit(1)
        )
        cover = cover_result.scalar_one_or_none()
        
        if cover:
            # 获取封面的媒体文件
            media_result = await db.execute(
                select(MediaFile)
                .where(MediaFile.resource_id == cover.id)
                .order_by(MediaFile.position)
            )
            media_files = media_result.scalars().all()
            
            if media_files:
                # 查询自定义按钮
                buttons_result = await db.execute(
                    select(InviteLinkButton)
                    .where(InviteLinkButton.invite_link_id == invite_link.id, InviteLinkButton.is_active == True)
                    .order_by(InviteLinkButton.display_order)
                )
                custom_buttons = buttons_result.scalars().all()
                
                # 发送封面
                await send_resource(message, cover, media_files, custom_buttons)
            else:
                await message.answer("⚠️ 封面资源配置错误")
        else:
            await message.answer(
                "👋 欢迎使用!\n\n"
                "暂无可用内容,请稍后再试。"
            )


@router.message(CommandStart())
async def handle_start_without_deep_link(message: Message):
    """处理不带参数的 /start 命令"""
    user_id = message.from_user.id
    
    async with get_db_context() as db:
        # 检查是否为老用户
        user_result = await db.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            # 老用户,正常响应
            await message.answer(
                f"👋 欢迎回来,{user.full_name}!\n\n"
                "请通过邀请链接访问更多内容。"
            )
        else:
            # 新用户,不响应 (按需求规格)
            pass


async def send_resource(message: Message, resource: Resource, media_files: list[MediaFile], custom_buttons: list = None):
    """发送资源
    
    Args:
        message: Telegram 消息对象
        resource: 资源对象
        media_files: 媒体文件列表
        custom_buttons: 自定义按钮列表 (InviteLinkButton 对象)
    """
    # 构建键盘按钮
    keyboard_buttons = []
    
    # 1. 固定的下一页按钮
    keyboard_buttons.append([InlineKeyboardButton(text="下一页 👉", callback_data="next_page")])
    
    # 2. 添加自定义按钮 (直接跳转 URL)
    if custom_buttons:
        for btn in custom_buttons:
            if btn.is_active:
                keyboard_buttons.append([InlineKeyboardButton(text=btn.text, url=btn.url)])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # 准备 caption: 标题 + 描述
    caption = ""
    if resource.title:
        caption += f"<b>{resource.title}</b>"
    if resource.description:
        if caption:
            caption += "\n\n"
        caption += resource.description
    
    if len(media_files) == 1:
        # 单个媒体
        media = media_files[0]
        if media.file_type == "photo":
            await message.answer_photo(
                photo=media.telegram_file_id,
                caption=caption or None,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await message.answer_video(
                video=media.telegram_file_id,
                caption=caption or None,
                parse_mode="HTML",
                reply_markup=keyboard,
                supports_streaming=True,
            )
    else:
        # 媒体组
        from aiogram.types import InputMediaPhoto, InputMediaVideo
        
        media_group = []
        for i, media in enumerate(media_files):
            if media.file_type == "photo":
                media_group.append(InputMediaPhoto(
                    media=media.telegram_file_id,
                    caption=caption if i == 0 else None,
                    parse_mode="HTML" if i == 0 else None,
                ))
            else:
                media_group.append(InputMediaVideo(
                    media=media.telegram_file_id,
                    caption=caption if i == 0 else None,
                    parse_mode="HTML" if i == 0 else None,
                    supports_streaming=True,
                ))
        
        await message.answer_media_group(media=media_group)
        
        # 单独发送按钮
        await message.answer(
            "👇 点击继续浏览",
            reply_markup=keyboard,
        )
