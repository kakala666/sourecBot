# Project Context

## Purpose

Telegram 邀请链接追踪机器人系统,用于:
- 追踪不同邀请链接带来的用户来源
- 向用户展示可配置的媒体内容和赞助商广告
- 提供 Web 后台管理邀请链接、资源和广告
- 在 Telegram 群组中查询统计数据和用户来源

## Tech Stack

- **Bot 框架**: Python 3.11+ / aiogram 3.x
- **Web 后端**: FastAPI / SQLAlchemy 2.0
- **Web 前端**: Next.js 15 / ECharts
- **数据库**: PostgreSQL
- **部署环境**: Debian 12.8 / systemd / Nginx

## Project Conventions

### Code Style
- Python: 遵循 PEP 8,使用 Black 格式化
- TypeScript: 使用 ESLint + Prettier
- 所有注释使用中文

### Architecture Patterns
- 后端: 分层架构 (Handlers → Services → Models)
- 前端: Next.js App Router + 组件化

### Testing Strategy
- 单元测试: pytest (Python) / Jest (TypeScript)
- 端到端测试: 手动验证核心流程

### Git Workflow
- 主分支: main
- 功能分支: feature/xxx
- 提交信息: 中文描述

## Domain Context

### Telegram Bot API
- Deep Link: `https://t.me/{BotUsername}?start={payload}`
- file_id: 媒体文件在 Telegram 服务器上的唯一标识
- 媒体组: 最多 10 个文件,只有第一个可带 caption

### 业务术语
- 邀请链接 (Invite Link): 带追踪参数的 Deep Link
- 资源 (Resource): 可发送给用户的媒体内容
- 封面 (Cover): 用户启动时首先看到的视频
- 广告组 (Ad Group): 一组赞助商广告的集合

## Important Constraints

- 无域名,使用 IP 地址访问
- 文件上传限制: 图片 10MB,视频 50MB
- Telegram Bot API 限制: 媒体组最多 10 个文件

## External Dependencies

- Telegram Bot API
- PostgreSQL 数据库
- Telegram 私有频道 (存储 file_id)
