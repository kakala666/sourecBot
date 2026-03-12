"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aiogram import Bot

from app.config import settings
from app.database import init_db, close_db
from app.api import router as api_router
from app.services.broadcast import BroadcastService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    await init_db()
    # 创建 Bot 实例供广播服务使用
    bot = Bot(token=settings.BOT_TOKEN)
    app.state.broadcast_service = BroadcastService(bot)
    yield
    # 关闭时
    await bot.session.close()
    await close_db()


# 创建 FastAPI 应用
app = FastAPI(
    title="SourceBot API",
    description="Telegram 邀请链接追踪机器人后台 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "SourceBot API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}
