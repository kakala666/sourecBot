-- 002_add_invite_link_buttons.sql
-- 添加邀请链接自定义按钮表

CREATE TABLE IF NOT EXISTS invite_link_buttons (
    id SERIAL PRIMARY KEY,
    invite_link_id INTEGER NOT NULL REFERENCES invite_links(id) ON DELETE CASCADE,
    text VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引：按邀请链接ID查询
CREATE INDEX IF NOT EXISTS idx_invite_link_buttons_link_id ON invite_link_buttons(invite_link_id);

-- 注释
COMMENT ON TABLE invite_link_buttons IS '邀请链接自定义按钮表';
COMMENT ON COLUMN invite_link_buttons.invite_link_id IS '所属邀请链接ID';
COMMENT ON COLUMN invite_link_buttons.text IS '按钮文字';
COMMENT ON COLUMN invite_link_buttons.url IS '跳转链接';
COMMENT ON COLUMN invite_link_buttons.display_order IS '显示顺序';
COMMENT ON COLUMN invite_link_buttons.is_active IS '是否启用';
COMMENT ON COLUMN invite_link_buttons.created_at IS '创建时间';
