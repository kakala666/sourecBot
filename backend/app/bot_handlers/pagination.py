"""
翻页处理器
处理用户翻页、广告展示和倒计时
"""
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func

from app.database import get_db_context
from app.models import User, UserSession, InviteLink, Resource, MediaFile, Sponsor, AdGroup, InviteLinkAdGroup, Statistics
from app.config import settings


router = Router()


# 等待时间配置 (秒)
WAIT_TIMES = [2, 3, 4, 5, 5, 5, 5]
PREVIEW_LIMIT = 5


def get_wait_time(wait_count: int) -> int:
    """获取等待时间"""
    if wait_count < len(WAIT_TIMES):
        return WAIT_TIMES[wait_count]
    return WAIT_TIMES[-1]


@router.callback_query(F.data == "next_page")
async def handle_next_page(callback: CallbackQuery, bot: Bot):
    """处理翻页请求"""
    user_id = callback.from_user.id
    
    async with get_db_context() as db:
        # 获取用户会话
        session_result = await db.execute(
            select(UserSession).where(UserSession.user_id == user_id)
        )
        session = session_result.scalar_one_or_none()
        
        if not session or not session.invite_code:
            await callback.answer("会话已过期,请重新开始")
            return
        
        # 获取邀请链接
        link_result = await db.execute(
            select(InviteLink).where(InviteLink.code == session.invite_code)
        )
        invite_link = link_result.scalar_one_or_none()
        
        if not invite_link:
            await callback.answer("邀请链接不存在")
            return
        
        # 获取该链接的所有非封面资源
        resources_result = await db.execute(
            select(Resource)
            .where(Resource.invite_link_id == invite_link.id, Resource.is_cover == False)
            .order_by(Resource.display_order)
        )
        resources = resources_result.scalars().all()
        
        current_page = session.current_page
        total_resources = len(resources)
        
        # 检查是否需要显示预览结束
        if current_page >= PREVIEW_LIMIT or (current_page >= total_resources and total_resources > 0):
            await send_preview_end(callback.message, db, user_id, session.invite_code)
            session.current_page = 0
            session.wait_count = 0
            await db.commit()
            await callback.answer()
            return
        
        # 如果资源已播放完但不足5个
        if current_page >= total_resources:
            await send_preview_end(callback.message, db, user_id, session.invite_code)
            session.current_page = 0
            session.wait_count = 0
            await db.commit()
            await callback.answer()
            return
        
        # 发送广告
        await send_sponsor_ad(callback.message, db, invite_link.id, session.current_ad_index, user_id, session.invite_code)
        
        # 计算等待时间
        wait_time = get_wait_time(session.wait_count)
        
        # 发送倒计时消息
        loading_msg = await callback.message.answer(
            f"⏳ 正在加载下一页内容,请稍候 {wait_time} 秒..."
        )
        
        # 倒计时
        for remaining in range(wait_time - 1, 0, -1):
            await asyncio.sleep(1)
            try:
                await loading_msg.edit_text(f"⏳ {remaining} 秒后自动播放...")
            except Exception:
                pass
        
        await asyncio.sleep(1)
        
        # 删除倒计时消息
        try:
            await loading_msg.delete()
        except Exception:
            pass
        
        # 发送下一页资源
        resource = resources[current_page]
        media_result = await db.execute(
            select(MediaFile)
            .where(MediaFile.resource_id == resource.id)
            .order_by(MediaFile.position)
        )
        media_files = media_result.scalars().all()
        
        if media_files:
            # 更新会话
            session.current_page = current_page + 1
            session.wait_count = session.wait_count + 1
            session.current_ad_index = (session.current_ad_index + 1)
            
            # 记录统计
            stat = Statistics(
                event_type="page_view",
                user_id=user_id,
                invite_code=session.invite_code,
                resource_id=resource.id,
                page_number=current_page + 1,
            )
            db.add(stat)
            await db.commit()
            
            # 检查下一页是否是最后一页
            next_page = current_page + 1
            is_last = (next_page >= PREVIEW_LIMIT) or (next_page >= total_resources)
            
            await send_resource(callback.message, resource, media_files, is_last)
        
        await callback.answer()


