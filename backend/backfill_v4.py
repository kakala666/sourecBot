"""
存储频道扫描 v4：两阶段匹配

阶段1: 扫描存储频道 msg_id 200-600，建立 file_unique_id → msg_id 映射
阶段2: 对 51 个大视频，用 send_video(file_id=...) 发到存储频道，
       从新消息提取 file_unique_id，再从阶段1的映射中找到原始 msg_id
"""
import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InputFile
from sqlalchemy import text

from app.config import settings
from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


async def main():
    log.info("=== 存储频道扫描 v4: 两阶段匹配 ===")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    channel_id = settings.STORAGE_CHANNEL_ID

    try:
        me = await bot.get_me()
        log.info(f"Bot: @{me.username}")

        # ===== 阶段1: 扫描存储频道，建立 file_unique_id → msg_id 映射 =====
        log.info("--- 阶段1: 扫描存储频道 ---")
        uid_to_msgid: dict[str, int] = {}
        scanned = 0

        for msg_id in range(200, 600):
            try:
                forwarded = await bot.forward_message(
                    chat_id=channel_id,
                    from_chat_id=channel_id,
                    message_id=msg_id,
                )
                scanned += 1

                uid = None
                if forwarded.video:
                    uid = forwarded.video.file_unique_id
                elif forwarded.photo:
                    uid = forwarded.photo[-1].file_unique_id
                elif forwarded.animation:
                    uid = forwarded.animation.file_unique_id
                elif forwarded.document:
                    uid = forwarded.document.file_unique_id

                if uid:
                    uid_to_msgid[uid] = msg_id

                # 删除转发
                try:
                    await bot.delete_message(chat_id=channel_id, message_id=forwarded.message_id)
                except Exception:
                    pass

            except Exception:
                pass

            await asyncio.sleep(0.12)

            if scanned > 0 and scanned % 50 == 0:
                log.info(f"  阶段1进度: msg_id={msg_id}, 扫描={scanned}, 映射={len(uid_to_msgid)}")

        log.info(f"阶段1完成: 扫描={scanned}, 映射条目={len(uid_to_msgid)}")

        # ===== 阶段2: 对未匹配的大视频，发送到频道获取 file_unique_id =====
        log.info("--- 阶段2: 匹配大视频 ---")

        async with engine.begin() as conn:
            rows = (await conn.execute(text(
                "SELECT id, telegram_file_id, media_type FROM media_files "
                "WHERE source_message_id IS NULL"
            ))).fetchall()

        log.info(f"需要匹配: {len(rows)} 个文件")

        matched = 0
        for mf_id, tg_fid, media_type in rows:
            try:
                # 用 file_id 发送到存储频道
                if media_type == 'video':
                    sent = await bot.send_video(chat_id=channel_id, video=tg_fid)
                    uid = sent.video.file_unique_id if sent.video else None
                elif media_type == 'photo':
                    sent = await bot.send_photo(chat_id=channel_id, photo=tg_fid)
                    uid = sent.photo[-1].file_unique_id if sent.photo else None
                elif media_type == 'animation':
                    sent = await bot.send_animation(chat_id=channel_id, animation=tg_fid)
                    uid = sent.animation.file_unique_id if sent.animation else None
                else:
                    sent = await bot.send_document(chat_id=channel_id, document=tg_fid)
                    uid = sent.document.file_unique_id if sent.document else None

                # 删除发送的消息
                try:
                    await bot.delete_message(chat_id=channel_id, message_id=sent.message_id)
                except Exception:
                    pass

                if uid:
                    log.info(f"  mf_id={mf_id}: file_unique_id={uid}")

                    # 从阶段1映射中查找原始 msg_id
                    orig_msg_id = uid_to_msgid.get(uid)

                    async with engine.begin() as conn:
                        if orig_msg_id:
                            await conn.execute(text(
                                "UPDATE media_files "
                                "SET source_channel_id = :ch, source_message_id = :msg, "
                                "    file_unique_id = :uid "
                                "WHERE id = :id"
                            ), {"ch": channel_id, "msg": orig_msg_id, "uid": uid, "id": mf_id})
                            matched += 1
                            log.info(f"    -> 匹配到 msg_id={orig_msg_id}")
                        else:
                            # 没找到原始消息，至少保存 file_unique_id
                            await conn.execute(text(
                                "UPDATE media_files SET file_unique_id = :uid WHERE id = :id"
                            ), {"uid": uid, "id": mf_id})
                            log.warning(f"    -> 未找到原始消息，仅保存 file_unique_id")

            except Exception as e:
                log.error(f"  mf_id={mf_id}: 发送失败: {e}")

            await asyncio.sleep(0.3)

        log.info(f"阶段2完成: 匹配={matched}, 未匹配={len(rows) - matched}")

        # 最终统计
        async with engine.begin() as conn:
            stats = (await conn.execute(text(
                "SELECT count(*) as total, "
                "  count(file_unique_id) FILTER (WHERE file_unique_id IS NOT NULL AND file_unique_id <> '') as has_uid, "
                "  count(source_message_id) FILTER (WHERE source_message_id IS NOT NULL) as has_msg "
                "FROM media_files"
            ))).fetchone()
        log.info(f"最终: total={stats[0]}, has_uid={stats[1]}, has_msg={stats[2]}")

    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
