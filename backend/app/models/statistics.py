"""
统计事件模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey

from app.database import Base


class Statistics(Base):
    """统计事件表"""
    __tablename__ = "statistics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True, comment="事件类型: user_start/page_view/ad_view/ad_click/preview_end")
    user_id = Column(BigInteger, nullable=True, index=True, comment="用户 Telegram ID")
    invite_code = Column(String(50), nullable=True, index=True, comment="邀请码")
    resource_id = Column(Integer, nullable=True, comment="资源ID")
    sponsor_id = Column(Integer, nullable=True, comment="广告ID")
    page_number = Column(Integer, nullable=True, comment="页码")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")
    
    def __repr__(self):
        return f"<Statistics(id={self.id}, type='{self.event_type}', user_id={self.user_id})>"
