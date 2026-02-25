"""
数据补全脚本：为 media_files 和 sponsor 相关表补全 file_unique_id

必须在当前 Bot token 还有效时运行。

用法：
    cd /root/sourcebot/backend
    python backfill_file_data.py

做的事情：
1. 对每个 media_files.telegram_file_id 调用 bot.get_file() 获取 file_unique_id
2. 对每个 sponsors.telegram_file_id 获取 file_unique_id（存入新增的 file_unique_id 列）
3. 对每个 sponsor_media_files.telegram_file_id 获取 file_unique_id
4. 遍历存储频道历史消息，建立 file_unique_id → message_id 映射
5. 回填 media_files.source_channel_id + source_message_id
"""
import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import text

from app.config import settings
from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


async def get_file_unique_id(bot: Bot, file_id: str) -> str | None:
    """通过 bot.get_file 获取 file_unique_id"""
    try:
        f = await bot.get_file(file_id)
        return f.file_unique_id
    except Exception as e:
        log.warning(f"get_file failed for {file_id[:40]}...: {e}")
        return None


async def backfill_media_files(bot: Bot):
    """补全 media_files 表的 file_unique_id"""
    log.info("=== 开始补全 media_files.file_unique_id ===")

    async with engine.begin() as conn:
        rows = (await conn.execute(text(
            "SELECT id, telegram_file_id FROM media_files "
            "WHERE file_unique_id IS NULL OR file_unique_id = ''"
        ))).fetchall()

    log.info(f"需要补全的 media_files: {len(rows)}")
    success = 0
    fail = 0

    for row_id, file_id in rows:
        unique_id = await get_file_unique_id(bot, file_id)
        if unique_id:
            async with engine.begin() as conn:
                await conn.execute(text(
                    "UPDATE media_files SET file_unique_id = :uid WHERE id = :id"
                ), {"uid": unique_id, "id": row_id})
            success += 1
        else:
            fail += 1
        # 避免触发 Telegram 限流
        await asyncio.sleep(0.1)

    log.info(f"media_files 补全完成: 成功={success}, 失败={fail}")


async def backfill_sponsor_media_files(bot: Bot):
    """补全 sponsor_media_files 表的 file_unique_id"""
    log.info("=== 开始补全 sponsor_media_files.file_unique_id ===")

    async with engine.begin() as conn:
        rows = (await conn.execute(text(
            "SELECT id, telegram_file_id FROM sponsor_media_files "
            "WHERE file_unique_id IS NULL OR file_unique_id = ''"
        ))).fetchall()

    log.info(f"需要补全的 sponsor_media_files: {len(rows)}")
    success = 0
    fail = 0

    for row_id, file_id in rows:
        unique_id = await get_file_unique_id(bot, file_id)
        if unique_id:
            async with engine.begin() as conn:
                await conn.execute(text(
                    "UPDATE sponsor_media_files SET file_unique_id = :uid WHERE id = :id"
                ), {"uid": unique_id, "id": row_id})
            success += 1
        else:
            fail += 1
        await asyncio.sleep(0.1)

    log.info(f"sponsor_media_files 补全完成: 成功={success}, 失败={fail}")


async def ensure_sponsors_file_unique_id_column():
    """确保 sponsors 表有 file_unique_id 列"""
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'sponsors' AND column_name = 'file_unique_id'"
        ))
        if not result.fetchone():
            log.info("为 sponsors 表添加 file_unique_id 列")
            await conn.execute(text(
                "ALTER TABLE sponsors ADD COLUMN file_unique_id VARCHAR(100)"
            ))


async def backfill_sponsors(bot: Bot):
    """补全 sponsors 表的 file_unique_id（单媒体广告）"""
    log.info("=== 开始补全 sponsors.file_unique_id ===")

    await ensure_sponsors_file_unique_id_column()

    async with engine.begin() as conn:
        rows = (await conn.execute(text(
            "SELECT id, telegram_file_id FROM sponsors "
            "WHERE telegram_file_id IS NOT NULL "
            "AND (file_unique_id IS NULL OR file_unique_id = '')"
        ))).fetchall()

    log.info(f"需要补全的 sponsors: {len(rows)}")
    success = 0
    fail = 0

    for row_id, file_id in rows:
        unique_id = await get_file_unique_id(bot, file_id)
        if unique_id:
            async with engine.begin() as conn:
                await conn.execute(text(
                    "UPDATE sponsors SET file_unique_id = :uid WHERE id = :id"
                ), {"uid": unique_id, "id": row_id})
            success += 1
        else:
            fail += 1
        await asyncio.sleep(0.1)

    log.info(f"sponsors 补全完成: 成功={success}, 失败={fail}")


