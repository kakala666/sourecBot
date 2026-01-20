## ADDED Requirements

### Requirement: Deep Link 邀请链接追踪

系统 SHALL 支持生成带参数的 Telegram Deep Link,用于追踪用户来源。

#### Scenario: 生成邀请链接
- **WHEN** 管理员创建新的邀请链接并指定名称
- **THEN** 系统生成唯一邀请码
- **AND** 生成格式为 `https://t.me/{BotUsername}?start={邀请码}` 的 Deep Link

#### Scenario: 用户通过邀请链接启动 Bot
- **WHEN** 新用户点击邀请链接并启动 Bot
- **THEN** 系统记录用户的 Telegram ID 和来源邀请码
- **AND** 发送该邀请链接配置的封面视频

#### Scenario: 老用户直接私聊 Bot
- **WHEN** 已有使用记录的用户直接私聊 Bot(未通过邀请链接)
- **THEN** 系统正常响应,使用该用户原有的来源信息

#### Scenario: 新用户直接私聊 Bot
- **WHEN** 没有使用记录的新用户直接私聊 Bot(未通过邀请链接)
- **THEN** 系统不做任何响应

---

### Requirement: 资源媒体播放

系统 SHALL 支持向用户发送配置的媒体资源(视频、图片、媒体组)。

#### Scenario: 发送封面视频
- **WHEN** 用户首次启动 Bot
- **THEN** 系统发送该邀请链接配置的封面视频
- **AND** 显示包含文案的 caption
- **AND** 附带"下一页"内联按钮

#### Scenario: 发送媒体组资源
- **WHEN** 用户翻页且下一个资源是媒体组
- **THEN** 系统发送媒体组(最多 10 个文件)
- **AND** 文案显示在第一个媒体的 caption 中

#### Scenario: 发送单个媒体资源
- **WHEN** 用户翻页且下一个资源是单个媒体
- **THEN** 系统发送该媒体(图片或视频)
- **AND** 显示配置的文案

---

### Requirement: 翻页等待与广告展示

系统 SHALL 在用户翻页时展示赞助商广告,并实现渐进式等待。

#### Scenario: 翻页触发广告
- **WHEN** 用户点击"下一页"按钮
- **THEN** 系统立即发送一条赞助商广告
- **AND** 广告来自该邀请链接绑定的广告组
- **AND** 广告按顺序轮播

#### Scenario: 渐进式等待时间
- **WHEN** 用户第 1 次翻页,**THEN** 等待 2 秒
- **WHEN** 用户第 2 次翻页,**THEN** 等待 3 秒
- **WHEN** 用户第 3 次翻页,**THEN** 等待 4 秒
- **WHEN** 用户第 4 次及以后翻页,**THEN** 等待 5 秒

#### Scenario: 倒计时提示
- **WHEN** 等待期间
- **THEN** 系统发送倒计时消息
- **AND** 每秒更新倒计时数字
- **AND** 等待结束后删除倒计时消息

#### Scenario: 广告点击统计
- **WHEN** 用户点击广告上的跳转按钮
- **THEN** 系统先记录点击事件
- **AND** 然后发送包含跳转链接的消息

---

### Requirement: 预览结束判断

系统 SHALL 根据资源数量和已播放数量判断预览是否结束。

#### Scenario: 资源少于 5 个
- **WHEN** 用户播放完所有资源(不含封面)
- **AND** 资源总数少于 5 个
- **THEN** 继续显示"下一页"按钮
- **AND** 用户点击后显示"预览结束"提示和跳转按钮

#### Scenario: 资源刚好 5 个
- **WHEN** 用户播放完第 5 个资源
- **AND** 资源总数刚好 5 个
- **THEN** 继续显示"下一页"按钮
- **AND** 用户点击后显示"预览结束"提示和跳转按钮

#### Scenario: 资源多于 5 个
- **WHEN** 用户播放完第 5 个资源
- **AND** 资源总数多于 5 个
- **THEN** 直接显示"预览结束"提示和跳转按钮
- **AND** 不再显示后续资源

---

### Requirement: 文件上传与 file_id 转换

系统 SHALL 支持上传媒体文件并转换为 Telegram file_id。

#### Scenario: 上传单个文件
- **WHEN** 管理员上传单个媒体文件(图片或视频)
- **THEN** 系统保存文件到临时目录
- **AND** 通过 Bot 发送到私有存储频道
- **AND** 提取 file_id 保存到数据库

#### Scenario: 上传媒体组
- **WHEN** 管理员上传多个文件(2-10 个)
- **THEN** 系统将这些文件作为一个媒体组处理
- **AND** 分别获取每个文件的 file_id

#### Scenario: 文件大小限制
- **WHEN** 上传的图片大于 10MB
- **OR** 上传的视频大于 50MB
- **THEN** 前端拒绝上传并显示错误提示
