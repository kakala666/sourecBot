"""
配置管理模块
从 .env 文件加载环境变量
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # Bot 配置
    BOT_TOKEN: str
    STORAGE_CHANNEL_ID: int  # 私有存储频道 ID
    STATS_GROUP_ID: int      # 统计群 ID
    SERVICE_GROUP_ID: int    # 客服群 ID
    
    # 数据库配置
    DATABASE_URL: str
    
    # JWT 配置
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 小时
    ALGORITHM: str = "HS256"
    
    # 服务端口
    API_PORT: int = 9000
    FRONTEND_PORT: int = 3001
    
    # 文件限制 (字节)
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024   # 10MB
    MAX_VIDEO_SIZE: int = 50 * 1024 * 1024   # 50MB
    
    # 上传目录
    UPLOAD_DIR: str = "uploads"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
