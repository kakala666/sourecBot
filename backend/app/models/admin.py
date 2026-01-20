"""
管理员模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database import Base


class Admin(Base):
    """管理员表"""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(200), nullable=False, comment="密码哈希")
    email = Column(String(200), nullable=True, comment="邮箱")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    def __repr__(self):
        return f"<Admin(id={self.id}, username='{self.username}')>"
