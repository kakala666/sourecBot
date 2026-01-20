"""
统计数据 API
统计查询和报表
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import InviteLink, User, Statistics, Sponsor
from app.api.auth import get_current_admin


router = APIRouter()


# ---------- Schema ----------

class OverviewStats(BaseModel):
    """概览统计"""
    total_users: int
    users_today: int
    total_views: int
    views_today: int
    active_links: int
    total_resources: int


class LinkStats(BaseModel):
    """邀请链接统计"""
    link_id: int
    link_name: str
    link_code: str
    users_7d: int
    users_30d: int
    users_total: int
    views_7d: int
    views_30d: int
    ad_views_7d: int
    ad_clicks_7d: int
    ctr: float


class AdStats(BaseModel):
    """广告统计"""
    sponsor_id: int
    sponsor_title: str
    views_total: int
    clicks_total: int
    ctr: float


class DailyStats(BaseModel):
    """每日统计"""
    date: str
    users: int
    views: int
    ad_clicks: int


# ---------- API ----------

@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取概览统计"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 总用户数
    total_users_result = await db.execute(
        select(func.count()).select_from(User)
    )
    total_users = total_users_result.scalar() or 0
    
    # 今日新增用户
    users_today_result = await db.execute(
        select(func.count()).select_from(User)
        .where(User.first_seen >= today_start)
    )
    users_today = users_today_result.scalar() or 0
    
    # 总浏览量
    total_views_result = await db.execute(
        select(func.count()).select_from(Statistics)
        .where(Statistics.event_type == "page_view")
    )
    total_views = total_views_result.scalar() or 0
    
    # 今日浏览量
    views_today_result = await db.execute(
        select(func.count()).select_from(Statistics)
        .where(and_(
            Statistics.event_type == "page_view",
            Statistics.created_at >= today_start
        ))
    )
    views_today = views_today_result.scalar() or 0
    
    # 活跃链接数
    active_links_result = await db.execute(
        select(func.count()).select_from(InviteLink)
        .where(InviteLink.is_active == True)
    )
    active_links = active_links_result.scalar() or 0
    
    # 总资源数
    from app.models import Resource
    total_resources_result = await db.execute(
        select(func.count()).select_from(Resource)
    )
    total_resources = total_resources_result.scalar() or 0
    
    return OverviewStats(
        total_users=total_users,
        users_today=users_today,
        total_views=total_views,
        views_today=views_today,
        active_links=active_links,
        total_resources=total_resources,
    )


@router.get("/links", response_model=List[LinkStats])
async def get_link_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取所有邀请链接统计"""
    now = datetime.utcnow()
    date_7d = now - timedelta(days=7)
    date_30d = now - timedelta(days=30)
    
    # 获取所有邀请链接
    links_result = await db.execute(select(InviteLink))
    links = links_result.scalars().all()
    
    stats = []
    for link in links:
        # 用户统计
        users_7d_result = await db.execute(
            select(func.count()).select_from(User)
            .where(and_(User.invite_code == link.code, User.first_seen >= date_7d))
        )
        users_7d = users_7d_result.scalar() or 0
        
        users_30d_result = await db.execute(
            select(func.count()).select_from(User)
            .where(and_(User.invite_code == link.code, User.first_seen >= date_30d))
        )
        users_30d = users_30d_result.scalar() or 0
        
        users_total_result = await db.execute(
            select(func.count()).select_from(User)
            .where(User.invite_code == link.code)
        )
        users_total = users_total_result.scalar() or 0
        
        # 浏览量统计
        views_7d_result = await db.execute(
            select(func.count()).select_from(Statistics)
            .where(and_(
                Statistics.invite_code == link.code,
                Statistics.event_type == "page_view",
                Statistics.created_at >= date_7d
            ))
        )
        views_7d = views_7d_result.scalar() or 0
        
        views_30d_result = await db.execute(
            select(func.count()).select_from(Statistics)
            .where(and_(
                Statistics.invite_code == link.code,
                Statistics.event_type == "page_view",
                Statistics.created_at >= date_30d
            ))
        )
        views_30d = views_30d_result.scalar() or 0
        
        # 广告统计
        ad_views_7d_result = await db.execute(
            select(func.count()).select_from(Statistics)
            .where(and_(
                Statistics.invite_code == link.code,
                Statistics.event_type == "ad_view",
                Statistics.created_at >= date_7d
            ))
        )
        ad_views_7d = ad_views_7d_result.scalar() or 0
        
        ad_clicks_7d_result = await db.execute(
            select(func.count()).select_from(Statistics)
            .where(and_(
                Statistics.invite_code == link.code,
                Statistics.event_type == "ad_click",
                Statistics.created_at >= date_7d
            ))
        )
        ad_clicks_7d = ad_clicks_7d_result.scalar() or 0
        
        ctr = (ad_clicks_7d / ad_views_7d * 100) if ad_views_7d > 0 else 0
        
        stats.append(LinkStats(
            link_id=link.id,
            link_name=link.name,
            link_code=link.code,
            users_7d=users_7d,
            users_30d=users_30d,
            users_total=users_total,
            views_7d=views_7d,
            views_30d=views_30d,
            ad_views_7d=ad_views_7d,
            ad_clicks_7d=ad_clicks_7d,
            ctr=round(ctr, 2),
        ))
    
    return stats


