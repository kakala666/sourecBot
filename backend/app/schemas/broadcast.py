"""
广播功能 Pydantic 模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class InlineButton(BaseModel):
    """内联按钮"""
    text: str = Field(..., description="按钮显示文字")
    url: str = Field(..., description="按钮链接地址")


class SendConfig(BaseModel):
    """发送配置"""
    rate: int = Field(..., ge=1, description="每批发送条数")
    interval: int = Field(..., ge=0, description="每批之间暂停秒数")
    max_recipients: int = Field(..., ge=0, description="发送人数上限，0 表示全部用户")


class BroadcastRequest(BaseModel):
    """创建广播请求"""
    image: Optional[str] = Field(None, description="base64 编码的图片数据，可选")
    caption: str = Field(..., description="消息文本内容，支持 HTML 格式")
    buttons: Optional[list[list[InlineButton]]] = Field(None, description="内联键盘按钮，二维数组")
    config: SendConfig
    user_ids: Optional[list[int]] = Field(None, description="指定接收用户 ID 列表，为空则发送给全部用户")


class BroadcastTaskInfo(BaseModel):
    """广播任务基本信息"""
    task_id: str
    status: str
    total_recipients: int
    sent_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    progress: float = 0.0
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class BroadcastCreateResponse(BaseModel):
    """创建广播响应"""
    code: int = 200
    data: dict


class BroadcastStatusResponse(BaseModel):
    """广播状态响应"""
    code: int = 200
    data: BroadcastTaskInfo


class BroadcastStopResponse(BaseModel):
    """停止广播响应"""
    code: int = 200
    data: dict


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
