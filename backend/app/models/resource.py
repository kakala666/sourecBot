"""
资源和媒体文件模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship

from app.database import Base


class Resource(Base):
    """资源表"""
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    invite_link_id = Column(Integer, ForeignKey("invite_links.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属邀请链接ID")
    title = Column(String(200), nullable=True, comment="资源标题")
    description = Column(Text, nullable=True, comment="资源描述/文案")
    media_type = Column(String(20), nullable=False, comment="媒体类型: photo/video/media_group")
    display_order = Column(Integer, default=0, comment="显示顺序")
    is_cover = Column(Boolean, default=False, comment="是否为封面")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系
    invite_link = relationship("InviteLink", back_populates="resources", foreign_keys=[invite_link_id])
    media_files = relationship("MediaFile", back_populates="resource", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Resource(id={self.id}, title='{self.title}', type='{self.media_type}')>"


class MediaFile(Base):
    """媒体文件表 (支持媒体组)"""
    __tablename__ = "media_files"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属资源ID")
    file_type = Column(String(20), nullable=False, comment="文件类型: photo/video")
    file_path = Column(String(500), nullable=True, comment="服务器文件路径")
    telegram_file_id = Column(String(200), nullable=False, comment="Telegram file_id")
    file_size = Column(BigInteger, nullable=True, comment="文件大小(字节)")
    position = Column(Integer, default=0, comment="在媒体组中的位置")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系
    resource = relationship("Resource", back_populates="media_files")
    
    def __repr__(self):
        return f"<MediaFile(id={self.id}, type='{self.file_type}', position={self.position})>"
