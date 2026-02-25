"""
邀请链接自定义按钮模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class InviteLinkButton(Base):
    """邀请链接自定义按钮表"""
    __tablename__ = "invite_link_buttons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    invite_link_id = Column(Integer, ForeignKey("invite_links.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属邀请链接ID")
    text = Column(String(100), nullable=False, comment="按钮文字")
    url = Column(String(500), nullable=False, comment="跳转链接")
    display_order = Column(Integer, default=0, comment="显示顺序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系
    invite_link = relationship("InviteLink", back_populates="buttons")
    
    def __repr__(self):
        return f"<InviteLinkButton(id={self.id}, text='{self.text}', url='{self.url[:30]}...')>"
