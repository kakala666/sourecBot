"""
邀请链接模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class InviteLink(Base):
    """邀请链接表"""
    __tablename__ = "invite_links"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True, comment="邀请码")
    name = Column(String(100), nullable=False, comment="链接名称")
    cover_resource_id = Column(Integer, ForeignKey("resources.id", ondelete="SET NULL"), nullable=True, comment="封面资源ID")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    resources = relationship("Resource", back_populates="invite_link", foreign_keys="Resource.invite_link_id")
    cover_resource = relationship("Resource", foreign_keys=[cover_resource_id])
    users = relationship("User", back_populates="invite_link")
    ad_groups = relationship("AdGroup", secondary="invite_link_ad_groups", back_populates="invite_links")
    
    def __repr__(self):
        return f"<InviteLink(id={self.id}, code='{self.code}', name='{self.name}')>"
