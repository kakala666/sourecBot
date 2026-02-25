#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG 实体全量检测脚本：从 MySQL 读取有效实体，抓取 t.me 页面校验并回写数据库。

一、整体逻辑（主流程）
------------------------
1. 数据源：从 MySQL tg_entity 表按 MYSQL_QUERY 分页拉取 (id, 链接/用户名)，
   仅拉取 deleted=0 且 status=1（有效）的实体。
2. 检测：对每条记录请求 https://t.me/{username}，解析 HTML（og:title、og:description、
   成员数、类型等），判断是否为有效群组/频道/机器人，或不存在/私人用户/无效。
3. 回写：若 SCHEDULE=True，本轮结束后批量回写 MySQL：
   - 检测失败（不存在、私人、解析失败等）→ 将该实体 status 置为 2（失效）；
   - 检测成功 → 更新 title、description、username、member_count、type、photo_url、
     invite_link、is_verified、last_sync_time、update_time。
4. 定时：若 SCHEDULE=True，每轮结束后休眠 INTERVAL_HOURS 小时，再执行下一轮；
   否则执行一轮后退出。

二、模块结构
------------------------
- 常量：TG 页面 URL、status 枚举、解析用正则、HTTP 头、运行参数（代理/MySQL/定时等）。
- 工具函数：extract_username、decode_html、is_invalid_description、is_private_user_page、
  determine_type（从链接/HTML 提取或判断信息）。
- ParseResult：单条检测结果（成功与否、标题、描述、成员数、类型等）。
- parse_tg_html：根据 t.me 页面 HTML 解析出 ParseResult（与 Java TgWebParseServiceImpl 对齐）。
- 异步网络：fetch_html_async（拉取 HTML）、process_one_async（单条：拉取+解析+重试）。
- 数据层：iter_inputs_from_mysql（分页迭代 (id, link)）、apply_db_updates（批量更新失效/有效）。
- main：校验配置 → 循环每轮（拉取输入 → 并发检测 → 收集结果 → 回写 DB）→ 定时则休眠。

三、数据加载逻辑
------------------------
- 来源：仅从 MySQL tg_entity 表加载，由 MYSQL_QUERY 决定范围（默认 deleted=0 且 status=1，且有 invite_link 或 username）。
- 查询形态：base_query 必须返回两列 (id, link)。link 可为完整 t.me 链接或 username，脚本会从中提取 username 再请求 https://t.me/{username}。
- 分页方式：keyset 分页，避免 OFFSET 深分页。每次执行：
    SELECT * FROM (base_query) t WHERE t.id > :last_id ORDER BY t.id ASC LIMIT :batch_size
  last_id 初始为 0，每批取完后更新为当前批最大 id，下一批从该 id 之后继续取。
- 拉取节奏：每批拉取 MYSQL_BATCH_SIZE 行，用 pymysql 连接执行后立即关闭连接；通过生成器 yield (entity_id, link)，主流程按 BATCH_SIZE（max(WORKERS*20, 2000)）条一批交给并发检测，拉取与检测可流水进行，无需一次性加载全表。

四、更新逻辑
------------------------
- 触发条件：仅当 SCHEDULE=True 时，每轮检测结束后对本轮结果执行回写；否则不写库。
- 数据来源：本轮收集的 results_for_db，元素为 (entity_id, ParseResult)。每条对应一次 t.me 请求的解析结果（成功或失败）。
- 分类处理：
  (1) 无效（success=False）：包括「用户名不存在」「私人用户」「无法获取名称/有效信息」「请求超时/网络异常」等。将这些记录的 id 收集为 invalid_ids，批量执行：
      UPDATE tg_entity SET status = 2, update_time = NOW() WHERE id IN (:ids)
      status=2 表示失效，下次全量加载时 MYSQL_QUERY 只查 status=1，故不会再被拉取。
  (2) 有效（success=True）：解析到标题、类型、成员数等。将这些记录组装为 (title, description, username, member_count, type, photo_url, invite_link, is_verified, id)，批量执行：
      UPDATE tg_entity SET title=%s, description=%s, username=%s, member_count=%s, type=%s,
        photo_url=%s, invite_link=%s, is_verified=%s, last_sync_time=NOW(), update_time=NOW() WHERE id=%s
      字段长度按表定义截断（如 title 255、description 5000、username 100 等）；username 统一为 @xxx 形式。
