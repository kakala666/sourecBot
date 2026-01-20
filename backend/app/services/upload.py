"""
文件上传服务
处理文件上传并转换为 Telegram file_id
"""
import os
import aiofiles
from pathlib import Path
from typing import Optional
from aiogram import Bot
from aiogram.types import FSInputFile

from app.config import settings


class FileUploadService:
    """文件上传服务"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_temp_file(self, file_content: bytes, filename: str) -> str:
        """保存临时文件"""
        file_path = self.upload_dir / filename
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        return str(file_path)
    
    async def upload_to_telegram(
        self, 
        file_path: str, 
        file_type: str,
        caption: Optional[str] = None
    ) -> str:
        """
        上传文件到 Telegram 私有频道获取 file_id
        
        Args:
            file_path: 本地文件路径
            file_type: 文件类型 (photo/video)
            caption: 可选的文件说明
        
        Returns:
            Telegram file_id
        """
        input_file = FSInputFile(file_path)
        
        if file_type == "photo":
            message = await self.bot.send_photo(
                chat_id=settings.STORAGE_CHANNEL_ID,
                photo=input_file,
                caption=caption,
            )
            file_id = message.photo[-1].file_id  # 获取最高分辨率的图片
        else:
            message = await self.bot.send_video(
                chat_id=settings.STORAGE_CHANNEL_ID,
                video=input_file,
                caption=caption,
            )
            file_id = message.video.file_id
        
        return file_id
    
    async def upload_and_get_file_id(
        self,
        file_content: bytes,
        filename: str,
        file_type: str,
        caption: Optional[str] = None,
        delete_after: bool = True,
    ) -> str:
        """
        保存文件并上传到 Telegram
        
        Args:
            file_content: 文件内容
            filename: 文件名
            file_type: 文件类型
            caption: 可选说明
            delete_after: 上传后是否删除本地文件
        
        Returns:
            Telegram file_id
        """
        # 保存临时文件
        file_path = await self.save_temp_file(file_content, filename)
        
        try:
            # 上传到 Telegram
            file_id = await self.upload_to_telegram(file_path, file_type, caption)
            return file_id
        finally:
            # 可选删除临时文件
            if delete_after and os.path.exists(file_path):
                os.remove(file_path)
    
    def get_file_size(self, file_content: bytes) -> int:
        """获取文件大小"""
        return len(file_content)
    
    def validate_file_size(self, file_content: bytes, file_type: str) -> bool:
        """验证文件大小"""
        size = self.get_file_size(file_content)
        if file_type == "photo":
            return size <= settings.MAX_IMAGE_SIZE
        else:
            return size <= settings.MAX_VIDEO_SIZE


# 全局 Bot 实例 (需要在启动时初始化)
_bot_instance: Optional[Bot] = None


def get_bot() -> Bot:
    """获取 Bot 实例"""
    global _bot_instance
    if _bot_instance is None:
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        _bot_instance = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    return _bot_instance


def get_upload_service() -> FileUploadService:
    """获取上传服务实例"""
    return FileUploadService(get_bot())
