"""
赞助商广告和广告组模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class AdGroup(Base):
    """广告组表"""
    __tablename__ = "ad_groups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="广告组名称")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系
    sponsors = relationship("Sponsor", back_populates="ad_group", cascade="all, delete-orphan")
    invite_links = relationship("InviteLink", secondary="invite_link_ad_groups", back_populates="ad_groups")
    
    def __repr__(self):
        return f"<AdGroup(id={self.id}, name='{self.name}')>"


class Sponsor(Base):
    """赞助商广告表"""
    __tablename__ = "sponsors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属广告组ID")
    title = Column(String(200), nullable=False, comment="广告标题")
    description = Column(Text, nullable=True, comment="广告描述")
    media_type = Column(String(20), nullable=True, comment="媒体类型: photo/video/none")
    telegram_file_id = Column(String(200), nullable=True, comment="Telegram file_id")
    button_text = Column(String(50), nullable=True, comment="按钮文字")
    button_url = Column(String(500), nullable=True, comment="跳转链接")
    is_active = Column(Boolean, default=True, comment="是否启用")
    display_order = Column(Integer, default=0, comment="显示顺序")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系
    ad_group = relationship("AdGroup", back_populates="sponsors")
    
    def __repr__(self):
        return f"<Sponsor(id={self.id}, title='{self.title}')>"


class InviteLinkAdGroup(Base):
    """邀请链接-广告组关联表"""
    __tablename__ = "invite_link_ad_groups"
    
    invite_link_id = Column(Integer, ForeignKey("invite_links.id", ondelete="CASCADE"), primary_key=True, comment="邀请链接ID")
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), primary_key=True, comment="广告组ID")
