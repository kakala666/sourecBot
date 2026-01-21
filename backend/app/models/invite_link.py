"""
邀请链接模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
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
    
    # 频道采集配置
    source_channel_id = Column(BigInteger, nullable=True, index=True, comment="绑定的频道ID")
    source_channel_username = Column(String(100), nullable=True, comment="频道用户名")
    auto_collect_enabled = Column(Boolean, default=False, comment="是否启用自动采集")
    
    # 关系
    resources = relationship("Resource", back_populates="invite_link", foreign_keys="Resource.invite_link_id")
    cover_resource = relationship("Resource", foreign_keys=[cover_resource_id])
    users = relationship("User", back_populates="invite_link")
    ad_groups = relationship("AdGroup", secondary="invite_link_ad_groups", back_populates="invite_links")
    
    def __repr__(self):
        return f"<InviteLink(id={self.id}, code='{self.code}', name='{self.name}')>"

