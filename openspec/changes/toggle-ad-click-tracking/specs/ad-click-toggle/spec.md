## ADDED Requirements
### Requirement: 广告点击统计开关
系统 MUST 提供全局开关以禁用广告点击统计。

#### Scenario: 配置页切换开关
- **WHEN** 管理员在配置页关闭“广告点击统计”
- **THEN** 系统停止记录 `ad_click` 统计事件

### Requirement: 禁用时直接跳转
系统 MUST 在禁用统计时让广告按钮直接跳转到广告链接，不显示提示信息。

#### Scenario: 点击广告按钮（禁用统计）
- **WHEN** 用户点击广告按钮且开关为禁用
- **THEN** 直接跳转到广告链接
- **AND** 不发送“正在加载...”或“网络波动”提示
