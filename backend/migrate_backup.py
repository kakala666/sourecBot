"""
备份功能数据库迁移脚本

使用方法:
    cd backend
    python migrate_backup.py

支持的数据库:
    - PostgreSQL (asyncpg)
    - SQLite (aiosqlite)
    - MySQL (aiomysql)
"""
import asyncio
import sys
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine

# 加载配置
from app.config import settings


async def get_existing_columns(conn, table_name: str) -> set[str]:
    """获取表的现有列名"""
    # 根据数据库类型使用不同的查询
    db_url = settings.DATABASE_URL.lower()
    
    if "sqlite" in db_url:
        result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
        rows = result.fetchall()
        return {row[1] for row in rows}  # column name is at index 1
    elif "postgresql" in db_url or "postgres" in db_url:
        result = await conn.execute(text(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """))
        rows = result.fetchall()
        return {row[0] for row in rows}
    elif "mysql" in db_url:
        result = await conn.execute(text(f"DESCRIBE {table_name}"))
        rows = result.fetchall()
        return {row[0] for row in rows}
    else:
        # 默认尝试 PostgreSQL 方式
        result = await conn.execute(text(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """))
        rows = result.fetchall()
        return {row[0] for row in rows}


async def table_exists(conn, table_name: str) -> bool:
    """检查表是否存在"""
    db_url = settings.DATABASE_URL.lower()
    
    try:
        if "sqlite" in db_url:
            result = await conn.execute(text(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
            ))
        elif "postgresql" in db_url or "postgres" in db_url:
            result = await conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                )
            """))
        elif "mysql" in db_url:
            result = await conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
        else:
            result = await conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                )
            """))
        
        row = result.fetchone()
        return bool(row and row[0])
    except Exception:
        return False


async def add_column_if_not_exists(conn, table_name: str, column_name: str, column_type: str):
    """如果列不存在则添加"""
    existing = await get_existing_columns(conn, table_name)
    
    if column_name.lower() in {c.lower() for c in existing}:
        print(f"  ✓ 列 {table_name}.{column_name} 已存在，跳过")
        return False
    
    db_url = settings.DATABASE_URL.lower()
    
    # 根据数据库类型调整类型名称
    if "sqlite" in db_url:
        # SQLite 类型映射
        type_map = {
            "VARCHAR(255)": "TEXT",
            "VARCHAR(100)": "TEXT",
            "VARCHAR(200)": "TEXT",
            "VARCHAR(50)": "TEXT",
            "VARCHAR(20)": "TEXT",
            "BIGINT": "INTEGER",
            "TEXT": "TEXT",
            "INTEGER": "INTEGER",
            "BOOLEAN": "INTEGER",
            "TIMESTAMP": "TEXT",
        }
        column_type = type_map.get(column_type.upper(), column_type)
    
    try:
        await conn.execute(text(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        ))
        print(f"  ✓ 添加列 {table_name}.{column_name} ({column_type})")
        return True
    except Exception as e:
        print(f"  ✗ 添加列 {table_name}.{column_name} 失败: {e}")
        return False


async def create_table_if_not_exists(conn, table_name: str, create_sql: str):
    """如果表不存在则创建"""
    if await table_exists(conn, table_name):
        print(f"  ✓ 表 {table_name} 已存在，跳过")
        return False
    
    try:
        await conn.execute(text(create_sql))
        print(f"  ✓ 创建表 {table_name}")
        return True
    except Exception as e:
        print(f"  ✗ 创建表 {table_name} 失败: {e}")
        return False


