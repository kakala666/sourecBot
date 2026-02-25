# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SourceBot is a Telegram invitation link tracking bot system (Telegram 邀请链接追踪机器人系统). It tracks user acquisition sources via Deep Links and delivers media content with sponsor advertisements.

**Tech Stack:**
- Backend: Python 3.11+ / FastAPI / aiogram 3.x / SQLAlchemy 2.0 / PostgreSQL
- Frontend: Next.js 15+ / React 19 / Ant Design 6 / ECharts / Zustand
- Deployment: Debian 12.8 / systemd / Nginx

## Build & Run Commands

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
python -m app.init_db
```

### Running Services
```bash
# Terminal 1 - Telegram Bot
cd backend && python -m app.bot

# Terminal 2 - API Server
cd backend && python -m uvicorn app.main:app --port 9000 --reload

# Terminal 3 - Frontend
cd frontend && npm install && npm run dev -- -p 3001
```

### Frontend Commands
```bash
npm run dev      # Development server
npm run build    # Production build
npm run lint     # ESLint
```

### Access Points
- Frontend: http://localhost:3001 (default: admin/admin123)
- API Docs: http://localhost:9000/docs

## Architecture

### Data Flow
```
Telegram User → Deep Link → Bot Handlers → PostgreSQL ← FastAPI API ← Next.js Dashboard
```

### Backend Structure (backend/app/)
- `bot.py` - Telegram bot entry point (aiogram)
- `main.py` - FastAPI application entry
- `bot_handlers/` - Telegram command handlers (start, pagination, stats_group, service_group, channel_collector)
- `api/` - FastAPI routes (auth, invite_links, resources, sponsors, statistics, upload)
- `models/` - SQLAlchemy ORM models
- `schemas/` - Pydantic request/response models
- `services/` - Business logic layer

### Frontend Structure (frontend/src/)
- `app/` - Next.js App Router pages
- `app/dashboard/` - Admin dashboard pages (links, resources, sponsors, statistics, settings, backup)
- `lib/api.ts` - Axios API client with auth interceptors
- `lib/store.ts` - Zustand auth state management

### Key Models
- **User** - Telegram users tracked via Deep Link (telegram_id, invite_code)
- **UserSession** - FSM state for pagination (current_page, wait_count, current_ad_index)
- **InviteLink** - Trackable invitation links with source_channel_id
- **Resource** - Media content with MediaFile children
- **AdGroup/Sponsor** - Advertisement groups and individual ads
- **Statistics** - Event tracking (user_start, page_view, ad_view, ad_click)

## Key Patterns

### Backend
- All database operations use async/await with SQLAlchemy 2.0
- JWT authentication via OAuth2PasswordBearer
- Dependency injection: `admin = Depends(get_current_admin)`

### Frontend
- All dashboard pages use `'use client'` directive
- Auth state persisted via Zustand + localStorage
- API calls through centralized `api.ts` with token refresh

### Telegram Bot (aiogram 3.x)
- Deep Link format: `https://t.me/{BotUsername}?start={invite_code}`
- Media groups: max 10 files, only first file can have caption
- file_id is unique per bot

## Environment Variables (backend/.env)

```bash
BOT_TOKEN=<telegram_bot_token>
STORAGE_CHANNEL_ID=-100xxx      # Private channel for file storage
STATS_GROUP_ID=-100xxx          # Statistics query group
SERVICE_GROUP_ID=-100xxx        # Customer service group
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/sourcebot
SECRET_KEY=<random_key>
```

## OpenSpec Workflow

This project uses spec-driven development. For new features or breaking changes:

1. Check existing specs: `openspec list --specs`
2. Check active changes: `openspec list`
3. Create proposal in `openspec/changes/<change-id>/`
4. Validate: `openspec validate <change-id> --strict --no-interactive`
5. Implement after approval

See `openspec/AGENTS.md` for detailed workflow.

## Language Requirements

- All code comments in Chinese (中文)
- All documentation in Chinese
- Commit messages in Chinese
- Plans and task lists in Chinese
