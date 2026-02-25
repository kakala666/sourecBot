# Change: 恢复广告点击统计（回调统计 + 引导跳转）

## Why
当前广告按钮为直接跳转，导致 `ad_click` 事件不再记录，统计报表与接口的点击数据长期为 0，无法衡量广告效果。

## What Changes
- 广告按钮改为回调，点击后记录 `ad_click` 并发送提示消息
- 延迟 1-2 秒后提示“网络波动，请重试”，附带跳转按钮
- 不改动现有统计 API 与前端报表结构

## Impact
- Affected specs: ad-click-tracking
- Affected code: `backend/app/bot_handlers/pagination.py`
