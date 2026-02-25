"""
存储频道扫描脚本 v2：智能扫描，从最新消息向前扫描

策略：
1. 先发一条测试消息到存储频道，获取当前最大 message_id
2. 从最大 message_id 向前扫描（forward 到自身，提取 file_unique_id，然后删除）
3. 对于没有 file_unique_id 的大文件，直接用 telegram_file_id 前缀匹配

用法：
    cd /root/sourcebot/backend
    python backfill_v2.py
"""
import asyncio
import hashlib
import logging

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


async def get_max_message_id(bot: Bot, channel_id: int) -> int:
    """发送一条消息获取当前最大 message_id，然后删除"""
    msg = await bot.send_message(chat_id=channel_id, text="__scan_probe__")
    max_id = msg.message_id
    await bot.delete_message(chat_id=channel_id, message_id=max_id)
    return max_id


def extract_file_info(message) -> list[dict]:
    """从消息中提取所有文件信息"""
    results = []
    if message.photo:
        p = message.photo[-1]
        results.append({
            "file_id": p.file_id,
            "file_unique_id": p.file_unique_id,
            "file_type": "photo",
        })
    if message.video:
        v = message.video
        results.append({
            "file_id": v.file_id,
            "file_unique_id": v.file_unique_id,
            "file_type": "video",
        })
    if message.animation:
        a = message.animation
        results.append({
            "file_id": a.file_id,
            "file_unique_id": a.file_unique_id,
            "file_type": "animation",
        })
    if message.document:
        d = message.document
        results.append({
            "file_id": d.file_id,
            "file_unique_id": d.file_unique_id,
            "file_type": "document",
        })
    return results


async def scan_storage_channel(bot: Bot):
    """扫描存储频道，建立完整的 file_unique_id + source_message_id 映射"""
    channel_id = settings.STORAGE_CHANNEL_ID

    # 获取最大 message_id
    max_msg_id = await get_max_message_id(bot, channel_id)
    log.info(f"存储频道最大 message_id: {max_msg_id}")

    # 加载所有需要补全的 media_files
    async with engine.begin() as conn:
        # 需要 source_message_id 的记录
        need_msg_rows = (await conn.execute(text(
            "SELECT id, telegram_file_id, file_unique_id FROM media_files "
            "WHERE source_message_id IS NULL"
        ))).fetchall()

    log.info(f"需要补全 source_message_id 的 media_files: {len(need_msg_rows)}")

    if not need_msg_rows:
        log.info("全部已补全，跳过")
        return

    # 建立两个索引：
    # 1. file_unique_id → [(mf_id, telegram_file_id), ...]  (有 unique_id 的)
    # 2. telegram_file_id → mf_id  (所有的，用于直接匹配)
    uid_index: dict[str, list[int]] = {}
    fid_index: dict[str, int] = {}

    for mf_id, tg_fid, f_uid in need_msg_rows:
        fid_index[tg_fid] = mf_id
        if f_uid:
            uid_index.setdefault(f_uid, []).append(mf_id)

    log.info(f"有 file_unique_id 的: {len(uid_index)}, 总 file_id 索引: {len(fid_index)}")

    matched = 0
    scanned = 0
    consecutive_fails = 0

    # 从最新消息向前扫描
    for msg_id in range(max_msg_id, 0, -1):
        try:
            # forward 到自身
            forwarded = await bot.forward_message(
                chat_id=channel_id,
                from_chat_id=channel_id,
                message_id=msg_id,
            )
            consecutive_fails = 0
            scanned += 1

            files = extract_file_info(forwarded)

            # 删除转发的消息
            try:
                await bot.delete_message(
                    chat_id=channel_id,
                    message_id=forwarded.message_id,
                )
            except Exception:
                pass

            for f in files:
                matched_ids = []

                # 方法1: file_unique_id 匹配
                if f["file_unique_id"] in uid_index:
                    matched_ids.extend(uid_index.pop(f["file_unique_id"]))

                # 方法2: file_id 直接匹配（同一个 Bot 的 file_id 完全相同）
                if f["file_id"] in fid_index:
                    mid = fid_index.pop(f["file_id"])
                    if mid not in matched_ids:
                        matched_ids.append(mid)

                if matched_ids:
                    async with engine.begin() as conn:
                        for mf_id in matched_ids:
                            await conn.execute(text(
                                "UPDATE media_files "
                                "SET source_channel_id = :ch, source_message_id = :msg, "
                                "    file_unique_id = COALESCE(NULLIF(file_unique_id, ''), :uid) "
                                "WHERE id = :id"
                            ), {
                                "ch": channel_id,
                                "msg": msg_id,
                                "uid": f["file_unique_id"],
                                "id": mf_id,
                            })
                    matched += len(matched_ids)
                    log.info(
                        f"  匹配: msg_id={msg_id}, uid={f['file_unique_id']}, "
                        f"type={f['file_type']}, mf_ids={matched_ids}"
                    )

            # 全部匹配完就提前退出
            remaining = len(fid_index)
            if remaining == 0:
                log.info("所有文件已匹配完毕!")
                break

        except Exception:
            consecutive_fails += 1
            # 连续 200 次失败说明已经到了频道最早的消息之前
            if consecutive_fails >= 200:
                log.info(f"连续 {consecutive_fails} 次失败，停止扫描")
                break

        # 限流：每秒约 6 个请求
        await asyncio.sleep(0.15)

        # 每 100 条打印进度
        if scanned % 100 == 0:
            log.info(f"  进度: 扫描={scanned}, 匹配={matched}, 剩余={len(fid_index)}")

    log.info(f"扫描完成: 扫描消息={scanned}, 匹配={matched}, 未匹配={len(fid_index)}")
    if fid_index:
        # 打印未匹配的 file_id 前 5 个
        for fid, mf_id in list(fid_index.items())[:5]:
            log.warning(f"  未匹配: mf_id={mf_id}, file_id={fid[:50]}...")


async def main():
    log.info("========================================")
    log.info("SourceBot 存储频道扫描 v2")
    log.info("========================================")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        me = await bot.get_me()
        log.info(f"Bot: @{me.username} (id={me.id})")
        await scan_storage_channel(bot)

        # 最终统计
        async with engine.begin() as conn:
            stats = (await conn.execute(text(
                "SELECT "
                "  count(*) as total, "
                "  count(file_unique_id) FILTER (WHERE file_unique_id IS NOT NULL AND file_unique_id <> '') as has_uid, "
                "  count(source_message_id) FILTER (WHERE source_message_id IS NOT NULL) as has_msg "
                "FROM media_files"
            ))).fetchone()
        log.info(f"最终状态: total={stats[0]}, has_file_unique_id={stats[1]}, has_source_message_id={stats[2]}")

        log.info("========================================")
        log.info("完成!")
        log.info("========================================")
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