- 分批与间隔：无效与有效分别按 DB_UPDATE_BATCH_SIZE 分批执行；每批执行完后 sleep(DB_UPDATE_DELAY_SEC)，再执行下一批，避免同一时间大量更新导致数据库压力过大。
- 返回值：apply_db_updates 返回 (更新为失效的行数, 更新有效字段的行数)，用于打日志。

五、参考与运行
------------------------
解析规则参考：continew-bot/.../TgWebParseServiceImpl.java
运行前在文件内修改「运行参数」常量（代理、MySQL、SCHEDULE、INTERVAL_HOURS 等）即可。
"""

from __future__ import annotations

import asyncio
import html as html_lib
import itertools
import random
import re
import sys
import time
from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional, Tuple

# ---------- 依赖检查与导入：脚本需要 aiohttp（HTTP）、pymysql（MySQL），缺一不可 ----------
try:
    import aiohttp  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError("缺少依赖 aiohttp（HTTP 请求 t.me 页面），请安装：pip install aiohttp") from e

try:
    import pymysql  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError("缺少依赖 pymysql（MySQL 数据加载与回写），请安装：pip install pymysql") from e


# ---------- 基础 URL 与业务枚举 ----------
TG_WEB_URL = "https://t.me/"
# tg_entity 表 status 枚举：1-正常 2-失效 3-待审核（本脚本只写入 1/2）
TG_ENTITY_STATUS_OK = 1
TG_ENTITY_STATUS_INVALID = 2

# ---------- 解析 t.me 页面用正则（与 Java TgWebParseServiceImpl 对齐） ----------
# 从 <meta property="og:xxx" content="..."> 提取标题、描述、图片
TITLE_PATTERN = re.compile(r'<meta property="og:title" content="([^"]+)"')
DESC_PATTERN = re.compile(r'<meta property="og:description" content="([^"]+)"')
IMAGE_PATTERN = re.compile(r'<meta property="og:image" content="([^"]+)"')
# 成员/订阅数：英文 "123 members"、"1,234 subscribers" 及中文 "123 位成员" 等
MEMBER_PATTERN = re.compile(r"(\d[\d\s]*) (members?|subscribers?)", re.IGNORECASE)
MEMBER_PATTERN_CN = re.compile(r"(\d[\d\s]*) (位成员|位订阅者|成员|订阅者)")
# 类型判断：频道/机器人关键词
TYPE_CHANNEL_PATTERN = re.compile(r"(channel|频道)", re.IGNORECASE)
TYPE_BOT_PATTERN = re.compile(r"(bot|机器人)", re.IGNORECASE)
VERIFIED_PATTERN = re.compile(r"(verified|已认证)", re.IGNORECASE)
# 私人用户页面特征（需排除，不当作群组/频道/机器人）
PRIVATE_USER_TITLE_PATTERN = re.compile(r"Telegram:\s*Contact\s*@", re.IGNORECASE)
PRIVATE_USER_ICON_PATTERN = re.compile(r"tgme_icon_user", re.IGNORECASE)
PRIVATE_USER_CONTACT_PATTERN = re.compile(r"you can contact", re.IGNORECASE)
PRIVATE_USER_SEND_MSG_PATTERN = re.compile(r"Send\s*Message", re.IGNORECASE)
# 无效描述：默认的 "You can view and join @xxx right away" 等，不当作有效简介
INVALID_DESC_VIEW_JOIN_PATTERN = re.compile(r"You can view and join @\w+ right away", re.IGNORECASE)
INVALID_DESC_CONTACT_PATTERN = re.compile(r"you can contact @\w+ right away", re.IGNORECASE)
# 从输入中提取 username：支持 t.me/xxx、telegram.me/xxx 或纯 @xxx / xxx
TG_LINK_PATTERN = re.compile(r"(?:https?://)?(?:t\.me|telegram\.me)/\+?([\w_]+)/?", re.IGNORECASE)
USERNAME_PATTERN = re.compile(r"^@?([\w_]{4,32})$")


# 请求 t.me 时使用的 HTTP 头，模拟浏览器避免被限流
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# ==================== 运行参数（直接修改此块，无需命令行） ====================
# 代理：bestproxy 等，留空则直连（易被 TG 限制）
PROXY = "http://bp-zcefh3mp9mlh:vI7GjpFjfNmCeqX6@proxy.bestproxy.com:2312"
# 并发与单请求：WORKERS 为同时进行的请求数，TIMEOUT 单次请求超时秒，RETRIES 失败重试次数
WORKERS = 200
TIMEOUT = 20.0
RETRIES = 2
MIN_DELAY_MS = 0
MAX_DELAY_MS = 0
# MySQL 数据源：仅从 tg_entity 拉取，base_query 必须返回两列 (id, link)
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = ""  # 请填写密码
MYSQL_DB = "soubot"
MYSQL_BATCH_SIZE = 2000  # 每次从 DB 拉取的行数（游标分页）
MYSQL_QUERY = (
    "SELECT id, "
    "CASE "
    "WHEN invite_link IS NOT NULL AND invite_link <> '' THEN invite_link "
    "WHEN username IS NOT NULL AND username <> '' THEN CONCAT('https://t.me/', username) "
    "ELSE NULL END AS link "
    "FROM tg_entity "
    "WHERE deleted = 0 AND status = 1 "
    "AND ((invite_link IS NOT NULL AND invite_link <> '') OR (username IS NOT NULL AND username <> ''))"
)
# 定时与回写：SCHEDULE=True 时每轮结束后回写 DB，并每隔 INTERVAL_HOURS 小时执行下一轮
SCHEDULE = True
INTERVAL_HOURS = 24.0
DB_UPDATE_BATCH_SIZE = 200   # 每批更新条数，越大 DB 瞬时压力越大
DB_UPDATE_DELAY_SEC = 2.0   # 每批之间的休眠秒数，用于分散写入压力
# =============================================================================


def extract_username(input_value: str) -> Optional[str]:
    """
    从输入中提取 Telegram 用户名（不含 @）。
    支持：t.me/xxx、telegram.me/xxx、@xxx、xxx。不符合则返回 None。
    """
    if not input_value:
        return None
    s = input_value.strip()
    m = TG_LINK_PATTERN.search(s)
    if m:
        return m.group(1)
    m = USERNAME_PATTERN.match(s)
    if m:
        return m.group(1)
    return None


def decode_html(value: str) -> str:
    """将 HTML 实体（如 &amp;、&quot;）解码为普通字符，与 Java decodeHtml 行为一致。"""
    return html_lib.unescape(value or "")


def is_invalid_description(desc: str) -> bool:
    """
    判断描述是否为「无效」的默认文案（如 "You can view and join @xxx right away"）。
    此类描述不当作有效简介，用于过滤无效实体。
    """
    if not desc:
        return True
    if INVALID_DESC_VIEW_JOIN_PATTERN.search(desc):
        return True
    if INVALID_DESC_CONTACT_PATTERN.search(desc):
        return True
    return False


def is_private_user_page(html: str) -> bool:
    """
    根据 t.me 页面 HTML 判断是否为「私人用户」页面（非群组/频道/机器人）。
    通过图标、标题、联系/发消息文案及是否无成员数等特征判断，需排除此类页面。
    """
    if not html:
        return False
    if PRIVATE_USER_ICON_PATTERN.search(html):
        return True
    if PRIVATE_USER_TITLE_PATTERN.search(html):
        return True
    if PRIVATE_USER_CONTACT_PATTERN.search(html) and PRIVATE_USER_SEND_MSG_PATTERN.search(html):
        has_member = bool(MEMBER_PATTERN.search(html) or MEMBER_PATTERN_CN.search(html))
        if not has_member:
            return True
    return False


def determine_type(html: str, username: str) -> str:
    """
    根据页面 HTML 与 username 判断实体类型：BOT / CHANNEL / GROUP。
    规则：username 以 bot 结尾→BOT；页面含 tgme_page_extra+subscriber→CHANNEL；
    tgme_page_extra+member→GROUP；否则按关键词 channel/bot 再判，默认 GROUP。
    """
    u = (username or "").lower()
    if u.endswith("bot"):
        return "BOT"
    if "tgme_page_extra" in html and "subscriber" in html:
        return "CHANNEL"
    if "tgme_page_extra" in html and "member" in html:
        return "GROUP"
    if TYPE_BOT_PATTERN.search(html):
        return "BOT"
    if TYPE_CHANNEL_PATTERN.search(html):
        return "CHANNEL"
    return "GROUP"


@dataclass
class ParseResult:
    """
    单条 t.me 页面的解析结果。
    - success=True 表示可当作有效群组/频道/机器人；False 表示不存在、私人用户或无法解析。
    - entity_id 为 tg_entity 表主键，用于回写时更新对应记录。
    - 成功时填充 title、description、member_count、type、photo_url、invite_link、is_verified 等。
    """
    input: str
    success: bool
    error_msg: str = ""
    username: str = ""
    type: str = ""
    title: str = ""
    description: str = ""
    member_count: Optional[int] = None
    photo_url: str = ""
    invite_link: str = ""
    is_verified: int = 0
    entity_id: Optional[int] = None
    fetched_url: str = ""


def parse_tg_html(input_value: str, username: str, html: str) -> ParseResult:
    """
    根据 t.me 页面 HTML 解析出 ParseResult，与 Java TgWebParseServiceImpl 逻辑对齐。
    顺序：页面不存在/私人用户 → 无标题 → 标题仅等于 username 且无描述/成员数 → 判无效；
    否则构造成功结果并填充 og:title、og:description、成员数、类型、头像、认证等。
    """
    # 1. 页面不存在（图标或文案）
    if "tgme_page_icon_notfound" in html or "Page not found" in html:
        return ParseResult(input=input_value, success=False, error_msg="该用户名不存在", username=username)
    # 2. 私人用户页面，不当作群组/频道/机器人
    if is_private_user_page(html):
        return ParseResult(input=input_value, success=False, error_msg="这是私人用户，不是群组/频道/机器人", username=username)

    # 3. 必须有 og:title，否则无法作为有效实体
    title = ""
    m = TITLE_PATTERN.search(html)
    if m:
        title = decode_html(m.group(1))
    if not title:
        return ParseResult(input=input_value, success=False, error_msg="无法获取名称信息", username=username)

    # 4. 若标题等于 username 且无描述、无成员数，视为无效（信息不足）
    if title.strip().lower() == (username or "").strip().lower():
        desc_raw = DESC_PATTERN.search(html)
        member_raw = MEMBER_PATTERN.search(html) or MEMBER_PATTERN_CN.search(html)
        if (not desc_raw) and (not member_raw):
            return ParseResult(input=input_value, success=False, error_msg="无法获取有效信息", username=username)

    # 5. 构造成功结果，先填基础字段
    result = ParseResult(
        input=input_value,
        success=True,
        username=username,
        invite_link=TG_WEB_URL + username,
        title=title,
        type=determine_type(html, username),
        is_verified=1 if VERIFIED_PATTERN.search(html) else 0,
    )

    # 6. 可选：描述（排除无效默认文案）
    dm = DESC_PATTERN.search(html)
    if dm:
        desc = decode_html(dm.group(1))
        if not is_invalid_description(desc):
            result.description = desc

    # 7. 可选：头像 URL
    im = IMAGE_PATTERN.search(html)
    if im:
        result.photo_url = im.group(1)

    # 8. 可选：成员/订阅数（去掉千分位空格后转 int）
    mm = MEMBER_PATTERN.search(html) or MEMBER_PATTERN_CN.search(html)
    if mm:
        member_str = mm.group(1)
        try:
            result.member_count = int(re.sub(r"\s+", "", member_str))
        except ValueError:
            result.member_count = None

    return result


async def fetch_html_async(
    session: aiohttp.ClientSession,
    url: str,
    proxy_url: Optional[str],
    timeout: float,
) -> Tuple[Optional[str], Optional[str]]:
    """
    异步请求 url，返回 (html 文本, 错误信息)。
    成功时错误信息为 None；失败时 html 为 None，错误信息为 "Timeout"、"HTTP 4xx" 或异常信息。
    """
    try:
        timeout_ctx = aiohttp.ClientTimeout(total=timeout)
        async with session.get(
            url,
            proxy=proxy_url or None,
            timeout=timeout_ctx,
            allow_redirects=True,
        ) as resp:
            text = await resp.text()
            if resp.status >= 400:
                return None, f"HTTP {resp.status}"
            return text, None
    except asyncio.TimeoutError:
        return None, "Timeout"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


async def process_one_async(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    entity_id: Optional[int],
    input_value: str,
    proxy_url: str,
    timeout: float,
    retries: int,
    min_delay_ms: int,
    max_delay_ms: int,
) -> ParseResult:
    """
    单条检测：从 input_value 提取 username → 请求 t.me/{username} → 解析 HTML 得到 ParseResult。
    受 sem 限制并发；失败时重试 retries 次，每次前可随机延迟 min/max_delay_ms。
    若无法识别链接/用户名或多次请求均失败，返回 success=False 的 ParseResult。
    """
    username = extract_username(input_value)
    if not username:
        r = ParseResult(input=input_value, success=False, error_msg="无法识别用户名或链接格式")
        r.entity_id = entity_id
        return r

    fetched_url = TG_WEB_URL + username
    last_err = ""

    async with sem:
        for attempt in range(retries + 1):
            # 可选：请求前随机延迟，降低瞬时并发
            if min_delay_ms > 0 or max_delay_ms > 0:
                delay = random.randint(min_delay_ms, max(min_delay_ms, max_delay_ms))
                await asyncio.sleep(delay / 1000.0)

            html_text, err = await fetch_html_async(session, fetched_url, proxy_url or None, timeout)
            if html_text:
                res = parse_tg_html(input_value, username, html_text)
                res.entity_id = entity_id
                res.fetched_url = fetched_url
                return res

            last_err = err or "Unknown"
            if attempt < retries:
                await asyncio.sleep(min(2.0 ** attempt, 4.0))

    r = ParseResult(input=input_value, success=False, error_msg=f"获取页面内容失败: {last_err}", username=username)
    r.entity_id = entity_id
    r.fetched_url = fetched_url
    return r


def iter_inputs_from_mysql(
    host: str,
    port: int,
    user: str,
    password: str,
    db: str,
    base_query: str,
    batch_size: int,
) -> Iterator[Tuple[Optional[int], str]]:
    """
    数据加载：从 MySQL 按 keyset 分页拉取 (id, 链接/用户名)，详见模块文档「三、数据加载逻辑」。
    base_query 必须返回两列：第一列 id，第二列 link（t.me 链接或 username）。
    内部用 WHERE id > last_id ORDER BY id LIMIT batch_size 实现分页；每批拉取 batch_size 行，用完后关闭连接。
    """
    last_id = 0
    while True:
        paged = f"SELECT * FROM ({base_query}) t WHERE t.id > %s ORDER BY t.id ASC LIMIT %s"
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=db, charset="utf8mb4")
        try:
            with conn.cursor() as cur:
                cur.execute(paged, (last_id, batch_size))
                rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            break

        for row in rows:
            entity_id = row[0]
            raw = row[1]
            if raw is None:
                continue
            s = str(raw).strip()
            if not s:
                continue
            yield int(entity_id), s
            last_id = max(last_id, int(entity_id))


def apply_db_updates(
    host: str,
    port: int,
    user: str,
    password: str,
    db: str,
    results: List[Tuple[int, "ParseResult"]],
    batch_size: int,
    delay_sec: float,
) -> Tuple[int, int]:
    """
    更新逻辑：根据本轮检测结果批量回写 tg_entity，详见模块文档「四、更新逻辑」。
    - success=False → 将对应 id 的 status 置为 2（失效），更新 update_time。
    - success=True → 更新 title、description、username、member_count、type、
      photo_url、invite_link、is_verified、last_sync_time、update_time。
    按 batch_size 分批、每批后 sleep(delay_sec)。返回 (置为失效行数, 更新有效行数)。
    """
    invalid_ids: List[int] = []
    valid_rows: List[Tuple[str, str, str, int, str, str, str, int, int]] = []

    for eid, r in results:
        if eid is None:
            continue
        if not r.success:
            invalid_ids.append(eid)
        else:
            # 有效实体：组装 UPDATE 所需字段，长度按表定义截断；username 统一为 @xxx 形式
            uname = (r.username or "").strip()
            if uname and not uname.startswith("@"):
                uname = "@" + uname
            uname = uname[:100]
            valid_rows.append(
                (
                    (r.title or "")[:255],
                    (r.description or "")[:5000],
                    uname,
                    r.member_count if r.member_count is not None else 0,
                    (r.type or "")[:20],
                    (r.photo_url or "")[:1000],
                    (r.invite_link or "")[:255],
                    1 if r.is_verified else 0,
                    eid,
                )
            )

    updated_invalid = 0
    updated_valid = 0

    def connect():
        return pymysql.connect(
            host=host, port=port, user=user, password=password, database=db, charset="utf8mb4"
        )

    # 1. 分批将无效实体 status 置为 2，每批后 sleep
    for i in range(0, len(invalid_ids), batch_size):
        chunk = invalid_ids[i : i + batch_size]
        if not chunk:
            continue
        conn = connect()
        try:
            with conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(chunk))
                cur.execute(
                    "UPDATE tg_entity SET status = %s, update_time = NOW() WHERE id IN (" + placeholders + ")",
                    [TG_ENTITY_STATUS_INVALID] + chunk,
                )
                updated_invalid += cur.rowcount
            conn.commit()
        finally:
            conn.close()
        if delay_sec > 0 and i + batch_size < len(invalid_ids):
            time.sleep(delay_sec)

    # 2. 分批更新有效实体字段，每批后 sleep
    sql_valid = (
        "UPDATE tg_entity SET title=%s, description=%s, username=%s, member_count=%s, type=%s, "
        "photo_url=%s, invite_link=%s, is_verified=%s, last_sync_time=NOW(), update_time=NOW() WHERE id=%s"
    )
    for i in range(0, len(valid_rows), batch_size):
        chunk = valid_rows[i : i + batch_size]
        if not chunk:
            continue
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.executemany(sql_valid, chunk)
                updated_valid += cur.rowcount
            conn.commit()
        finally:
            conn.close()
        if delay_sec > 0 and i + batch_size < len(valid_rows):
            time.sleep(delay_sec)

    return updated_invalid, updated_valid


def main() -> int:
    """
    入口：校验配置 → 循环执行「拉取输入 → 并发检测 → 收集结果 → 回写 DB」。
    若 SCHEDULE=True，每轮结束后回写数据库并休眠 INTERVAL_HOURS 小时再执行下一轮；否则执行一轮后退出。
    """
    if not MYSQL_HOST or not MYSQL_HOST.strip():
        print("错误：请设置 MYSQL_HOST（数据来源为 MySQL）", file=sys.stderr)
        return 1
    # 仅在定时模式下回写 DB（与「每轮全量检测后统一更新」的设计一致）
    do_db_update = SCHEDULE

    if not PROXY or not PROXY.strip():
        print("警告：未设置 PROXY，将直连请求（很容易被 TG 限制/封禁）", file=sys.stderr)

    print("数据来源：MySQL", file=sys.stderr)
    print(f"  host={MYSQL_HOST}:{MYSQL_PORT} db={MYSQL_DB}", file=sys.stderr)
    print(f"  query={MYSQL_QUERY[:80]}...", file=sys.stderr)
    print(f"  batch_size={MYSQL_BATCH_SIZE}", file=sys.stderr)
    print(f"代理: {PROXY}", file=sys.stderr)
    print(f"并发数: {WORKERS}, 超时: {TIMEOUT}s, 重试: {RETRIES}次", file=sys.stderr)

    PROGRESS_INTERVAL = 500  # 每处理多少条打印一次进度
    BATCH_SIZE = max(WORKERS * 20, 2000)  # 每批从迭代器取多少条并发执行

    round_num = 0
    while True:
        round_num += 1
        if SCHEDULE:
            print(f"\n===== 第 {round_num} 轮全量检测 ===== ", file=sys.stderr)
            if round_num == 1:
                print("定时模式：每轮全量扫描", file=sys.stderr)

        # 本轮检测结果，用于回写时区分无效(id→status=2)与有效(更新字段)
        results_for_db: List[Tuple[int, ParseResult]] = [] if do_db_update else []

        def get_inputs() -> Iterator[Tuple[Optional[int], str]]:
            return iter_inputs_from_mysql(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB,
                base_query=MYSQL_QUERY,
                batch_size=MYSQL_BATCH_SIZE,
            )

        inputs_iter = get_inputs()
        print("开始处理（asyncio+aiohttp），每 500 条打印一次进度...", file=sys.stderr)

        start = time.time()
        total = 0
        ok = 0
        fail = 0

        async def run_batches() -> None:
            """按 BATCH_SIZE 从 inputs_iter 取一批 (id, link)，并发请求 t.me 并解析，统计 ok/fail 并收集 results_for_db。"""
            nonlocal total, ok, fail
            headers = {k: v for k, v in DEFAULT_HEADERS.items()}
            connector = aiohttp.TCPConnector(limit=WORKERS * 2, limit_per_host=WORKERS)
            sem = asyncio.Semaphore(WORKERS)

            async def one_task(eid: Optional[int], inv: str) -> Tuple[Optional[int], str, object]:
                """单条：请求+解析，返回 (eid, inv, ParseResult 或 Exception)。"""
                try:
                    r = await process_one_async(
                        session, sem, eid, inv,
                        PROXY, TIMEOUT, RETRIES,
                        MIN_DELAY_MS, MAX_DELAY_MS,
                    )
                    return (eid, inv, r)
                except Exception as ex:
                    return (eid, inv, ex)

            async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
                while True:
                    chunk = list(itertools.islice(inputs_iter, BATCH_SIZE))
                    if not chunk:
                        break
                    tasks = [asyncio.create_task(one_task(eid, inv)) for eid, inv in chunk]
                    for done in asyncio.as_completed(tasks):
                        eid, inv, r = await done
                        total += 1
                        if isinstance(r, Exception):
                            fail += 1
                            err_result = ParseResult(
                                input=inv,
                                success=False,
                                error_msg=f"{type(r).__name__}: {r}",
                                entity_id=eid,
                            )
                            if do_db_update and eid is not None:
                                results_for_db.append((eid, err_result))
                        else:
                            if r.success:
                                ok += 1
                            else:
                                fail += 1
                            if do_db_update and eid is not None:
                                results_for_db.append((eid, r))
                        if total % PROGRESS_INTERVAL == 0:
                            elapsed = time.time() - start
                            rps = total / elapsed if elapsed > 0 else 0.0
                            print(
                                f"progress: total={total} ok={ok} fail={fail} rps={rps:.1f} elapsed_s={elapsed:.1f}",
                                file=sys.stderr,
                            )
                            sys.stderr.flush()

        asyncio.run(run_batches())

        elapsed = time.time() - start
        rps = total / elapsed if elapsed > 0 else 0.0
        print(
            f"完成: total={total} ok={ok} fail={fail} 耗时={elapsed:.1f}s rps={rps:.2f}",
            file=sys.stderr,
        )

        # 定时模式：批量回写数据库（无效→status=2，有效→更新字段），分批+间隔
        if do_db_update and results_for_db:
            print(
                f"回写数据库: 共 {len(results_for_db)} 条，每批 {DB_UPDATE_BATCH_SIZE} 条，间隔 {DB_UPDATE_DELAY_SEC}s ...",
                file=sys.stderr,
            )
            u_inv, u_ok = apply_db_updates(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB,
                results=results_for_db,
                batch_size=DB_UPDATE_BATCH_SIZE,
                delay_sec=DB_UPDATE_DELAY_SEC,
            )
            print(f"DB 更新: 置为失效(status=2)={u_inv}, 更新有效实体={u_ok}", file=sys.stderr)

        if not SCHEDULE:
            break
        print(f"下一轮于 {INTERVAL_HOURS} 小时后执行，按 Ctrl+C 可退出...", file=sys.stderr)
        time.sleep(INTERVAL_HOURS * 3600)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

