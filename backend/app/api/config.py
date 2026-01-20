"""
系统配置 API
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import Config
from app.api.auth import get_current_admin


router = APIRouter()


class ConfigItem(BaseModel):
    """配置项"""
    key: str
    value: str | None
    description: str | None
    
    class Config:
        from_attributes = True


class ConfigUpdate(BaseModel):
    """更新配置请求"""
    value: str


@router.get("", response_model=List[ConfigItem])
async def list_configs(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取所有配置"""
    result = await db.execute(select(Config))
    configs = result.scalars().all()
    return configs


@router.get("/{key}", response_model=ConfigItem)
async def get_config(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取单个配置"""
    result = await db.execute(select(Config).where(Config.key == key))
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    return config


@router.patch("/{key}", response_model=ConfigItem)
async def update_config(
    key: str,
    data: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """更新配置"""
    result = await db.execute(select(Config).where(Config.key == key))
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    config.value = data.value
    await db.commit()
    await db.refresh(config)
    
    return config
