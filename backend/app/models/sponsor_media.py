"""
广告媒体文件模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class SponsorMediaFile(Base):
    """广告媒体文件表"""
    __tablename__ = "sponsor_media_files"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sponsor_id = Column(Integer, ForeignKey("sponsors.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属广告ID")
    file_type = Column(String(20), nullable=False, comment="文件类型: photo/video")
    telegram_file_id = Column(String(200), nullable=False, comment="Telegram file_id")
    file_size = Column(Integer, nullable=True, comment="文件大小(字节)")
    position = Column(Integer, default=0, comment="在媒体组中的位置")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系
    sponsor = relationship("Sponsor", back_populates="media_files")
    
    def __repr__(self):
        return f"<SponsorMediaFile(id={self.id}, sponsor_id={self.sponsor_id}, type='{self.file_type}')>"
