"""
客服群处理器
处理转发消息识别和用户来源查询
"""
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.database import get_db_context
from app.models import User, InviteLink, Statistics
from app.config import settings


router = Router()


# 只在客服群内响应
router.message.filter(F.chat.id == settings.SERVICE_GROUP_ID)


@router.message(F.forward_from)
async def handle_forwarded_message(message: Message):
    """处理转发消息,自动识别用户来源"""
    # 获取原始发送者
    original_user = message.forward_from
    user_id = original_user.id
    
    await query_and_reply_user_info(message, user_id, original_user)


@router.message(F.forward_sender_name)
async def handle_forwarded_message_hidden(message: Message):
    """处理设置了隐私保护的转发消息"""
    sender_name = message.forward_sender_name
    
    await message.reply(
        f"⚠️ 用户设置了隐私保护\n\n"
        f"转发显示名称: {sender_name}\n\n"
        f"无法自动识别用户,请使用命令手动查询:\n"
        f"/check <Telegram ID>"
    )


@router.message(Command("check"))
async def handle_check_command(message: Message):
    """手动查询用户信息"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply(
            "❌ 请指定用户 ID\n\n"
            "用法: /check <Telegram ID>"
        )
        return
    
    try:
        user_id = int(args[1].strip())
    except ValueError:
        await message.reply("❌ 无效的用户 ID")
        return
    
    await query_and_reply_user_info(message, user_id, None)


async def query_and_reply_user_info(message: Message, user_id: int, original_user):
    """查询用户信息并回复"""
    async with get_db_context() as db:
        # 查询用户
        user_result = await db.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            # 用户未使用过 Bot
            name = "未知"
            if original_user:
                name = f"{original_user.first_name or ''} {original_user.last_name or ''}".strip()
                name = name or original_user.username or f"用户{user_id}"
            
            reply_text = f"""
❌ <b>用户未使用过本 Bot</b>

📱 ID:
<code>{user_id}</code>

👤 姓名:
<code>{name}</code>
            """
            await message.reply(reply_text.strip())
            return
        
        # 获取来源名称
        source_name = "未知来源"
        if user.invite_code:
            link_result = await db.execute(
                select(InviteLink).where(InviteLink.code == user.invite_code)
            )
            invite_link = link_result.scalar_one_or_none()
            if invite_link:
                source_name = invite_link.name
        
        # 格式化日期
        first_seen = user.first_seen.strftime('%Y-%m-%d') if user.first_seen else "未知"
        last_active = user.last_active.strftime('%Y-%m-%d %H:%M') if user.last_active else "未知"
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 生成备注
        full_name = user.full_name
        remark = f"{full_name} {today}【{source_name}】"
        username_display = f"@{user.username}" if user.username else "无"
        
        # 构建回复消息 - 每行一个字段,都可复制
        reply_text = f"""
👤 <b>用户信息</b>
━━━━━━━━━━━━━━━━

📱 ID:
<code>{user.telegram_id}</code>

👤 姓名:
<code>{full_name}</code>

🔗 用户名:
<code>{username_display}</code>

━━━━━━━━━━━━━━━━
🎯 <b>来源信息</b>

📍 来源:
<code>{source_name}</code>

📅 首次使用:
<code>{first_seen}</code>

⏰ 最后活跃:
<code>{last_active}</code>

━━━━━━━━━━━━━━━━
📋 <b>客服备注</b>
<code>{remark}</code>
        """
        
        # 添加按钮
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📊 查看详细统计",
                callback_data=f"user_stats:{user_id}"
            )]
        ])
        
        await message.reply(reply_text.strip(), reply_markup=keyboard)


@router.callback_query(F.data.startswith("user_stats:"))
async def handle_user_stats(callback):
    """查看用户详细统计"""
    user_id = int(callback.data.split(":")[1])
    
    async with get_db_context() as db:
        from sqlalchemy import func, and_
        
        # 获取用户
        user_result = await db.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("用户不存在")
            return
        
        # 浏览页数
        page_views_result = await db.execute(
            select(func.count())
            .select_from(Statistics)
            .where(and_(
                Statistics.user_id == user_id,
                Statistics.event_type == "page_view"
            ))
        )
        page_views = page_views_result.scalar() or 0
        
        # 广告点击次数
        ad_clicks_result = await db.execute(
            select(func.count())
            .select_from(Statistics)
            .where(and_(
                Statistics.user_id == user_id,
                Statistics.event_type == "ad_click"
            ))
        )
        ad_clicks = ad_clicks_result.scalar() or 0
        
        # 是否完成预览
        preview_end_result = await db.execute(
            select(func.count())
            .select_from(Statistics)
            .where(and_(
                Statistics.user_id == user_id,
                Statistics.event_type == "preview_end"
            ))
        )
        preview_end = preview_end_result.scalar() or 0
        
        stats_text = f"""
📊 <b>用户详细统计</b>

👤 用户: {user.full_name}
📱 ID: {user.telegram_id}

━━━━━━━━━━━━━━━━
📖 浏览页数: {page_views}
👆 广告点击: {ad_clicks}
✅ 完成预览: {"是" if preview_end > 0 else "否"}
        """
        
        await callback.message.answer(stats_text.strip())
        await callback.answer()