async def backfill_source_message_ids(bot: Bot):
    """
    遍历存储频道消息，建立 file_unique_id → message_id 映射，
    回填 media_files.source_channel_id + source_message_id

    策略：用 bot.forward_message 不可行（不知道 message_id）。
    改用：从存储频道逐条 copy_message 到自己，提取 file_unique_id。

    但 Bot API 没有 getHistory。所以我们用另一种方式：
    从 message_id=1 开始尝试 forward，直到连续 50 次失败为止。
    """
    log.info("=== 开始扫描存储频道，建立 message_id 映射 ===")

    channel_id = settings.STORAGE_CHANNEL_ID

    # 先加载所有需要匹配的 file_unique_id
    async with engine.begin() as conn:
        rows = (await conn.execute(text(
            "SELECT id, file_unique_id FROM media_files "
            "WHERE file_unique_id IS NOT NULL AND file_unique_id != '' "
            "AND source_message_id IS NULL"
        ))).fetchall()

    if not rows:
        log.info("所有 media_files 都已有 source_message_id，跳过")
        return

    # 建立 file_unique_id → [media_file_id, ...] 的映射
    uid_to_mf_ids: dict[str, list[int]] = {}
    for mf_id, uid in rows:
        uid_to_mf_ids.setdefault(uid, []).append(mf_id)

    log.info(f"需要匹配的 file_unique_id: {len(uid_to_mf_ids)}")

    # 扫描存储频道：从 message_id 1 开始，逐个尝试 forward 到自己
    # 用 copy_message 到 STORAGE_CHANNEL_ID 自身（然后删除）
    matched = 0
    consecutive_fails = 0
    msg_id = 0

    while consecutive_fails < 100:
        msg_id += 1
        try:
            # forward 到存储频道自身来获取消息内容
            forwarded = await bot.forward_message(
                chat_id=channel_id,
                from_chat_id=channel_id,
                message_id=msg_id,
            )

            consecutive_fails = 0

            # 提取 file_unique_id
            unique_ids = []
            if forwarded.photo:
                unique_ids.append(forwarded.photo[-1].file_unique_id)
            if forwarded.video:
                unique_ids.append(forwarded.video.file_unique_id)
            if forwarded.animation:
                unique_ids.append(forwarded.animation.file_unique_id)
            if forwarded.document:
                unique_ids.append(forwarded.document.file_unique_id)

            # 删除转发的消息
            try:
                await bot.delete_message(chat_id=channel_id, message_id=forwarded.message_id)
            except Exception:
                pass

            # 匹配
            for uid in unique_ids:
                if uid in uid_to_mf_ids:
                    mf_ids = uid_to_mf_ids.pop(uid)
                    async with engine.begin() as conn:
                        for mf_id in mf_ids:
                            await conn.execute(text(
                                "UPDATE media_files "
                                "SET source_channel_id = :ch, source_message_id = :msg "
                                "WHERE id = :id"
                            ), {"ch": channel_id, "msg": msg_id, "id": mf_id})
                    matched += len(mf_ids)
                    log.info(f"  匹配: msg_id={msg_id}, uid={uid}, media_file_ids={mf_ids}")

            # 全部匹配完就提前退出
            if not uid_to_mf_ids:
                log.info("所有 file_unique_id 已匹配完毕")
                break

        except Exception:
            consecutive_fails += 1

        # 限流
        await asyncio.sleep(0.15)

    log.info(f"存储频道扫描完成: 扫描到 msg_id={msg_id}, 匹配={matched}, 未匹配={len(uid_to_mf_ids)}")
    if uid_to_mf_ids:
        log.warning(f"未匹配的 file_unique_id: {list(uid_to_mf_ids.keys())[:10]}...")


async def main():
    log.info("========================================")
    log.info("SourceBot 数据补全脚本")
    log.info("========================================")
    log.info(f"BOT_TOKEN: ...{settings.BOT_TOKEN[-10:]}")
    log.info(f"STORAGE_CHANNEL_ID: {settings.STORAGE_CHANNEL_ID}")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        me = await bot.get_me()
        log.info(f"Bot: @{me.username} (id={me.id})")

        # 第 1 步：补全 file_unique_id
        await backfill_media_files(bot)
        await backfill_sponsor_media_files(bot)
        await backfill_sponsors(bot)

        # 第 2 步：扫描存储频道，回填 source_message_id
        await backfill_source_message_ids(bot)

        log.info("========================================")
        log.info("全部完成!")
        log.info("========================================")
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
