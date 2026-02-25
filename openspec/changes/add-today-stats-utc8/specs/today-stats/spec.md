## ADDED Requirements
### Requirement: 今日统计指标
系统 MUST 在统计概览中提供今日新用户、今日浏览量、今日广告展示、今日广告点击四项指标。

#### Scenario: 获取统计概览
- **WHEN** 管理端请求统计概览
- **THEN** 返回四项“今日”指标数据

### Requirement: 今日口径为 UTC+8
系统 MUST 使用 UTC+8 的起止时间计算统计面板所有时间口径。

#### Scenario: 计算统计面板口径
- **WHEN** 计算统计面板相关时间统计
- **THEN** 以 UTC+8 当天 00:00:00 作为起点
