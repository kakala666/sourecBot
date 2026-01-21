"""
API 路由模块
"""
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.invite_links import router as invite_links_router
from app.api.resources import router as resources_router
from app.api.sponsors import router as sponsors_router
from app.api.statistics import router as statistics_router
from app.api.upload import router as upload_router
from app.api.config import router as config_router
from app.api.users import router as users_router

router = APIRouter()

# 注册子路由
router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(invite_links_router, prefix="/invite-links", tags=["邀请链接"])
router.include_router(resources_router, prefix="/resources", tags=["资源管理"])
router.include_router(sponsors_router, prefix="/sponsors", tags=["广告管理"])
router.include_router(statistics_router, prefix="/statistics", tags=["统计数据"])
router.include_router(upload_router, prefix="/upload", tags=["文件上传"])
router.include_router(config_router, prefix="/config", tags=["系统配置"])
router.include_router(users_router, prefix="/users", tags=["用户管理"])
