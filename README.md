# SourceBot

Telegram 邀请链接追踪机器人系统

## 功能

- 📎 **邀请链接管理** - Deep Link 追踪用户来源
- 🎬 **媒体资源管理** - 图片/视频/媒体组上传
- 📢 **广告投放** - 翻页浏览中穿插广告,统计点击
- 📊 **数据统计** - 用户/浏览量/广告效果报表
- 👥 **统计群查询** - /query /total 命令
- 💬 **客服群识别** - 转发消息自动识别用户来源

## 技术栈

**后端:** Python 3.11 + FastAPI + aiogram 3.x + PostgreSQL  
**前端:** Next.js 15 + Ant Design + ECharts

## 快速开始

### 1. 配置后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env       # 编辑填写配置
python -m app.init_db
```

### 2. 启动服务

```bash
# 终端 1: Bot
python -m app.bot

# 终端 2: API
python -m uvicorn app.main:app --port 9000

# 终端 3: 前端
cd frontend && npm install && npm run dev -- -p 3001
```

### 3. 访问

- 前端: http://localhost:3001
- API: http://localhost:9000/docs
- 默认账号: admin / admin123

## 配置说明

编辑 `backend/.env`:

```bash
BOT_TOKEN=your_bot_token
STORAGE_CHANNEL_ID=-100xxx     # 私有存储频道
STATS_GROUP_ID=-100xxx         # 统计群
SERVICE_GROUP_ID=-100xxx       # 客服群
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/sourcebot
SECRET_KEY=your_secret_key
```

## License

MIT
