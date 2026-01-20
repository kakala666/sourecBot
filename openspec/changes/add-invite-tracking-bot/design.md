# 技术设计文档

## Context

构建 Telegram 邀请链接追踪机器人系统,包含:
- Telegram Bot (aiogram 3.x)
- Web 后台 (FastAPI + Next.js)
- PostgreSQL 数据库
- 部署在 Debian 12.8 服务器

### 约束条件
- 无域名,使用 IP 地址访问
- 使用用户名+密码认证(非 Telegram Login Widget)
- 文件上传后转换为 file_id 存储到 Telegram 私有频道
- 禁用端口: 3000, 4000, 5000, 5001, 8000

---

## 详细技术栈

### 后端 (Python)

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 运行时 | Python | 3.11+ | 主语言 |
| Bot 框架 | aiogram | 3.x | Telegram Bot API |
| Web 框架 | FastAPI | 0.110+ | REST API |
| ORM | SQLAlchemy | 2.0+ | 数据库操作 |
| 数据库驱动 | asyncpg | 0.29+ | PostgreSQL 异步驱动 |
| 数据验证 | Pydantic | 2.x | 请求/响应模型 |
| 密码加密 | bcrypt | 4.x | 管理员密码 |
| JWT | python-jose | 3.x | Token 生成验证 |
| 环境配置 | python-dotenv | 1.x | .env 文件加载 |
| 异步 HTTP | aiohttp | 3.x | aiogram 依赖 |

### 前端 (TypeScript)

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Next.js | 15.x | React 全栈框架 |
| UI 库 | Ant Design | 5.x | 企业级组件库 |
| 图表 | ECharts | 5.x | 数据可视化 |
| HTTP 客户端 | axios | 1.x | API 请求 |
| 状态管理 | zustand | 4.x | 轻量级状态库 |
| 表单验证 | zod | 3.x | Schema 验证 |

### 数据库

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 数据库 | PostgreSQL | 16.x | 主数据库 |
| 连接池 | asyncpg | - | 异步连接 |

### 部署

| 组件 | 技术 | 用途 |
|------|------|------|
| 进程管理 | systemd | Bot 和 API 服务管理 |
| 版本管理 | Git | 代码版本控制 |
| 包管理 | pip + npm | 依赖管理 |

### 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 (Next.js) | 3001 | 开发模式和生产模式 |
| 后端 API (FastAPI) | 9000 | REST API 服务 |
| PostgreSQL | 5432 | 数据库默认端口 |

---

## Goals / Non-Goals

### Goals
- 实现完整的邀请链接追踪系统
- 提供易用的 Web 后台管理界面
- 支持群组内查询统计和客服功能
- 保证系统稳定性和可维护性

### Non-Goals
- 不支持多 Bot 管理
- 不支持国际化(仅中文)
- 不支持移动端 APP

---

## Decisions

### 1. 数据库选择: PostgreSQL
- **决策**: 使用 PostgreSQL 而非 SQLite
- **原因**: 并发写入性能好,支持复杂统计查询,易于扩展
- **备选**: SQLite (并发性能差,统计查询慢)

### 2. 文件存储策略: file_id 方案
- **决策**: 上传文件后立即发送到私有 Telegram 频道,获取 file_id 存储
- **原因**: Bot 发送速度快,节省服务器存储空间
- **备选**: 保留本地文件每次上传 (占用空间大,发送慢)

### 3. 用户状态管理: aiogram FSM
- **决策**: 使用 aiogram 内置的 FSM(有限状态机)
- **原因**: 原生支持,无需额外依赖,适合简单状态流转
- **备选**: Redis 存储状态 (增加复杂度)

### 4. 前端框架: Next.js 15 + App Router
- **决策**: 使用 Next.js 开发模式运行
- **原因**: 简化部署,直接访问端口
- **备选**: 静态导出 + Nginx

### 5. 广告点击统计: 先记录后跳转
- **决策**: 使用 callback_data 先记录点击,再发送跳转链接
- **原因**: 精确统计点击率
- **备选**: 直接 URL 按钮 (无法统计)