async def run_migration():
    """执行迁移"""
    print("=" * 60)
    print("备份功能数据库迁移")
    print("=" * 60)
    print(f"数据库: {settings.DATABASE_URL[:50]}...")
    print()
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        db_url = settings.DATABASE_URL.lower()
        is_sqlite = "sqlite" in db_url
        
        # 1. 为 media_files 表添加新列
        print("[1/4] 更新 media_files 表...")
        if await table_exists(conn, "media_files"):
            await add_column_if_not_exists(conn, "media_files", "file_unique_id", "VARCHAR(100)")
            await add_column_if_not_exists(conn, "media_files", "source_channel_id", "BIGINT")
            await add_column_if_not_exists(conn, "media_files", "source_message_id", "BIGINT")
        else:
            print("  ⚠ 表 media_files 不存在，请先运行 init_db()")
        
        # 2. 为 sponsor_media_files 表添加新列
        print("\n[2/4] 更新 sponsor_media_files 表...")
        if await table_exists(conn, "sponsor_media_files"):
            await add_column_if_not_exists(conn, "sponsor_media_files", "file_unique_id", "VARCHAR(100)")
        else:
            print("  ⚠ 表 sponsor_media_files 不存在，请先运行 init_db()")
        
        # 3. 创建 bot_backups 表
        print("\n[3/4] 创建 bot_backups 表...")
        if is_sqlite:
            create_bot_backups = """
                CREATE TABLE bot_backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_bot_token TEXT NOT NULL,
                    backup_bot_username TEXT,
                    backup_bot_id INTEGER,
                    is_active INTEGER DEFAULT 0,
                    sync_status TEXT DEFAULT 'pending',
                    total_count INTEGER DEFAULT 0,
                    synced_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    last_synced_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
        else:
            create_bot_backups = """
                CREATE TABLE bot_backups (
                    id SERIAL PRIMARY KEY,
                    backup_bot_token VARCHAR(255) NOT NULL,
                    backup_bot_username VARCHAR(255),
                    backup_bot_id BIGINT,
                    is_active BOOLEAN DEFAULT FALSE,
                    sync_status VARCHAR(50) DEFAULT 'pending',
                    total_count INTEGER DEFAULT 0,
                    synced_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    last_synced_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        await create_table_if_not_exists(conn, "bot_backups", create_bot_backups)
        
        # 4. 创建 file_id_mappings 表
        print("\n[4/4] 创建 file_id_mappings 表...")
        if is_sqlite:
            create_file_id_mappings = """
                CREATE TABLE file_id_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_unique_id TEXT NOT NULL,
                    primary_file_id TEXT NOT NULL,
                    backup_file_id TEXT,
                    file_type TEXT,
                    source_type TEXT,
                    source_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
        else:
            create_file_id_mappings = """
                CREATE TABLE file_id_mappings (
                    id SERIAL PRIMARY KEY,
                    file_unique_id VARCHAR(255) NOT NULL,
                    primary_file_id VARCHAR(255) NOT NULL,
                    backup_file_id VARCHAR(255),
                    file_type VARCHAR(50),
                    source_type VARCHAR(50),
                    source_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        await create_table_if_not_exists(conn, "file_id_mappings", create_file_id_mappings)
        
        # 创建索引
        print("\n[额外] 创建索引...")
        indexes = [
            ("ix_media_files_file_unique_id", "media_files", "file_unique_id"),
            ("ix_sponsor_media_files_file_unique_id", "sponsor_media_files", "file_unique_id"),
            ("ix_file_id_mappings_file_unique_id", "file_id_mappings", "file_unique_id"),
            ("ix_file_id_mappings_source", "file_id_mappings", "source_type, source_id"),
        ]
        
        for idx_name, table_name, columns in indexes:
            try:
                if is_sqlite:
                    await conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({columns})"
                    ))
                else:
                    # PostgreSQL/MySQL
                    await conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({columns})"
                    ))
                print(f"  ✓ 索引 {idx_name}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"  ✓ 索引 {idx_name} 已存在")
                else:
                    print(f"  ⚠ 索引 {idx_name}: {e}")
    
    await engine.dispose()
    
    print()
    print("=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print()
    print("下一步：")
    print("1. 重启后端服务")
    print("2. 在前端访问「备份管理」页面配置备份 Bot")


if __name__ == "__main__":
    try:
        asyncio.run(run_migration())
    except KeyboardInterrupt:
        print("\n用户取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n迁移失败: {e}")
        sys.exit(1)
