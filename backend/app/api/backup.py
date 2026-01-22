"""
备份管理 API
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import BotBackup
from app.api.auth import get_current_admin
from app.services.backup_sync import backup_sync_service


router = APIRouter()


class BackupConfigCreate(BaseModel):
    """创建备份配置请求"""
    token: str


class BackupConfigResponse(BaseModel):
    """备份配置响应"""
    id: int
    backup_bot_username: Optional[str]
    backup_bot_id: Optional[int]
    is_active: bool
    sync_status: str
    total_count: int
    synced_count: int
    failed_count: int
    error_message: Optional[str]
    last_synced_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class BackupStatusResponse(BaseModel):
    """备份状态响应"""
    has_config: bool
    config: Optional[BackupConfigResponse]
    is_syncing: bool


class MessageResponse(BaseModel):
    """通用消息响应"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


@router.get("/status", response_model=BackupStatusResponse)
async def get_backup_status(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin)
):
    """获取备份状态"""
    result = await db.execute(select(BotBackup).limit(1))
    backup = result.scalar_one_or_none()
    
    return BackupStatusResponse(
        has_config=backup is not None,
        config=BackupConfigResponse.model_validate(backup) if backup else None,
        is_syncing=backup_sync_service._is_syncing
    )


@router.post("/config", response_model=MessageResponse)
async def create_backup_config(
    data: BackupConfigCreate,
    _: None = Depends(get_current_admin)
):
    """创建备份配置"""
    result = await backup_sync_service.create_backup_config(data.token)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return MessageResponse(success=True, message="备份配置已创建")


@router.delete("/config", response_model=MessageResponse)
async def delete_backup_config(
    _: None = Depends(get_current_admin)
):
    """删除备份配置"""
    result = await backup_sync_service.delete_backup_config()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return MessageResponse(success=True, message="备份配置已删除")


@router.post("/sync/start", response_model=MessageResponse)
async def start_sync(
    _: None = Depends(get_current_admin)
):
    """开始同步"""
    result = await backup_sync_service.start_sync()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return MessageResponse(success=True, message=result.get("message", "同步已开始"))


@router.post("/sync/stop", response_model=MessageResponse)
async def stop_sync(
    _: None = Depends(get_current_admin)
):
    """停止同步"""
    result = await backup_sync_service.stop_sync()
    return MessageResponse(success=True, message=result.get("message", "正在停止"))


@router.post("/switch/backup", response_model=MessageResponse)
async def switch_to_backup(
    _: None = Depends(get_current_admin)
):
    """切换到备份 Bot"""
    result = await backup_sync_service.switch_to_backup()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return MessageResponse(success=True, message=result.get("message", "已切换到备份 Bot"))


@router.post("/switch/primary", response_model=MessageResponse)
async def switch_to_primary(
    _: None = Depends(get_current_admin)
):
    """切换回主 Bot"""
    result = await backup_sync_service.switch_to_primary()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return MessageResponse(success=True, message=result.get("message", "已切换回主 Bot"))