@router.get("/ads", response_model=List[AdStats])
async def get_ad_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取广告统计"""
    # 获取所有广告
    sponsors_result = await db.execute(select(Sponsor))
    sponsors = sponsors_result.scalars().all()
    
    stats = []
    for sponsor in sponsors:
        views_result = await db.execute(
            select(func.count()).select_from(Statistics)
            .where(and_(
                Statistics.sponsor_id == sponsor.id,
                Statistics.event_type == "ad_view"
            ))
        )
        views_total = views_result.scalar() or 0
        
        clicks_result = await db.execute(
            select(func.count()).select_from(Statistics)
            .where(and_(
                Statistics.sponsor_id == sponsor.id,
                Statistics.event_type == "ad_click"
            ))
        )
        clicks_total = clicks_result.scalar() or 0
        
        ctr = (clicks_total / views_total * 100) if views_total > 0 else 0
        
        stats.append(AdStats(
            sponsor_id=sponsor.id,
            sponsor_title=sponsor.title,
            views_total=views_total,
            clicks_total=clicks_total,
            ctr=round(ctr, 2),
        ))
    
    return stats


@router.get("/daily", response_model=List[DailyStats])
async def get_daily_stats(
    days: int = Query(default=7, ge=1, le=90),
    invite_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取每日统计数据"""
    now = datetime.utcnow()
    
    stats = []
    for i in range(days):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        # 用户数
        user_query = select(func.count()).select_from(User).where(and_(
            User.first_seen >= date_start,
            User.first_seen < date_end
        ))
        if invite_code:
            user_query = user_query.where(User.invite_code == invite_code)
        users_result = await db.execute(user_query)
        users = users_result.scalar() or 0
        
        # 浏览量
        views_query = select(func.count()).select_from(Statistics).where(and_(
            Statistics.event_type == "page_view",
            Statistics.created_at >= date_start,
            Statistics.created_at < date_end
        ))
        if invite_code:
            views_query = views_query.where(Statistics.invite_code == invite_code)
        views_result = await db.execute(views_query)
        views = views_result.scalar() or 0
        
        # 广告点击
        clicks_query = select(func.count()).select_from(Statistics).where(and_(
            Statistics.event_type == "ad_click",
            Statistics.created_at >= date_start,
            Statistics.created_at < date_end
        ))
        if invite_code:
            clicks_query = clicks_query.where(Statistics.invite_code == invite_code)
        clicks_result = await db.execute(clicks_query)
        ad_clicks = clicks_result.scalar() or 0
        
        stats.append(DailyStats(
            date=date_start.strftime('%Y-%m-%d'),
            users=users,
            views=views,
            ad_clicks=ad_clicks,
        ))
    
    return stats
