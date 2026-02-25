## Context
统计面板当前只展示总用户与 7 天浏览等指标，且统计面板时间口径以 UTC 为基准。

## Goals / Non-Goals
- Goals:
  - 增加四项“今日”指标：新用户、浏览量、广告展示、广告点击
  - 统一统计面板所有时间口径为 UTC+8
- Non-Goals:
  - 不调整历史统计口径
  - 不重构统计接口结构

## Decisions
- Decision: 在 `statistics/overview` 中增加今日广告展示与点击字段
  - 原因: 复用现有概览接口与前端调用链
- Decision: 统计面板所有时间口径按 UTC+8 计算
  - 方案: 使用 UTC 时间 + 8 小时作为基准起点

## Risks / Trade-offs
- 风险: 与既有 UTC 口径不一致导致数据跳变
  - 缓解: 文案明确“UTC+8”

## Migration Plan
1) 更新后端统计计算口径
2) 更新前端统计面板展示
3) 手工核对一天内统计结果

## Open Questions
- 是否需要在界面显式标注“UTC+8”？
