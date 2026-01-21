"""
Telegram Bot 入口
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config import settings
from app.database import init_db, close_db
from app.bot_handlers.start import router as start_router
from app.bot_handlers.pagination import router as pagination_router
from app.bot_handlers.stats_group import router as stats_router
from app.bot_handlers.service_group import router as service_router
from app.bot_handlers.channel_collector import router as channel_router


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    logger.info("正在启动 SourceBot...")
    
    # 初始化数据库
    await init_db()
    logger.info("数据库初始化完成")
    
    # 创建 Bot 实例
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # 创建调度器
    dp = Dispatcher()
    
    # 注册路由
    dp.include_router(start_router)
    dp.include_router(pagination_router)
    dp.include_router(stats_router)
    dp.include_router(service_router)
    dp.include_router(channel_router)
    
    # 启动轮询
    logger.info("Bot 启动成功,开始轮询...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await close_db()
        await bot.session.close()
        logger.info("Bot 已关闭")


if __name__ == "__main__":
    asyncio.run(main())
