"""
用户和会话模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True, comment="Telegram 用户ID")
    username = Column(String(100), nullable=True, comment="用户名")
    first_name = Column(String(100), nullable=True, comment="名字")
    last_name = Column(String(100), nullable=True, comment="姓氏")
    invite_code = Column(String(50), ForeignKey("invite_links.code"), nullable=True, index=True, comment="来源邀请码")
    first_seen = Column(DateTime, default=datetime.utcnow, comment="首次使用时间")
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="最后活跃时间")
    
    # 关系
    invite_link = relationship("InviteLink", back_populates="users", foreign_keys=[invite_code], primaryjoin="User.invite_code == InviteLink.code")
    session = relationship("UserSession", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    @property
    def full_name(self) -> str:
        """获取完整姓名"""
        parts = [self.first_name or "", self.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        return name or self.username or f"用户{self.telegram_id}"
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, invite_code='{self.invite_code}')>"


class UserSession(Base):
    """用户会话表 (FSM 状态)"""
    __tablename__ = "user_sessions"
    
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True, comment="用户ID")
    invite_code = Column(String(50), nullable=True, comment="当前浏览的邀请码")
    current_page = Column(Integer, default=0, comment="当前页码")
    wait_count = Column(Integer, default=0, comment="已等待次数")
    current_ad_index = Column(Integer, default=0, comment="当前广告索引")
    last_interaction = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="最后交互时间")
    
    # 关系
    user = relationship("User", back_populates="session")
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, page={self.current_page}, wait_count={self.wait_count})>"
