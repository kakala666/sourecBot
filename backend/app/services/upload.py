"""
文件上传服务
处理文件上传并转换为 Telegram file_id
"""
import os
from io import BytesIO
from pathlib import Path
from typing import Optional

import aiofiles
import imageio.v3 as iio
from aiogram import Bot
from aiogram.types import FSInputFile
from PIL import Image

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
            thumbnail_path = self._create_video_thumbnail(file_path)
            try:
                message = await self.bot.send_video(
                    chat_id=settings.STORAGE_CHANNEL_ID,
                    video=input_file,
                    caption=caption,
                    thumbnail=FSInputFile(thumbnail_path),
                    cover=FSInputFile(thumbnail_path),
                    supports_streaming=True,
                )
                file_id = message.video.file_id
            finally:
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
        
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

    def _create_video_thumbnail(self, file_path: str) -> str:
        """从视频首帧生成缩略图（JPEG ≤320px，≤200KB）"""
        try:
            frame = iio.imread(file_path, index=0)
        except Exception as exc:
            raise RuntimeError("提取视频首帧失败") from exc

        image = Image.fromarray(frame).convert("RGB")
        image = self._resize_to_max(image, 320)
        jpeg_bytes = self._encode_jpeg_under_limit(image, 200 * 1024)

        thumb_path = self.upload_dir / f"{Path(file_path).stem}_thumb.jpg"
        with open(thumb_path, "wb") as f:
            f.write(jpeg_bytes)
        return str(thumb_path)

    def _resize_to_max(self, image: Image.Image, max_dim: int) -> Image.Image:
        """等比缩放到最大边不超过 max_dim"""
        width, height = image.size
        if max(width, height) <= max_dim:
            return image
        scale = max_dim / max(width, height)
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return image.resize(new_size, Image.LANCZOS)

    def _encode_jpeg_under_limit(self, image: Image.Image, max_bytes: int) -> bytes:
        """压缩到指定大小以内"""
        quality = 85
        while quality >= 35:
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            if buffer.tell() <= max_bytes:
                return buffer.getvalue()
            quality -= 10

        current = image
        while True:
            width, height = current.size
            if max(width, height) <= 100:
                break
            current = current.resize(
                (max(1, int(width * 0.9)), max(1, int(height * 0.9))),
                Image.LANCZOS,
            )
            buffer = BytesIO()
            current.save(buffer, format="JPEG", quality=70, optimize=True)
            if buffer.tell() <= max_bytes:
                return buffer.getvalue()

        raise ValueError("无法生成满足大小限制的缩略图")
    
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
