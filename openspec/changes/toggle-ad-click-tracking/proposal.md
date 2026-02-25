# Change: 广告点击统计全局开关

## Why
需要在后台配置页提供全局开关，用于禁用广告点击统计。禁用时点击广告按钮直接跳转，不提示、不统计。

## What Changes
- 配置页新增“禁用广告点击统计”开关
- 后端配置新增对应字段并下发
- 点击广告按钮逻辑根据开关切换：禁用则直接跳转

## Impact
- Affected specs: ad-click-toggle
- Affected code: `backend/app/api/config.py`、`backend/app/models/config.py`、`frontend/src/app/dashboard/config/page.tsx`、`backend/app/bot_handlers/pagination.py`
