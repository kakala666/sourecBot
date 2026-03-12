"""
广播服务核心逻辑
管理广播任务的创建、执行、停止和状态查询
"""
import asyncio
import base64
import hashlib
import logging
import random
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


class BroadcastTask:
    """单个广播任务的状态容器"""

    def __init__(self, task_id: str, total_recipients: int):
        self.task_id = task_id
        self.status: str = "running"
        self.total_recipients = total_recipients
        self.sent_count: int = 0
        self.success_count: int = 0
        self.fail_count: int = 0
        self.created_at: datetime = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self._stop_flag: bool = False
        self._asyncio_task: Optional[asyncio.Task] = None

    @property
    def progress(self) -> float:
        if self.total_recipients == 0:
            return 100.0
        return round(self.sent_count / self.total_recipients * 100, 1)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "total_recipients": self.total_recipients,
            "sent_count": self.sent_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }

    def request_stop(self):
        self._stop_flag = True


class BroadcastService:
    """广播服务，管理广播任务生命周期"""

    def __init__(self, bot: Bot):
        self.bot = bot
        # 任务存储：task_id -> BroadcastTask
        self._tasks: dict[str, BroadcastTask] = {}
        self._running_task_id: Optional[str] = None

    def _generate_task_id(self) -> str:
        """生成任务 ID，格式: bc_{timestamp}_{hash4}"""
        ts = int(time.time())
        h = hashlib.md5(f"{ts}{random.random()}".encode()).hexdigest()[:4]
        return f"bc_{ts}_{h}"

    def get_task(self, task_id: str) -> Optional[BroadcastTask]:
        return self._tasks.get(task_id)

    def has_running_task(self) -> bool:
        if self._running_task_id is None:
            return False
        task = self._tasks.get(self._running_task_id)
        if task and task.status == "running":
            return True
        # 已结束，清理标记
        self._running_task_id = None
        return False

    @staticmethod
    def _decode_image(image_data: str) -> bytes:
        """解码 base64 图片，支持带 data URI 前缀"""
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]
        return base64.b64decode(image_data)

    @staticmethod
    def _build_keyboard(
        buttons: Optional[list[list[dict]]],
    ) -> Optional[InlineKeyboardMarkup]:
        """构建内联键盘"""
        if not buttons:
            return None
        rows = []
        for row in buttons:
            kb_row = [
                InlineKeyboardButton(text=btn["text"], url=btn["url"])
                for btn in row
            ]
            rows.append(kb_row)
        return InlineKeyboardMarkup(inline_keyboard=rows)

    async def _fetch_recipient_ids(
        self,
        user_ids: Optional[list[int]],
        max_recipients: int,
    ) -> list[int]:
        """获取接收者 telegram_id 列表，必要时随机抽取"""
        async with AsyncSessionLocal() as session:
            if user_ids:
                # 使用指定用户列表
                return user_ids

            # 从数据库查询全部用户 telegram_id
            result = await session.execute(
                select(User.telegram_id)
            )
            all_ids = [row[0] for row in result.fetchall()]

            if max_recipients > 0 and max_recipients < len(all_ids):
                # 随机抽取
                return random.sample(all_ids, max_recipients)
            return all_ids

    async def create_task(
        self,
        image: Optional[str],
        caption: str,
        buttons: Optional[list[list[dict]]],
        config: dict,
        user_ids: Optional[list[int]],
    ) -> BroadcastTask:
        """创建并启动广播任务"""
        rate = config["rate"]
        interval = config["interval"]
        max_recipients = config["max_recipients"]

        # 获取接收者列表
        recipients = await self._fetch_recipient_ids(user_ids, max_recipients)
        if not recipients:
            raise ValueError("没有可发送的目标用户")

        # 解码图片（如果有）
        image_bytes: Optional[bytes] = None
        if image:
            try:
                image_bytes = self._decode_image(image)
            except Exception as e:
                raise ValueError(f"Invalid image: base64 decode failed - {e}")

        # 创建任务
        task_id = self._generate_task_id()
        task = BroadcastTask(task_id, len(recipients))
        self._tasks[task_id] = task
        self._running_task_id = task_id

        # 构建键盘
        keyboard = self._build_keyboard(buttons)

        # 启动后台协程
        task._asyncio_task = asyncio.create_task(
            self._execute_broadcast(
                task, recipients, image_bytes, caption, keyboard, rate, interval,
            )
        )
        return task

    async def _send_to_user(
        self,
        chat_id: int,
        caption: str,
        keyboard: Optional[InlineKeyboardMarkup],
        file_id: Optional[str] = None,
    ) -> bool:
        """向单个用户发送消息，HTML 解析失败自动回退纯文本"""
        try:
            if file_id:
                # 带图片发送
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            else:
                # 纯文本发送
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            return True
        except Exception as html_err:
            # HTML 解析失败，回退纯文本重发
            if "can't parse" in str(html_err).lower() or "parse" in str(html_err).lower():
                try:
                    if file_id:
                        await self.bot.send_photo(
                            chat_id=chat_id,
                            photo=file_id,
                            caption=caption,
                            reply_markup=keyboard,
                        )
                    else:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=caption,
                            reply_markup=keyboard,
                        )
                    return True
                except Exception:
                    return False
            # 其他错误（用户已封锁 bot 等）
            logger.debug("发送失败 chat_id=%s: %s", chat_id, html_err)
            return False

    async def _execute_broadcast(
        self,
        task: BroadcastTask,
        recipients: list[int],
        image_bytes: Optional[bytes],
        caption: str,
        keyboard: Optional[InlineKeyboardMarkup],
        rate: int,
        interval: int,
    ):
        """后台执行广播任务"""
        task.started_at = datetime.now(timezone.utc)
        tmp_path: Optional[str] = None
        file_id: Optional[str] = None

        try:
            # 如果有图片，先上传到存储频道获取 file_id
            if image_bytes:
                tmp_path = self._save_temp_image(image_bytes)
                try:
                    msg = await self.bot.send_photo(
                        chat_id=settings.STORAGE_CHANNEL_ID,
                        photo=FSInputFile(tmp_path),
                        caption="[广播图片]",
                    )
                    file_id = msg.photo[-1].file_id
                except Exception as e:
                    logger.error("上传广播图片失败: %s", e)
                    task.status = "failed"
                    raise

            remaining = recipients

            # 逐用户发送
            batch_count = 0
            for uid in remaining:
                if task._stop_flag:
                    task.status = "stopped"
                    break

                success = await self._send_to_user(uid, caption, keyboard, file_id)
                task.sent_count += 1
                if success:
                    task.success_count += 1
                else:
                    task.fail_count += 1

                batch_count += 1
                # 每条间隔 0.5 秒
                await asyncio.sleep(0.5)
                # 达到批次上限，暂停 interval 秒
                if batch_count >= rate:
                    batch_count = 0
                    if interval > 0:
                        await asyncio.sleep(interval)

            # 正常完成
            if task.status == "running":
                task.status = "completed"

        except Exception as e:
            logger.error("广播任务 %s 异常: %s", task.task_id, e)
            task.status = "failed"
        finally:
            task.finished_at = datetime.now(timezone.utc)
            self._running_task_id = None
            # 清理临时文件
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass

    @staticmethod
    def _save_temp_image(data: bytes) -> str:
        """保存图片到临时文件，返回路径"""
        fd, path = tempfile.mkstemp(suffix=".jpg")
        with open(fd, "wb") as f:
            f.write(data)
        return path

    def stop_task(self, task_id: str) -> Optional[BroadcastTask]:
        """停止广播任务"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        if task.status == "running":
            task.request_stop()
        return task
