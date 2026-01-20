# Telegram 邀请链接追踪机器人 - 后端

## 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI 入口
│   ├── bot.py            # Telegram Bot 入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── models/           # SQLAlchemy 模型
│   ├── schemas/          # Pydantic 模型
│   ├── api/              # API 路由
│   ├── bot_handlers/     # Bot 消息处理
│   ├── services/         # 业务逻辑
│   └── utils/            # 工具函数
└── uploads/              # 文件上传目录
```
