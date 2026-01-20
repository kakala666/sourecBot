'use client';

import { useEffect, useState } from 'react';
import { Card, Form, Input, Button, message, Spin, Divider, Alert } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import { api } from '@/lib/api';

interface ConfigItem {
    key: string;
    value: string | null;
    description: string | null;
}

export default function SettingsPage() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [configs, setConfigs] = useState<ConfigItem[]>([]);
    const [form] = Form.useForm();

    useEffect(() => {
        loadConfigs();
    }, []);

    const loadConfigs = async () => {
        try {
            const response = await api.get('/config');
            setConfigs(response.data);

            // 设置表单初始值
            const initialValues: Record<string, string> = {};
            response.data.forEach((c: ConfigItem) => {
                initialValues[c.key] = c.value || '';
            });
            form.setFieldsValue(initialValues);
        } catch (error) {
            message.error('加载配置失败');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        const values = await form.validateFields();
        setSaving(true);

        try {
            // 逐个更新配置
            for (const [key, value] of Object.entries(values)) {
                await api.patch(`/config/${key}`, { value });
            }
            message.success('配置已保存');
        } catch (error) {
            message.error('保存失败');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <div className="flex justify-center items-center h-64"><Spin size="large" /></div>;
    }

    // 按功能分组配置
    const previewConfigs = configs.filter(c => c.key.startsWith('preview_'));
    const otherConfigs = configs.filter(c => !c.key.startsWith('preview_'));

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">系统设置</h1>
                <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
                    保存设置
                </Button>
            </div>

            <Form form={form} layout="vertical">
                <Card title="预览结束设置" className="mb-6">
                    <Alert
                        message="这些设置控制用户浏览完 5 个资源后显示的结束页面"
                        type="info"
                        showIcon
                        className="mb-4"
                    />

                    <Form.Item
                        name="preview_end_url"
                        label="跳转链接"
                        extra="用户点击按钮后跳转的链接,例如: https://t.me/your_channel"
                    >
                        <Input placeholder="https://t.me/your_channel" />
                    </Form.Item>

                    <Form.Item
                        name="preview_end_button"
                        label="按钮文字"
                        extra="跳转按钮上显示的文字"
                    >
                        <Input placeholder="🚀 进入官方平台" />
                    </Form.Item>

                    <Form.Item
                        name="preview_end_text"
                        label="提示文案"
                        extra="支持 HTML 格式,例如 <b>粗体</b>"
                    >
                        <Input.TextArea rows={4} placeholder="🎬 <b>预览结束</b>&#10;&#10;感谢观看!更多精彩内容请进入官方平台。" />
                    </Form.Item>
                </Card>

                <Card title="其他设置">
                    <Form.Item
                        name="preview_limit"
                        label="预览资源数量限制"
                        extra="用户最多可浏览的资源数量"
                    >
                        <Input type="number" style={{ width: 120 }} />
                    </Form.Item>

                    <Form.Item
                        name="wait_times"
                        label="翻页等待时间"
                        extra="每次翻页的等待秒数,用逗号分隔,例如: 2,3,4,5,5,5,5"
                    >
                        <Input placeholder="2,3,4,5,5,5,5" />
                    </Form.Item>

                    <Form.Item
                        name="remark_template"
                        label="客服备注模板"
                        extra="可用变量: {name} 用户名, {date} 日期, {source} 来源"
                    >
                        <Input placeholder="{name} {date}【{source}】" />
                    </Form.Item>
                </Card>
            </Form>
        </div>
    );
}