### 6. 部署方式: 直接端口访问
- **决策**: 不使用反向代理,直接访问各服务端口
- **原因**: 简化部署,减少依赖
- **备选**: Nginx 反向代理 (增加复杂度)

---

## 测试方案

### 1. 单元测试

**后端 (pytest)**
```bash
# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov

# 运行测试
pytest tests/ -v --cov=app --cov-report=html
```

测试范围:
- 数据库模型 CRUD 操作
- 服务层业务逻辑
- API 端点响应
- JWT Token 生成验证

**前端 (Jest)**
```bash
npm run test
```

测试范围:
- 组件渲染测试
- API 请求 Mock 测试
- 表单验证逻辑

### 2. Bot 功能测试

**手动测试清单:**
- [ ] Deep Link 启动 → 记录来源 → 发送封面
- [ ] 翻页 → 发送广告 → 倒计时 → 发送资源
- [ ] 等待时间递增 (2/3/4/5/5...)
- [ ] 预览结束判断 (<5 / =5 / >5)
- [ ] 老用户直接私聊 → 正常响应
- [ ] 新用户直接私聊 → 不响应
- [ ] 统计群查询命令
- [ ] 客服群转发识别

### 3. API 接口测试

**使用 Postman 或 curl:**
```bash
# 登录获取 Token
curl -X POST http://localhost:9000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# 获取邀请链接列表
curl http://localhost:9000/api/invite-links \
  -H "Authorization: Bearer {token}"
```

### 4. 端到端测试

手动流程验证:
1. 创建邀请链接 → 上传资源 → 设置封面
2. 配置广告组 → 绑定到邀请链接
3. 使用 Deep Link 启动 Bot → 验证完整翻页流程
4. 在统计群查询报表 → 验证数据准确性
5. 在客服群转发消息 → 验证用户识别

---

## 本地开发部署

### 前置条件

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ (本地安装)
- Telegram Bot Token (从 @BotFather 获取)
- Telegram 私有频道 (用于存储 file_id)

### 步骤 1: 克隆项目并配置环境

```powershell
# Windows PowerShell
cd d:\pythonProject\sourceBot

# 创建 Python 虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装 Python 依赖
pip install -r requirements.txt
```

### 步骤 2: 安装并配置 PostgreSQL (Windows)

**安装:**
1. 下载安装包: https://www.postgresql.org/download/windows/
2. 运行安装程序,记住设置的密码
3. 安装完成后 PostgreSQL 服务会自动启动

**创建数据库:**
```powershell
# 打开 psql (在开始菜单搜索 "SQL Shell (psql)")
# 或使用以下命令 (需要将 PostgreSQL bin 目录添加到 PATH)
psql -U postgres
```

```sql
-- 在 psql 中执行
CREATE DATABASE sourcebot;
CREATE USER botuser WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE sourcebot TO botuser;
\q
```

### 步骤 3: 配置环境变量

创建 `.env` 文件:
```bash
# Bot 配置
BOT_TOKEN=your_bot_token_from_botfather
STORAGE_CHANNEL_ID=-1001234567890     # 私有存储频道 ID
STATS_GROUP_ID=-1009876543210         # 统计群 ID
SERVICE_GROUP_ID=-1001111111111       # 客服群 ID

# 数据库配置
DATABASE_URL=postgresql+asyncpg://botuser:your_password@localhost:5432/sourcebot

# JWT 配置
SECRET_KEY=your_random_secret_key_at_least_32_chars

# 服务端口
API_PORT=9000
FRONTEND_PORT=3001
```

### 步骤 4: 初始化数据库

```powershell
# 运行数据库迁移
python -m app.database.init_db
```

### 步骤 5: 启动后端服务

```powershell
# 终端 1: 启动 Bot
python -m app.bot

# 终端 2: 启动 API 服务
python -m uvicorn app.main:app --reload --port 9000
```

### 步骤 6: 启动前端

```powershell
cd frontend
npm install
npm run dev -- -p 3001
```

### 步骤 7: 访问

- **前端**: http://localhost:3001
- **API 文档**: http://localhost:9000/docs
- **Bot**: 通过 Telegram 私聊测试

