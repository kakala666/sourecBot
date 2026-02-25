"""
SourceBot 管理员密码更新脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.database import AsyncSessionLocal
from app.models import Admin
from app.utils.auth import hash_password
from sqlalchemy import select


async def update_admin_password(username: str, new_password: str):
    """更新管理员密码"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Admin).where(Admin.username == username)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            print(f"❌ 用户不存在: {username}")
            return False
        
        admin.password_hash = hash_password(new_password)
        await session.commit()
        
        print(f"✅ 密码更新成功!")
        print(f"   用户名: {username}")
        print(f"   新密码: {new_password}")
        return True


if __name__ == "__main__":
    # 更新 admin 用户密码为 guowang111.
    asyncio.run(update_admin_password("admin", "guowang111."))
