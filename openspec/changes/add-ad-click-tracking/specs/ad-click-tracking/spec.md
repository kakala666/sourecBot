## ADDED Requirements
### Requirement: 广告点击回调统计
系统 MUST 通过广告按钮回调记录 `ad_click` 统计事件。

#### Scenario: 用户点击广告按钮
- **WHEN** 用户点击广告按钮
- **THEN** 系统写入 `ad_click` 统计事件

### Requirement: 点击提示与引导跳转
系统 MUST 在点击后先提示“正在加载...”，并在 1-2 秒后提示“网络波动，请重试”，同时提供广告频道跳转按钮。

#### Scenario: 点击后消息流程
- **WHEN** 用户点击广告按钮
- **THEN** 立即发送“正在加载...”消息
- **AND** 1-2 秒后编辑为“网络波动，请重试”并附带跳转按钮

### Requirement: 统计接口复用
系统 MUST 继续复用现有统计接口字段与前端报表展示。

#### Scenario: 统计报表读取广告点击
- **WHEN** 管理端请求统计接口
- **THEN** `ad_click` 相关字段返回有效数据并在前端展示