---

## 服务器部署 (Debian 12.8)

### 前置条件

- Debian 12.8 服务器
- SSH 访问权限
- 服务器 IP 地址

### 步骤 1: 安装系统依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# 安装 Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 安装 Git
sudo apt install -y git
```

### 步骤 2: 配置 PostgreSQL

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 创建数据库和用户
CREATE DATABASE sourcebot;
CREATE USER botuser WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE sourcebot TO botuser;
\q
```

### 步骤 3: 部署代码

```bash
# 创建项目目录
sudo mkdir -p /opt/sourcebot
sudo chown $USER:$USER /opt/sourcebot

# 克隆代码 (或上传)
cd /opt/sourcebot
git clone your_repo_url .

# 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置
```

### 步骤 4: 安装前端依赖

```bash
cd /opt/sourcebot/frontend
npm install
```

### 步骤 5: 配置 systemd 服务

**Bot 服务:**
```bash
sudo nano /etc/systemd/system/sourcebot-bot.service
```

```ini
[Unit]
Description=Source Bot Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/sourcebot
Environment="PATH=/opt/sourcebot/.venv/bin"
ExecStart=/opt/sourcebot/.venv/bin/python -m app.bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**API 服务:**
```bash
sudo nano /etc/systemd/system/sourcebot-api.service
```

```ini
[Unit]
Description=Source Bot API Service
After=network.target postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/sourcebot
Environment="PATH=/opt/sourcebot/.venv/bin"
ExecStart=/opt/sourcebot/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**前端服务:**
```bash
sudo nano /etc/systemd/system/sourcebot-frontend.service
```

```ini
[Unit]
Description=Source Bot Frontend
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/sourcebot/frontend
ExecStart=/usr/bin/npm run start -- -p 3001
Restart=always
RestartSec=10
Environment="NODE_ENV=production"

[Install]
WantedBy=multi-user.target
```

**启用服务:**
```bash
# 先构建前端
cd /opt/sourcebot/frontend
npm run build

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable sourcebot-bot sourcebot-api sourcebot-frontend
sudo systemctl start sourcebot-bot sourcebot-api sourcebot-frontend

# 检查状态
sudo systemctl status sourcebot-bot
sudo systemctl status sourcebot-api
sudo systemctl status sourcebot-frontend
```

### 步骤 6: 配置防火墙

```bash
sudo apt install -y ufw
sudo ufw allow ssh
sudo ufw allow 3001/tcp   # 前端
sudo ufw allow 9000/tcp   # API
sudo ufw enable
```

### 步骤 7: 验证部署

```bash
# 检查服务状态
sudo systemctl status sourcebot-bot
sudo systemctl status sourcebot-api
sudo systemctl status sourcebot-frontend

# 查看日志
sudo journalctl -u sourcebot-bot -f
sudo journalctl -u sourcebot-api -f
sudo journalctl -u sourcebot-frontend -f
```

### 访问

- **前端**: http://YOUR_SERVER_IP:3001
- **API**: http://YOUR_SERVER_IP:9000
- **API 文档**: http://YOUR_SERVER_IP:9000/docs
- **Bot**: 通过 Telegram 测试

---

## Risks / Trade-offs

### 1. 无域名限制
- **风险**: 无法使用 Telegram Login Widget
- **缓解**: 使用用户名+密码认证,JWT Token 管理会话

### 2. file_id 依赖私有频道
- **风险**: 频道被删除会导致所有资源失效
- **缓解**: 妥善保管私有频道,不要删除

### 3. PostgreSQL 运维
- **风险**: 需要安装和管理数据库服务
- **缓解**: 使用 systemd 管理,PostgreSQL 稳定性高

### 4. 直接端口暴露
- **风险**: 需要记住多个端口
- **缓解**: 端口固定且明确 (前端 3001, API 9000)

---

## Open Questions

1. ~~数据库选择~~ → 已确定 PostgreSQL
2. ~~认证方式~~ → 已确定用户名+密码
3. ~~等待时间规则~~ → 已确定 2/3/4/5/5/5/5 秒
4. ~~端口配置~~ → 前端 3001, API 9000
