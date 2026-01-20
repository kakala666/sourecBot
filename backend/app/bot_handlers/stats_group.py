"""
统计群处理器
处理统计查询命令
"""
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func, and_

from app.database import get_db_context
from app.models import InviteLink, User, Statistics
from app.config import settings


router = Router()


# 只在统计群内响应
router.message.filter(F.chat.id == settings.STATS_GROUP_ID)


@router.message(Command("query"))
async def handle_query_command(message: Message):
    """查询单个邀请链接的统计数据"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply(
            "❌ 请指定邀请链接名称\n\n"
            "用法: /query <链接名称>"
        )
        return
    
    link_name = args[1].strip()
    
    async with get_db_context() as db:
        # 查询邀请链接
        result = await db.execute(
            select(InviteLink).where(InviteLink.name == link_name)
        )
        invite_link = result.scalar_one_or_none()
        
        if not invite_link:
            await message.reply(f"❌ 未找到邀请链接: {link_name}")
            return
        
        # 获取统计数据
        stats = await get_link_statistics(db, invite_link.code)
        
        report = format_statistics_report(link_name, stats)
        await message.reply(report)


@router.message(Command("total"))
async def handle_total_command(message: Message):
    """查询所有邀请链接的汇总统计"""
    async with get_db_context() as db:
        # 获取所有邀请链接
        links_result = await db.execute(
            select(InviteLink).order_by(InviteLink.name)
        )
        links = links_result.scalars().all()
        
        if not links:
            await message.reply("📊 暂无邀请链接数据")
            return
        
        report_lines = ["📊 <b>总体统计报表</b>\n"]
        report_lines.append("━" * 20 + "\n")
        
        total_stats = {
            "users_7d": 0,
            "users_30d": 0,
            "views_7d": 0,
            "views_30d": 0,
            "ad_views_7d": 0,
            "ad_clicks_7d": 0,
        }
        
        for link in links:
            stats = await get_link_statistics(db, link.code)
            
            report_lines.append(f"\n📎 <b>{link.name}</b>")
            report_lines.append(f"  新用户(7天): {stats['users_7d']}")
            report_lines.append(f"  新用户(30天): {stats['users_30d']}")
            report_lines.append(f"  浏览量(7天): {stats['views_7d']}")
            
            # 累加总计
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)
        
        # 添加总计
        report_lines.append("\n" + "━" * 20)
        report_lines.append("\n📈 <b>总计</b>")
        report_lines.append(f"  新用户(7天): {total_stats['users_7d']}")
        report_lines.append(f"  新用户(30天): {total_stats['users_30d']}")
        report_lines.append(f"  总浏览量(7天): {total_stats['views_7d']}")
        
        if total_stats['ad_views_7d'] > 0:
            ctr = total_stats['ad_clicks_7d'] / total_stats['ad_views_7d'] * 100
            report_lines.append(f"  广告点击率: {ctr:.1f}%")
        
        await message.reply("\n".join(report_lines))


@router.message(Command("help"))
async def handle_help_command(message: Message):
    """显示帮助信息"""
    help_text = """
📖 <b>统计群命令帮助</b>

/query <名称> - 查询单个邀请链接统计
/total - 查询所有链接汇总统计
/help - 显示本帮助信息

<b>统计指标说明:</b>
• 新用户: 通过该链接首次使用 Bot 的用户数
• 浏览量: 翻页浏览次数
• 广告展示: 广告显示次数
• 广告点击: 用户点击广告次数
• 点击率: 点击数 / 展示数 × 100%
    """
    await message.reply(help_text)


async def get_link_statistics(db, invite_code: str) -> dict:
    """获取邀请链接的统计数据"""
    now = datetime.utcnow()
    date_7d = now - timedelta(days=7)
    date_30d = now - timedelta(days=30)
    
    # 新用户数 (7天)
    users_7d_result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(and_(
            User.invite_code == invite_code,
            User.first_seen >= date_7d
        ))
    )
    users_7d = users_7d_result.scalar() or 0
    
    # 新用户数 (30天)
    users_30d_result = await db.execute(
        select(func.count())
        .select_from(User)
        .where(and_(
            User.invite_code == invite_code,
            User.first_seen >= date_30d
        ))
    )
    users_30d = users_30d_result.scalar() or 0
    
    # 浏览量 (7天)
    views_7d_result = await db.execute(
        select(func.count())
        .select_from(Statistics)
        .where(and_(
            Statistics.invite_code == invite_code,
            Statistics.event_type == "page_view",
            Statistics.created_at >= date_7d
        ))
    )
    views_7d = views_7d_result.scalar() or 0
    
    # 浏览量 (30天)
    views_30d_result = await db.execute(
        select(func.count())
        .select_from(Statistics)
        .where(and_(
            Statistics.invite_code == invite_code,
            Statistics.event_type == "page_view",
            Statistics.created_at >= date_30d
        ))
    )
    views_30d = views_30d_result.scalar() or 0
    
    # 广告展示 (7天)
    ad_views_7d_result = await db.execute(
        select(func.count())
        .select_from(Statistics)
        .where(and_(
            Statistics.invite_code == invite_code,
            Statistics.event_type == "ad_view",
            Statistics.created_at >= date_7d
        ))
    )
    ad_views_7d = ad_views_7d_result.scalar() or 0
    
    # 广告点击 (7天)
    ad_clicks_7d_result = await db.execute(
        select(func.count())
        .select_from(Statistics)
        .where(and_(
            Statistics.invite_code == invite_code,
            Statistics.event_type == "ad_click",
            Statistics.created_at >= date_7d
        ))
    )
    ad_clicks_7d = ad_clicks_7d_result.scalar() or 0
    
    return {
        "users_7d": users_7d,
        "users_30d": users_30d,
        "views_7d": views_7d,
        "views_30d": views_30d,
        "ad_views_7d": ad_views_7d,
        "ad_clicks_7d": ad_clicks_7d,
    }


def format_statistics_report(link_name: str, stats: dict) -> str:
    """格式化统计报表"""
    ctr = 0
    if stats['ad_views_7d'] > 0:
        ctr = stats['ad_clicks_7d'] / stats['ad_views_7d'] * 100
    
    report = f"""
📊 <b>统计报表: {link_name}</b>

📅 <b>近 7 天</b>
━━━━━━━━━━━━━━━━
👥 新增用户: {stats['users_7d']}
👁 浏览量: {stats['views_7d']}
📢 广告展示: {stats['ad_views_7d']}
👆 广告点击: {stats['ad_clicks_7d']}
📈 点击率: {ctr:.1f}%

📅 <b>近 30 天</b>
━━━━━━━━━━━━━━━━
👥 新增用户: {stats['users_30d']}
👁 浏览量: {stats['views_30d']}
    """
    return report.strip()
