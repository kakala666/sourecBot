"""
存储频道扫描 v3：补全剩余 51 个大视频的 file_unique_id + source_message_id

原理：
- 51 个大视频无法通过 bot.getFile() 获取 file_unique_id（>20MB 限制）
- 但它们存在于存储频道中，且当前 Bot 发送时的 file_id 与数据库中存储的一致
- 所以：正向遍历存储频道 msg_id 1~700，forward 到频道自身，
  提取 file_id 与数据库比对，匹配后回填 file_unique_id + source_message_id
- forward 的消息立即删除，不留残留

安全措施：
- dry_run 模式：默认只打印匹配结果，不写数据库
- 加 --commit 参数才真正写入
- 所有 UPDATE 只填充空字段，不覆盖已有数据

用法：
    cd /root/sourcebot/backend
    source .venv/bin/activate

    # 先 dry-run 验证
    python backfill_v3.py

    # 确认无误后真正写入
    python backfill_v3.py --commit
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

# 已知内容范围：v1 扫描匹配到的 source_message_id 在 273~549
SCAN_START = 1
SCAN_END = 700


async def main():
    commit_mode = "--commit" in sys.argv
    mode_label = "COMMIT（真正写入）" if commit_mode else "DRY-RUN（只读验证）"

    log.info(f"=== 存储频道扫描 v3 [{mode_label}] ===")
    log.info(f"扫描范围: msg_id {SCAN_START} ~ {SCAN_END}")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    channel_id = settings.STORAGE_CHANNEL_ID

    try:
        me = await bot.get_me()
        log.info(f"Bot: @{me.username} (id={me.id})")

        # 加载未匹配的 media_files
        async with engine.begin() as conn:
            rows = (await conn.execute(text(
                "SELECT id, telegram_file_id FROM media_files "
                "WHERE source_message_id IS NULL"
            ))).fetchall()

        if not rows:
            log.info("所有 media_files 都已有 source_message_id，无需操作")
            return

        # file_id → mf_id 索引
        fid_index = {fid: mf_id for mf_id, fid in rows}
        log.info(f"需要匹配: {len(fid_index)} 个文件")

        matched = 0
        scanned = 0
        match_results = []  # 记录所有匹配结果

        for msg_id in range(SCAN_START, SCAN_END + 1):
            try:
                forwarded = await bot.forward_message(
                    chat_id=channel_id,
                    from_chat_id=channel_id,
                    message_id=msg_id,
                )
                scanned += 1

                # 提取文件信息
                files = []
                if forwarded.video:
                    v = forwarded.video
                    files.append((v.file_id, v.file_unique_id))
                if forwarded.photo:
                    p = forwarded.photo[-1]
                    files.append((p.file_id, p.file_unique_id))
                if forwarded.document:
                    d = forwarded.document
                    files.append((d.file_id, d.file_unique_id))
                if forwarded.animation:
                    a = forwarded.animation
                    files.append((a.file_id, a.file_unique_id))

                # 删除转发的消息
                try:
                    await bot.delete_message(
                        chat_id=channel_id,
                        message_id=forwarded.message_id,
                    )
                except Exception:
                    log.warning(f"删除转发消息失败: msg_id={forwarded.message_id}")

                # file_id 匹配
                for fid, uid in files:
                    if fid in fid_index:
                        mf_id = fid_index.pop(fid)
                        matched += 1
                        match_results.append({
                            "mf_id": mf_id,
                            "msg_id": msg_id,
                            "file_unique_id": uid,
                        })
                        log.info(
                            f"  匹配 #{matched}: mf_id={mf_id}, "
                            f"msg_id={msg_id}, uid={uid}"
                        )

                # 全部匹配完提前退出
                if not fid_index:
                    log.info("全部匹配完毕!")
                    break

            except Exception:
                pass  # 消息不存在或已删除

            # Telegram 限流：~6 req/s
            await asyncio.sleep(0.15)

            # 每 100 条消息打印进度
            if msg_id % 100 == 0:
                log.info(
                    f"  进度: msg_id={msg_id}, 扫描={scanned}, "
                    f"匹配={matched}, 剩余={len(fid_index)}"
                )

        # 汇总
        log.info(f"扫描完成: 有效消息={scanned}, 匹配={matched}, 未匹配={len(fid_index)}")

        if fid_index:
            log.warning(f"以下 {len(fid_index)} 个文件未在存储频道中找到:")
            for fid, mf_id in list(fid_index.items())[:10]:
                log.warning(f"  mf_id={mf_id}, fid={fid[:60]}...")

        # 写入数据库
        if match_results and commit_mode:
            log.info(f"正在写入 {len(match_results)} 条匹配结果...")
            async with engine.begin() as conn:
                for r in match_results:
                    await conn.execute(text(
                        "UPDATE media_files "
                        "SET source_channel_id = :ch, "
                        "    source_message_id = :msg, "
                        "    file_unique_id = COALESCE(NULLIF(file_unique_id, ''), :uid) "
                        "WHERE id = :id AND source_message_id IS NULL"
                    ), {
                        "ch": channel_id,
                        "msg": r["msg_id"],
                        "uid": r["file_unique_id"],
                        "id": r["mf_id"],
                    })
            log.info("写入完成")
        elif match_results and not commit_mode:
            log.info(f"DRY-RUN 模式，跳过写入。加 --commit 参数执行真正写入。")

        # 最终统计
        async with engine.begin() as conn:
            stats = (await conn.execute(text(
                "SELECT count(*) as total, "
                "  count(file_unique_id) FILTER (WHERE file_unique_id IS NOT NULL AND file_unique_id <> '') as has_uid, "
                "  count(source_message_id) FILTER (WHERE source_message_id IS NOT NULL) as has_msg "
                "FROM media_files"
            ))).fetchone()
        log.info(f"当前数据库状态: total={stats[0]}, has_uid={stats[1]}, has_msg={stats[2]}")

    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
