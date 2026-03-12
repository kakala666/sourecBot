"""
广播 API 路由
提供创建广播、查询状态、停止广播三个端点
使用 X-API-Key 认证
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.config import settings
from app.schemas.broadcast import (
    BroadcastCreateResponse,
    BroadcastRequest,
    BroadcastStatusResponse,
    BroadcastStopResponse,
)
from app.services.broadcast import BroadcastService

router = APIRouter()


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """验证 API Key"""
    if x_api_key != settings.BROADCAST_API_KEY:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "Invalid API key"},
        )
    return x_api_key


def get_broadcast_service(request: Request) -> BroadcastService:
    """从 app.state 获取广播服务实例"""
    return request.app.state.broadcast_service


@router.post(
    "",
    response_model=BroadcastCreateResponse,
    summary="创建广播任务",
)
async def create_broadcast(
    body: BroadcastRequest,
    _key: str = Depends(verify_api_key),
    svc: BroadcastService = Depends(get_broadcast_service),
):
    """创建并启动一个新的广播任务"""
    # 检查是否有正在运行的任务
    if svc.has_running_task():
        raise HTTPException(
            status_code=409,
            detail={"code": 409, "message": "A broadcast task is already running"},
        )

    # 转换 buttons 为 dict 列表
    buttons = None
    if body.buttons:
        buttons = [[btn.model_dump() for btn in row] for row in body.buttons]

    try:
        task = await svc.create_task(
            image=body.image,
            caption=body.caption,
            buttons=buttons,
            config=body.config.model_dump(),
            user_ids=body.user_ids if body.user_ids else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "message": str(e)},
        )

    return {
        "code": 200,
        "data": {
            "task_id": task.task_id,
            "total_recipients": task.total_recipients,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
        },
    }


@router.get(
    "/{task_id}",
    response_model=BroadcastStatusResponse,
    summary="查询广播任务状态",
)
async def get_broadcast_status(
    task_id: str,
    _key: str = Depends(verify_api_key),
    svc: BroadcastService = Depends(get_broadcast_service),
):
    """查询指定广播任务的实时状态"""
    task = svc.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "Task not found"},
        )
    return {"code": 200, "data": task.to_dict()}


@router.post(
    "/{task_id}/stop",
    response_model=BroadcastStopResponse,
    summary="停止广播任务",
)
async def stop_broadcast(
    task_id: str,
    _key: str = Depends(verify_api_key),
    svc: BroadcastService = Depends(get_broadcast_service),
):
    """停止正在运行的广播任务"""
    task = svc.stop_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "Task not found"},
        )
    return {
        "code": 200,
        "data": {
            "task_id": task.task_id,
            "status": task.status,
            "sent_count": task.sent_count,
            "success_count": task.success_count,
            "fail_count": task.fail_count,
        },
    }