async def send_resource(message, resource: Resource, media_files: list[MediaFile], is_last: bool = False):
    """发送资源"""
    button_text = "下一页 👉" if not is_last else "下一页 👉"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, callback_data="next_page")]
    ])
    
    # 构建 caption: 标题 + 描述
    caption = ""
    if resource.title:
        caption += f"<b>{resource.title}</b>"
    if resource.description:
        if caption:
            caption += "\n\n"
        caption += resource.description
    
    if len(media_files) == 1:
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
            )
    else:
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
                ))
        
        await message.answer_media_group(media=media_group)
        await message.answer("👇 点击继续浏览", reply_markup=keyboard)


async def send_sponsor_ad(message, db, invite_link_id: int, ad_index: int, user_id: int, invite_code: str):
    """发送赞助商广告"""
    # 获取该邀请链接绑定的广告组
    ad_groups_result = await db.execute(
        select(AdGroup)
        .join(InviteLinkAdGroup)
        .where(InviteLinkAdGroup.invite_link_id == invite_link_id)
    )
    ad_groups = ad_groups_result.scalars().all()
    
    if not ad_groups:
        return
    
    # 获取所有广告
    ad_group_ids = [ag.id for ag in ad_groups]
    sponsors_result = await db.execute(
        select(Sponsor)
        .where(Sponsor.ad_group_id.in_(ad_group_ids), Sponsor.is_active == True)
        .order_by(Sponsor.display_order)
    )
    sponsors = sponsors_result.scalars().all()
    
    if not sponsors:
        return
    
    # 轮播选择广告
    sponsor = sponsors[ad_index % len(sponsors)]
    
    # 构建广告内容
    ad_text = f"🎯 <b>{sponsor.title}</b>"
    if sponsor.description:
        ad_text += f"\n\n{sponsor.description}"
    
    # 构建键盘 (先记录点击再跳转)
    keyboard = None
    if sponsor.button_text and sponsor.button_url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=sponsor.button_text,
                callback_data=f"ad_click:{sponsor.id}"
            )]
        ])
    
    # 发送广告
    if sponsor.telegram_file_id:
        if sponsor.media_type == "photo":
            await message.answer_photo(
                photo=sponsor.telegram_file_id,
                caption=ad_text,
                reply_markup=keyboard,
            )
        else:
            await message.answer_video(
                video=sponsor.telegram_file_id,
                caption=ad_text,
                reply_markup=keyboard,
            )
    else:
        await message.answer(ad_text, reply_markup=keyboard)
    
    # 记录广告展示
    stat = Statistics(
        event_type="ad_view",
        user_id=user_id,
        invite_code=invite_code,
        sponsor_id=sponsor.id,
    )
    db.add(stat)


async def send_preview_end(message, db, user_id: int, invite_code: str):
    """发送预览结束消息"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 进入官方平台", url="https://example.com")]  # TODO: 配置跳转链接
    ])
    
    await message.answer(
        "🎬 <b>预览结束</b>\n\n"
        "感谢观看!更多精彩内容请进入官方平台。",
        reply_markup=keyboard,
    )
    
    # 记录统计
    stat = Statistics(
        event_type="preview_end",
        user_id=user_id,
        invite_code=invite_code,
    )
    db.add(stat)


@router.callback_query(F.data.startswith("ad_click:"))
async def handle_ad_click(callback: CallbackQuery):
    """处理广告点击"""
    sponsor_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    async with get_db_context() as db:
        # 获取广告
        sponsor_result = await db.execute(
            select(Sponsor).where(Sponsor.id == sponsor_id)
        )
        sponsor = sponsor_result.scalar_one_or_none()
        
        if not sponsor or not sponsor.button_url:
            await callback.answer("广告已失效")
            return
        
        # 获取用户会话的邀请码
        session_result = await db.execute(
            select(UserSession).where(UserSession.user_id == user_id)
        )
        session = session_result.scalar_one_or_none()
        invite_code = session.invite_code if session else None
        
        # 记录点击
        stat = Statistics(
            event_type="ad_click",
            user_id=user_id,
            invite_code=invite_code,
            sponsor_id=sponsor_id,
        )
        db.add(stat)
        await db.commit()
        
        # 发送跳转链接
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 打开链接", url=sponsor.button_url)]
        ])
        
        await callback.message.answer(
            f"🔗 点击下方按钮访问:\n{sponsor.button_url}",
            reply_markup=keyboard,
        )
        
        await callback.answer("正在跳转...")
