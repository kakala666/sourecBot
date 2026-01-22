-- 备份功能数据库迁移脚本
-- 执行时间: 添加备份 Bot 功能时
-- 注意: 如果使用 init_db() 自动创建表，此脚本仅供手动迁移参考

-- =====================================================
-- 1. 创建备份配置表 bot_backups
-- =====================================================
CREATE TABLE IF NOT EXISTS bot_backups (
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
);

-- 添加索引
CREATE INDEX IF NOT EXISTS ix_bot_backups_is_active ON bot_backups (is_active);

-- =====================================================
-- 2. 创建文件 ID 映射表 file_id_mappings
-- =====================================================
CREATE TABLE IF NOT EXISTS file_id_mappings (
    id SERIAL PRIMARY KEY,
    file_unique_id VARCHAR(255) NOT NULL,
    primary_file_id VARCHAR(255) NOT NULL,
    backup_file_id VARCHAR(255),
    file_type VARCHAR(50),
    source_type VARCHAR(50),
    source_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 添加索引
CREATE INDEX IF NOT EXISTS ix_file_id_mappings_file_unique_id ON file_id_mappings (file_unique_id);
CREATE INDEX IF NOT EXISTS ix_file_id_mappings_source ON file_id_mappings (source_type, source_id);

-- =====================================================
-- 3. 为 media_files 表添加新字段
-- =====================================================
ALTER TABLE media_files 
    ADD COLUMN IF NOT EXISTS file_unique_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS source_channel_id BIGINT,
    ADD COLUMN IF NOT EXISTS source_message_id INTEGER;

-- 添加索引
CREATE INDEX IF NOT EXISTS ix_media_files_file_unique_id ON media_files (file_unique_id);

-- =====================================================
-- 4. 为 sponsor_media_files 表添加新字段
-- =====================================================
ALTER TABLE sponsor_media_files 
    ADD COLUMN IF NOT EXISTS file_unique_id VARCHAR(255);

-- 添加索引
CREATE INDEX IF NOT EXISTS ix_sponsor_media_files_file_unique_id ON sponsor_media_files (file_unique_id);

-- =====================================================
-- 回滚脚本 (如需回滚请执行以下命令)
-- =====================================================
-- DROP TABLE IF EXISTS file_id_mappings;
-- DROP TABLE IF EXISTS bot_backups;
-- ALTER TABLE media_files DROP COLUMN IF EXISTS file_unique_id;
-- ALTER TABLE media_files DROP COLUMN IF EXISTS source_channel_id;
-- ALTER TABLE media_files DROP COLUMN IF EXISTS source_message_id;
-- ALTER TABLE sponsor_media_files DROP COLUMN IF EXISTS file_unique_id;
