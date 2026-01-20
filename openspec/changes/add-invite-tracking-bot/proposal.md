# Change: 添加 Telegram 邀请链接追踪机器人系统

## Why

需要构建一个完整的 Telegram 机器人系统,用于:
1. 追踪不同邀请链接带来的用户来源
2. 向用户展示可配置的媒体内容(视频/图片/媒体组)
3. 在翻页浏览时展示赞助商广告
4. 提供 Web 后台管理邀请链接、资源和广告
5. 在统计群中查询数据报表
6. 在客服群中快速识别用户来源

## What Changes

### 新增功能模块

**1. Bot 核心功能 (bot-core)**
- Deep Link 邀请链接追踪
- 封面视频播放
- 资源翻页浏览(渐进式等待 2/3/4/5/5/5/5 秒)
- 赞助商广告展示(顺序轮播)
- 预览结束提示
- 用户状态管理(FSM)

**2. Web 后台管理 (web-admin)**
- 管理员登录(用户名+密码)
- 邀请链接 CRUD
- 资源上传与管理(支持媒体组)
- 赞助商广告管理
- 广告组与邀请链接绑定
- 统计数据可视化(ECharts)

**3. 统计群功能 (stats-group)**
- `/query <名称>` 查询单个链接报表
- `/total` 查询总报表
- 近 7 天/30 天数据统计

**4. 客服群功能 (service-group)**
- 转发消息自动识别用户
- 查询用户来源
- 生成可复制的用户信息(每行一个字段)

### 技术栈

| 组件 | 技术 |
|------|------|
| Bot 框架 | aiogram 3.x |
| Web 后端 | FastAPI |
| Web 前端 | Next.js 15 + ECharts |
| 数据库 | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| 部署环境 | Debian 12.8 |

## Impact

- Affected specs: 新建 4 个能力规格
  - `bot-core` - Bot 核心功能
  - `web-admin` - Web 后台管理
  - `stats-group` - 统计群功能
  - `service-group` - 客服群功能
- Affected code: 全新项目,无现有代码
