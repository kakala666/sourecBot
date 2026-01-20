"""
数据库初始化脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import engine, Base, AsyncSessionLocal
from app.models import *  # 导入所有模型
from app.utils.auth import hash_password


async def init_database():
    """初始化数据库,创建所有表"""
    print("正在创建数据库表...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("数据库表创建完成!")


async def create_default_admin():
    """创建默认管理员账号"""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        # 检查是否已存在管理员
        result = await session.execute(select(Admin).limit(1))
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"管理员已存在: {existing_admin.username}")
            return
        
        # 创建默认管理员
        default_admin = Admin(
            username="admin",
            password_hash=hash_password("admin123"),  # 默认密码,请在生产环境修改
            email="admin@example.com",
            is_active=True,
        )
        
        session.add(default_admin)
        await session.commit()
        
        print("默认管理员已创建:")
        print("  用户名: admin")
        print("  密码: admin123")
        print("  ⚠️  请在生产环境中修改默认密码!")


async def create_default_config():
    """创建默认配置"""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        # 默认配置列表
        default_configs = [
            {
                "key": "remark_template",
                "value": "{name} {date}【{source}】",
                "description": "客服备注模板"
            },
            {
                "key": "preview_limit",
                "value": "5",
                "description": "预览资源数量限制"
            },
            {
                "key": "wait_times",
                "value": "2,3,4,5,5,5,5",
                "description": "翻页等待时间(秒),逗号分隔"
            },
        ]
        
        for config_data in default_configs:
            result = await session.execute(
                select(Config).where(Config.key == config_data["key"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                config = Config(**config_data)
                session.add(config)
                print(f"创建配置: {config_data['key']}")
        
        await session.commit()
        print("默认配置创建完成!")


async def main():
    """主函数"""
    print("=" * 50)
    print("SourceBot 数据库初始化")
    print("=" * 50)
    
    await init_database()
    await create_default_admin()
    await create_default_config()
    
    print("=" * 50)
    print("初始化完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
