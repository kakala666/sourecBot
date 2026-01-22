"""
备份相关模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, BigInteger, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class BotBackup(Base):
    """备份 Bot 配置"""
    __tablename__ = "bot_backups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    backup_bot_token = Column(String(100), nullable=False, comment="备份 Bot Token")
    backup_bot_username = Column(String(50), nullable=True, comment="备份 Bot 用户名")
    backup_bot_id = Column(BigInteger, nullable=True, comment="备份 Bot Telegram ID")
    
    # 同步状态: pending/syncing/synced/error
    sync_status = Column(String(20), default="pending", comment="同步状态")
    last_synced_at = Column(DateTime, nullable=True, comment="上次同步时间")
    synced_count = Column(Integer, default=0, comment="已同步数量")
    failed_count = Column(Integer, default=0, comment="失败数量")
    total_count = Column(Integer, default=0, comment="总数量")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 是否已切换到备份 Bot
    is_active = Column(Boolean, default=False, comment="是否激活备份 Bot")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self):
        return f"<BotBackup(id={self.id}, username='{self.backup_bot_username}', status='{self.sync_status}')>"


class FileIdMapping(Base):
    """file_id 映射表
    
    存储同一文件在主 Bot 和备份 Bot 下的 file_id 映射关系。
    使用 file_unique_id 作为跨 Bot 的唯一标识。
    """
    __tablename__ = "file_id_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 跨 Bot 通用的唯一标识
    file_unique_id = Column(String(100), nullable=False, index=True, comment="文件唯一标识")
    
    # 主 Bot 的 file_id
    primary_file_id = Column(String(200), nullable=False, comment="主 Bot file_id")
    # 备份 Bot 的 file_id
    backup_file_id = Column(String(200), nullable=True, comment="备份 Bot file_id")
    
    file_type = Column(String(20), nullable=True, comment="文件类型: photo/video/animation")
    
    # 来源类型和 ID（用于追踪）
    source_type = Column(String(20), nullable=True, comment="来源类型: resource/sponsor")
    source_id = Column(Integer, nullable=True, comment="来源 ID (MediaFile.id 或 SponsorMediaFile.id)")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        UniqueConstraint('file_unique_id', name='uq_file_unique_id'),
    )
    
    def __repr__(self):
        return f"<FileIdMapping(id={self.id}, unique_id='{self.file_unique_id[:20]}...')>"
