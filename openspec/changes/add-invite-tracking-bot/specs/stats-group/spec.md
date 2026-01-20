## ADDED Requirements

### Requirement: 统计群权限控制

系统 SHALL 限制 Bot 只在指定的统计群内响应查询命令。

#### Scenario: 统计群内响应命令
- **WHEN** 用户在统计群内发送查询命令
- **THEN** Bot 响应并返回数据

#### Scenario: 其他群忽略
- **WHEN** Bot 被拉入其他群组
- **THEN** Bot 不响应任何消息

#### Scenario: 统计群标识
- **WHEN** 部署 Bot 时
- **THEN** 通过环境变量 STATS_GROUP_ID 指定统计群 ID

---

### Requirement: 单个邀请链接查询

系统 SHALL 支持查询单个邀请链接的统计数据。

#### Scenario: 查询成功
- **WHEN** 用户发送 `/query 百度推广`
- **THEN** Bot 返回该邀请链接的统计报表
- **AND** 包含近 7 天和近 30 天数据

#### Scenario: 查询不存在的链接
- **WHEN** 用户查询不存在的邀请链接名称
- **THEN** Bot 返回"未找到该邀请链接"提示

#### Scenario: 缺少参数
- **WHEN** 用户只发送 `/query` 不带参数
- **THEN** Bot 返回用法说明

---

### Requirement: 总报表查询

系统 SHALL 支持查询所有邀请链接的汇总统计。

#### Scenario: 查询总报表
- **WHEN** 用户发送 `/total`
- **THEN** Bot 返回所有邀请链接的统计汇总
- **AND** 每个链接显示近 7 天和近 30 天数据
- **AND** 最后显示总计数据

---

### Requirement: 统计报表内容

系统 SHALL 在报表中包含以下统计指标。

#### Scenario: 报表字段
- **WHEN** 返回统计报表
- **THEN** 包含以下字段:
  - 新增用户数
  - 总浏览量
  - 平均浏览页数
  - 广告展示次数
  - 广告点击次数
  - 广告点击率
