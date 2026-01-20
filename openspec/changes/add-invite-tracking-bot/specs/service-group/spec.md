## ADDED Requirements

### Requirement: 客服群权限控制

系统 SHALL 限制 Bot 只在指定的客服群内响应转发消息。

#### Scenario: 客服群内响应转发消息
- **WHEN** 客服将用户在任意地方发送的消息转发到客服群
- **THEN** Bot 自动识别并返回该用户的来源信息

#### Scenario: 客服群标识
- **WHEN** 部署 Bot 时
- **THEN** 通过环境变量 SERVICE_GROUP_ID 指定客服群 ID

---

### Requirement: 转发消息自动识别

系统 SHALL 自动检测客服群中的转发消息,并查询原始发送者的来源信息。这是客服群的**主要交互方式**,无需输入任何命令。

#### Scenario: 客服转发用户消息
- **WHEN** 客服将用户在私聊、群组或频道中发送的消息转发到客服群
- **THEN** Bot 自动识别转发消息 (检测 forward_from 或 forward_sender_name 字段)
- **AND** 提取原始发送者的 Telegram ID
- **AND** 自动返回该用户的来源信息

#### Scenario: 用户已使用过 Bot
- **WHEN** 原始发送者有使用记录
- **THEN** Bot 返回该用户的完整信息

#### Scenario: 用户未使用过 Bot
- **WHEN** 原始发送者没有使用记录
- **THEN** Bot 返回"该用户未使用过本 Bot"
- **AND** 仍显示可复制的 Telegram ID

#### Scenario: 隐私保护限制
- **WHEN** 原始发送者设置了隐私保护 (forward_from 为空)
- **THEN** Bot 返回"无法识别用户身份,请使用 /check 命令手动查询"

---

### Requirement: 用户信息显示格式

系统 SHALL 以可复制的格式显示用户信息,每个字段单独一行。

#### Scenario: 信息显示格式
- **WHEN** 显示用户信息
- **THEN** 使用 `<code>` 标签包裹每个可复制字段
- **AND** 每行显示一个字段

#### Scenario: 显示字段列表
- **WHEN** 用户有完整信息
- **THEN** 显示以下字段 (每行一个,均可点击复制):
  - Telegram ID
  - 姓名
  - 用户名
  - 来源名称
  - 首次使用日期
  - 最后活跃时间
  - 客服备注 (格式: `{name} {date}【{source}】`)

---

### Requirement: 手动查询用户

系统 SHALL 支持通过命令手动查询用户信息。

#### Scenario: 通过 ID 查询
- **WHEN** 客服发送 `/check 123456789`
- **THEN** Bot 查询该 Telegram ID 对应的用户
- **AND** 返回与转发消息相同格式的用户信息

#### Scenario: 用户不存在
- **WHEN** 查询的 Telegram ID 不在数据库中
- **THEN** Bot 返回"未找到该用户"

---

### Requirement: 用户行为统计展示

系统 SHALL 在用户信息中提供详细统计的查看按钮。

#### Scenario: 查看详细统计
- **WHEN** 客服点击"查看详细统计"按钮
- **THEN** Bot 返回该用户的行为统计
- **AND** 包含: 浏览页数、广告点击次数、是否完成预览
