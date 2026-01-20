## ADDED Requirements

### Requirement: 管理员认证

系统 SHALL 提供管理员登录功能,使用用户名和密码认证。

#### Scenario: 管理员登录成功
- **WHEN** 管理员输入正确的用户名和密码
- **THEN** 系统返回 JWT Token
- **AND** Token 有效期为 24 小时

#### Scenario: 管理员登录失败
- **WHEN** 管理员输入错误的用户名或密码
- **THEN** 系统返回认证失败错误

#### Scenario: Token 验证
- **WHEN** 请求携带有效的 JWT Token
- **THEN** 系统允许访问受保护的 API

#### Scenario: Token 过期
- **WHEN** 请求携带过期的 JWT Token
- **THEN** 系统返回 401 未授权错误

---

### Requirement: 邀请链接管理

系统 SHALL 支持邀请链接的完整 CRUD 操作。

#### Scenario: 创建邀请链接
- **WHEN** 管理员提交邀请链接名称
- **THEN** 系统生成唯一邀请码
- **AND** 返回完整的 Deep Link

#### Scenario: 获取邀请链接列表
- **WHEN** 管理员请求邀请链接列表
- **THEN** 系统返回所有邀请链接
- **AND** 包含每个链接的资源数量和用户数量

#### Scenario: 更新邀请链接
- **WHEN** 管理员修改邀请链接的名称或状态
- **THEN** 系统更新相应记录

#### Scenario: 删除邀请链接
- **WHEN** 管理员删除邀请链接
- **THEN** 系统删除该链接及其关联的资源

---

### Requirement: 资源管理

系统 SHALL 支持资源的上传、编辑和排序。

#### Scenario: 上传资源
- **WHEN** 管理员上传媒体文件并填写标题和文案
- **THEN** 系统保存资源信息
- **AND** 转换为 file_id 存储

#### Scenario: 设置封面资源
- **WHEN** 管理员将某个资源设置为封面
- **THEN** 该资源标记为封面
- **AND** 原封面资源取消封面标记

#### Scenario: 更新资源排序
- **WHEN** 管理员调整资源的显示顺序
- **THEN** 系统更新所有受影响资源的 display_order

#### Scenario: 删除资源
- **WHEN** 管理员删除资源
- **THEN** 系统删除资源记录及其关联的媒体文件记录

---

### Requirement: 广告组管理

系统 SHALL 支持广告组的管理和邀请链接绑定。

#### Scenario: 创建广告组
- **WHEN** 管理员创建新的广告组
- **THEN** 系统保存广告组信息

#### Scenario: 绑定广告组到邀请链接
- **WHEN** 管理员将广告组绑定到邀请链接
- **THEN** 该邀请链接的用户将看到该广告组的广告

#### Scenario: 一个邀请链接绑定多个广告组
- **WHEN** 邀请链接绑定了多个广告组
- **THEN** 系统按顺序轮播所有广告组中的广告

---

### Requirement: 赞助商广告管理

系统 SHALL 支持赞助商广告的 CRUD 操作。

#### Scenario: 创建广告
- **WHEN** 管理员上传广告素材并填写信息
- **THEN** 系统保存广告到指定的广告组

#### Scenario: 广告信息包含
- **WHEN** 创建广告时
- **THEN** 必须包含: 标题、描述(可选)、媒体素材(可选)、按钮文字、跳转链接

#### Scenario: 更新广告显示顺序
- **WHEN** 管理员调整广告的 display_order
- **THEN** 影响广告的轮播顺序

---

### Requirement: 统计数据可视化

系统 SHALL 提供统计数据的查询和可视化展示。

#### Scenario: 概览统计
- **WHEN** 管理员访问仪表盘
- **THEN** 显示总用户数、今日新增、活跃链接数、总资源数

#### Scenario: 邀请链接统计
- **WHEN** 管理员查看邀请链接详情
- **THEN** 显示用户增长趋势图 (ECharts)
- **AND** 显示近 7 天/30 天数据

#### Scenario: 广告统计
- **WHEN** 管理员查看广告统计
- **THEN** 显示每个广告的展示次数、点击次数、点击率

#### Scenario: 用户行为统计
- **WHEN** 管理员查看用户行为分析
- **THEN** 显示留存漏斗(翻到第 N 页的用户占比)
- **AND** 显示流失节点分析
