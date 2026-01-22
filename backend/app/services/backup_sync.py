"""
备份同步服务

提供：
- 备份 Bot 配置管理
- file_id 同步
- 主备切换
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import MediaFile, SponsorMediaFile, BotBackup, FileIdMapping
from app.config import settings

logger = logging.getLogger(__name__)


class BackupSyncService:
    """备份同步服务"""
    
    def __init__(self):
        self._backup_bot: Optional[Bot] = None
        self._is_syncing: bool = False
        self._stop_flag: bool = False
    
    async def get_backup_config(self) -> Optional[BotBackup]:
        """获取备份配置"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(BotBackup).limit(1))
            return result.scalar_one_or_none()
    
    async def create_backup_config(self, token: str) -> dict:
        """创建备份配置
        
        Args:
            token: 备份 Bot Token
            
        Returns:
            {"success": bool, "error": str, "backup": BotBackup}
        """
        try:
            # 验证 Token
            bot = Bot(token=token)
            bot_info = await bot.get_me()
            await bot.session.close()
            
            # 验证备份 Bot 是否在存储频道中
            try:
                test_bot = Bot(token=token)
                member = await test_bot.get_chat_member(
                    chat_id=settings.STORAGE_CHANNEL_ID,
                    user_id=bot_info.id
                )
                await test_bot.session.close()
                
                if member.status not in ('administrator', 'creator'):
                    return {
                        "success": False,
                        "error": f"备份 Bot @{bot_info.username} 需要是存储频道的管理员"
                    }
            except TelegramAPIError as e:
                return {
                    "success": False,
                    "error": f"无法验证备份 Bot 在存储频道的权限: {str(e)}"
                }
            
            async with AsyncSessionLocal() as session:
                # 检查是否已存在配置
                existing = await session.execute(select(BotBackup).limit(1))
                if existing.scalar_one_or_none():
                    return {"success": False, "error": "已存在备份配置，请先删除"}
                
                # 统计需要同步的文件数
                media_count = await session.scalar(
                    select(func.count()).select_from(MediaFile)
                )
                sponsor_count = await session.scalar(
                    select(func.count()).select_from(SponsorMediaFile)
                )
                total = (media_count or 0) + (sponsor_count or 0)
                
                # 创建配置
                backup = BotBackup(
                    backup_bot_token=token,
                    backup_bot_username=bot_info.username,
                    backup_bot_id=bot_info.id,
                    sync_status="pending",
                    total_count=total,
                )
                session.add(backup)
                await session.commit()
                await session.refresh(backup)
                
                logger.info(f"创建备份配置: @{bot_info.username}, 待同步文件: {total}")
                
                return {"success": True, "backup": backup}
                
        except TelegramAPIError as e:
            return {"success": False, "error": f"Token 无效: {str(e)}"}
        except Exception as e:
            logger.error(f"创建备份配置失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def delete_backup_config(self) -> dict:
        """删除备份配置"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(BotBackup).limit(1))
            backup = result.scalar_one_or_none()
            
            if not backup:
                return {"success": False, "error": "没有备份配置"}
            
            if backup.is_active:
                return {"success": False, "error": "备份 Bot 正在使用中，无法删除"}
            
            await session.delete(backup)
            
            # 删除映射表
            await session.execute(
                FileIdMapping.__table__.delete()
            )
            
            await session.commit()
            
            logger.info("已删除备份配置和映射数据")
            return {"success": True}
    
    async def start_sync(self) -> dict:
        """开始同步"""
        if self._is_syncing:
            return {"success": False, "error": "同步正在进行中"}
        
        backup = await self.get_backup_config()
        if not backup:
            return {"success": False, "error": "没有备份配置"}
        
        # 启动后台同步任务
        asyncio.create_task(self._execute_sync(backup.id))
        
        return {"success": True, "message": "同步任务已启动"}
    
    async def stop_sync(self) -> dict:
        """停止同步"""
        self._stop_flag = True
        return {"success": True, "message": "正在停止同步..."}
    
    async def _execute_sync(self, backup_id: int) -> None:
        """执行同步任务"""
        self._is_syncing = True
        self._stop_flag = False
        
        logger.info(f"开始同步任务: backup_id={backup_id}")
        
        try:
            async with AsyncSessionLocal() as session:
                # 获取备份配置
                result = await session.execute(
                    select(BotBackup).where(BotBackup.id == backup_id)
                )
                backup = result.scalar_one_or_none()
                
                if not backup:
                    logger.error("备份配置不存在")
                    return
                
                # 更新状态
                backup.sync_status = "syncing"
                await session.commit()
                
                # 创建备份 Bot 实例
                backup_bot = Bot(token=backup.backup_bot_token)
                
                try:
                    # 同步 MediaFile
                    synced, failed = await self._sync_media_files(
                        session, backup_bot, backup_id
                    )
                    
                    # 同步 SponsorMediaFile
                    s2, f2 = await self._sync_sponsor_files(
                        session, backup_bot, backup_id
                    )
                    synced += s2
                    failed += f2
                    
                    # 更新状态
                    backup.sync_status = "synced" if failed == 0 else "error"
                    backup.synced_count = synced
                    backup.failed_count = failed
                    backup.last_synced_at = datetime.utcnow()
                    
                    if failed > 0:
                        backup.error_message = f"{failed} 个文件同步失败"
                    else:
                        backup.error_message = None
                    
                    await session.commit()
                    
                    logger.info(f"同步完成: synced={synced}, failed={failed}")
                    
                finally:
                    await backup_bot.session.close()
                    
        except Exception as e:
            logger.error(f"同步任务出错: {e}", exc_info=True)
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(BotBackup).where(BotBackup.id == backup_id)
                )
                backup = result.scalar_one_or_none()
                if backup:
                    backup.sync_status = "error"
                    backup.error_message = str(e)
                    await session.commit()
        finally:
            self._is_syncing = False
            self._stop_flag = False
    
    async def _sync_media_files(
        self,
        session: AsyncSession,
        backup_bot: Bot,
        backup_id: int
    ) -> tuple[int, int]:
        """同步 MediaFile"""
        synced = 0
        failed = 0
        
        # 获取所有有 source_message_id 的媒体文件
        result = await session.execute(
            select(MediaFile).where(
                MediaFile.source_message_id.isnot(None),
                MediaFile.source_channel_id.isnot(None)
            )
        )
        media_files = result.scalars().all()
        
        logger.info(f"待同步 MediaFile: {len(media_files)}")
        
        for mf in media_files:
            if self._stop_flag:
                logger.info("收到停止信号，退出同步")
                break
            
            # 检查是否已同步
            existing = await session.execute(
                select(FileIdMapping).where(
                    FileIdMapping.source_type == "resource",
                    FileIdMapping.source_id == mf.id
                )
            )
            if existing.scalar_one_or_none():
                synced += 1
                continue
            
            try:
                # 转发消息到存储频道
                forwarded = await backup_bot.forward_message(
                    chat_id=settings.STORAGE_CHANNEL_ID,
                    from_chat_id=mf.source_channel_id,
                    message_id=mf.source_message_id
                )
                
                # 提取 file_id
                backup_file_id = None
                backup_file_unique_id = None
                
                if forwarded.photo:
                    photo = forwarded.photo[-1]
                    backup_file_id = photo.file_id
                    backup_file_unique_id = photo.file_unique_id
                elif forwarded.video:
                    backup_file_id = forwarded.video.file_id
                    backup_file_unique_id = forwarded.video.file_unique_id
                elif forwarded.animation:
                    backup_file_id = forwarded.animation.file_id
                    backup_file_unique_id = forwarded.animation.file_unique_id
                elif forwarded.document:
                    backup_file_id = forwarded.document.file_id
                    backup_file_unique_id = forwarded.document.file_unique_id
                
                if backup_file_id:
                    # 更新 MediaFile 的 file_unique_id
                    if not mf.file_unique_id:
                        mf.file_unique_id = backup_file_unique_id
                    
                    # 创建映射
                    mapping = FileIdMapping(
                        file_unique_id=mf.file_unique_id or backup_file_unique_id,
                        primary_file_id=mf.telegram_file_id,
                        backup_file_id=backup_file_id,
                        file_type=mf.file_type,
                        source_type="resource",
                        source_id=mf.id
                    )
                    session.add(mapping)
                    await session.commit()
                    
                    synced += 1
                    logger.debug(f"同步成功: MediaFile id={mf.id}")
                else:
                    failed += 1
                    logger.warning(f"无法提取 file_id: MediaFile id={mf.id}")
                
                # 删除转发的消息
                try:
                    await backup_bot.delete_message(
                        chat_id=settings.STORAGE_CHANNEL_ID,
                        message_id=forwarded.message_id
                    )
                except:
                    pass
                
                # 速率限制
                await asyncio.sleep(0.3)
                
            except TelegramAPIError as e:
                failed += 1
                logger.error(f"同步失败 MediaFile id={mf.id}: {e}")
        
        return synced, failed
    
    async def _sync_sponsor_files(
        self,
        session: AsyncSession,
        backup_bot: Bot,
        backup_id: int
    ) -> tuple[int, int]:
        """同步 SponsorMediaFile
        
        广告媒体没有 source_message_id，需要通过发送到存储频道再提取
        """
        synced = 0
        failed = 0
        
        # 获取主 Bot
        from app.config import settings
        main_bot = Bot(token=settings.BOT_TOKEN)
        
        try:
            result = await session.execute(select(SponsorMediaFile))
            sponsor_files = result.scalars().all()
            
            logger.info(f"待同步 SponsorMediaFile: {len(sponsor_files)}")
            
            for sf in sponsor_files:
                if self._stop_flag:
                    break
                
                # 检查是否已同步
                existing = await session.execute(
                    select(FileIdMapping).where(
                        FileIdMapping.source_type == "sponsor",
                        FileIdMapping.source_id == sf.id
                    )
                )
                if existing.scalar_one_or_none():
                    synced += 1
                    continue
                
                try:
                    # 用主 Bot 发送到存储频道
                    if sf.file_type == "photo":
                        sent = await main_bot.send_photo(
                            chat_id=settings.STORAGE_CHANNEL_ID,
                            photo=sf.telegram_file_id
                        )
                    elif sf.file_type == "video":
                        sent = await main_bot.send_video(
                            chat_id=settings.STORAGE_CHANNEL_ID,
                            video=sf.telegram_file_id
                        )
                    else:
                        sent = await main_bot.send_document(
                            chat_id=settings.STORAGE_CHANNEL_ID,
                            document=sf.telegram_file_id
                        )
                    
                    # 备份 Bot 转发这条消息
                    forwarded = await backup_bot.forward_message(
                        chat_id=settings.STORAGE_CHANNEL_ID,
                        from_chat_id=settings.STORAGE_CHANNEL_ID,
                        message_id=sent.message_id
                    )
                    
                    # 提取 file_id
                    backup_file_id = None
                    file_unique_id = None
                    
                    if forwarded.photo:
                        photo = forwarded.photo[-1]
                        backup_file_id = photo.file_id
                        file_unique_id = photo.file_unique_id
                    elif forwarded.video:
                        backup_file_id = forwarded.video.file_id
                        file_unique_id = forwarded.video.file_unique_id
                    elif forwarded.document:
                        backup_file_id = forwarded.document.file_id
                        file_unique_id = forwarded.document.file_unique_id
                    
                    if backup_file_id:
                        # 更新 SponsorMediaFile
                        if not sf.file_unique_id:
                            sf.file_unique_id = file_unique_id
                        
                        # 创建映射
                        mapping = FileIdMapping(
                            file_unique_id=sf.file_unique_id or file_unique_id,
                            primary_file_id=sf.telegram_file_id,
                            backup_file_id=backup_file_id,
                            file_type=sf.file_type,
                            source_type="sponsor",
                            source_id=sf.id
                        )
                        session.add(mapping)
                        await session.commit()
                        
                        synced += 1
                    else:
                        failed += 1
                    
                    # 删除临时消息
                    try:
                        await main_bot.delete_message(
                            chat_id=settings.STORAGE_CHANNEL_ID,
                            message_id=sent.message_id
                        )
                        await backup_bot.delete_message(
                            chat_id=settings.STORAGE_CHANNEL_ID,
                            message_id=forwarded.message_id
                        )
                    except:
                        pass
                    
                    await asyncio.sleep(0.5)
                    
                except TelegramAPIError as e:
                    failed += 1
                    logger.error(f"同步失败 SponsorMediaFile id={sf.id}: {e}")
        
        finally:
            await main_bot.session.close()
        
        return synced, failed
    
    async def switch_to_backup(self) -> dict:
        """切换到备份 Bot"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(BotBackup).limit(1))
            backup = result.scalar_one_or_none()
            
            if not backup:
                return {"success": False, "error": "没有备份配置"}
            
            if backup.sync_status != "synced":
                return {"success": False, "error": "请先完成同步"}
            
            backup.is_active = True
            await session.commit()
            
            logger.info("已切换到备份 Bot")
            return {"success": True, "message": "已切换到备份 Bot"}
    
    async def switch_to_primary(self) -> dict:
        """切换回主 Bot"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(BotBackup).limit(1))
            backup = result.scalar_one_or_none()
            
            if not backup:
                return {"success": False, "error": "没有备份配置"}
            
            backup.is_active = False
            await session.commit()
            
            logger.info("已切换回主 Bot")
            return {"success": True, "message": "已切换回主 Bot"}
    
    async def get_file_id(self, file_unique_id: str) -> Optional[str]:
        """根据 file_unique_id 获取当前应使用的 file_id
        
        如果备份 Bot 激活，返回 backup_file_id，否则返回 primary_file_id
        """
        async with AsyncSessionLocal() as session:
            # 获取备份配置
            backup_result = await session.execute(select(BotBackup).limit(1))
            backup = backup_result.scalar_one_or_none()
            
            use_backup = backup and backup.is_active
            
            # 查找映射
            result = await session.execute(
                select(FileIdMapping).where(
                    FileIdMapping.file_unique_id == file_unique_id
                )
            )
            mapping = result.scalar_one_or_none()
            
            if not mapping:
                return None
            
            if use_backup and mapping.backup_file_id:
                return mapping.backup_file_id
            return mapping.primary_file_id


# 全局单例
backup_sync_service = BackupSyncService()
