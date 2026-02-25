# Change: 统计面板新增今日指标并统一为 UTC+8

## Why
后台统计面板缺少“今日新用户/今日浏览量/今日广告展示/今日广告点击”指标，且统计面板所有时间口径需统一为 UTC+8。

## What Changes
- 统计概览接口增加今日广告展示与今日广告点击字段
- 统计面板展示四项“今日”指标（UTC+8 口径）
- 统计面板所有时间口径统一为 UTC+8

## Impact
- Affected specs: today-stats
- Affected code: `backend/app/api/statistics.py`、`frontend/src/app/dashboard/statistics/page.tsx`
