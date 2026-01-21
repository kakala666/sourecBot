'use client';

import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Switch, message, Space, Tag, Tooltip, InputNumber } from 'antd';
import { PlusOutlined, CopyOutlined, EditOutlined, DeleteOutlined, LinkOutlined, DisconnectOutlined } from '@ant-design/icons';
import { inviteLinksApi } from '@/lib/api';
import api from '@/lib/api';

interface InviteLink {
    id: number;
    code: string;
    name: string;
    is_active: boolean;
    deep_link: string;
    resource_count: number;
    user_count: number;
    source_channel_id: number | null;
    source_channel_username: string | null;
    auto_collect_enabled: boolean;
}

export default function LinksPage() {
    const [loading, setLoading] = useState(true);
    const [links, setLinks] = useState<InviteLink[]>([]);
    const [modalOpen, setModalOpen] = useState(false);
    const [editingLink, setEditingLink] = useState<InviteLink | null>(null);
    const [form] = Form.useForm();

    // 频道绑定弹窗
    const [channelModalOpen, setChannelModalOpen] = useState(false);
    const [bindingLink, setBindingLink] = useState<InviteLink | null>(null);
    const [channelForm] = Form.useForm();

    useEffect(() => {
        loadLinks();
    }, []);

    const loadLinks = async () => {
        setLoading(true);
        try {
            const data = await inviteLinksApi.list();
            setLinks(data);
        } catch (error) {
            message.error('加载失败');
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = () => {
        setEditingLink(null);
        form.resetFields();
        setModalOpen(true);
    };

    const handleEdit = (link: InviteLink) => {
        setEditingLink(link);
        form.setFieldsValue(link);
        setModalOpen(true);
    };

    const handleDelete = async (id: number) => {
        Modal.confirm({
            title: '确认删除',
            content: '删除后无法恢复,确定要删除吗?',
            onOk: async () => {
                await inviteLinksApi.delete(id);
                message.success('删除成功');
                loadLinks();
            },
        });
    };

    const handleSubmit = async () => {
        const values = await form.validateFields();
        try {
            if (editingLink) {
                await inviteLinksApi.update(editingLink.id, values);
                message.success('更新成功');
            } else {
                await inviteLinksApi.create(values);
                message.success('创建成功');
            }
            setModalOpen(false);
            loadLinks();
        } catch (error) {
            message.error('操作失败');
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        message.success('已复制到剪贴板');
    };

    // 打开频道绑定弹窗
    const handleBindChannel = (link: InviteLink) => {
        setBindingLink(link);
        channelForm.setFieldsValue({
            channel_id: link.source_channel_id || '',
            channel_username: link.source_channel_username || '',
            auto_collect_enabled: link.auto_collect_enabled ?? true,
        });
        setChannelModalOpen(true);
    };

    // 提交频道绑定
    const handleChannelSubmit = async () => {
        if (!bindingLink) return;

        const values = await channelForm.validateFields();
        try {
            await api.patch(`/invite-links/${bindingLink.id}/bind-channel`, {
                channel_id: values.channel_id,
                channel_username: values.channel_username || null,
                auto_collect_enabled: values.auto_collect_enabled,
            });
            message.success('频道绑定成功');
            setChannelModalOpen(false);
            loadLinks();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '绑定失败');
        }
    };

    // 解绑频道
    const handleUnbindChannel = async (link: InviteLink) => {
        Modal.confirm({
            title: '确认解绑',
            content: '解绑后将停止自动采集该频道的资源,确定吗?',
            onOk: async () => {
                try {
                    await api.delete(`/invite-links/${link.id}/unbind-channel`);
                    message.success('已解绑频道');
                    loadLinks();
                } catch (error) {
                    message.error('解绑失败');
                }
            },
        });
    };

    // 切换自动采集
    const handleToggleCollect = async (link: InviteLink) => {
        try {
            await api.patch(`/invite-links/${link.id}/toggle-collect`);
            message.success(link.auto_collect_enabled ? '已暂停采集' : '已开启采集');
            loadLinks();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '操作失败');
        }
    };

    const columns = [
        { title: '名称', dataIndex: 'name', key: 'name' },
        { title: '邀请码', dataIndex: 'code', key: 'code' },
        {
            title: 'Deep Link',
            dataIndex: 'deep_link',
            key: 'deep_link',
            render: (text: string) => (
                <Space>
                    <Tooltip title={text}>
                        <span className="text-blue-500 truncate max-w-xs">{text}</span>
                    </Tooltip>
                    <Button icon={<CopyOutlined />} size="small" onClick={() => copyToClipboard(text)} />
                </Space>
            ),
        },
        {
            title: '状态',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (active: boolean) => (
                <Tag color={active ? 'green' : 'red'}>{active ? '启用' : '禁用'}</Tag>
            ),
        },
        {
            title: '绑定频道',
            key: 'channel',
            render: (_: any, record: InviteLink) => {
                if (record.source_channel_id) {
                    return (
                        <Space>
                            <Tag color={record.auto_collect_enabled ? 'blue' : 'default'}>
                                {record.source_channel_username
                                    ? `@${record.source_channel_username}`
                                    : record.source_channel_id}
                            </Tag>
                            <Tooltip title={record.auto_collect_enabled ? '点击暂停采集' : '点击开启采集'}>
                                <Switch
                                    size="small"
                                    checked={record.auto_collect_enabled}
                                    onChange={() => handleToggleCollect(record)}
                                />
                            </Tooltip>
                        </Space>
                    );
                }
                return <span style={{ color: '#999' }}>未绑定</span>;
            },
        },
        { title: '资源数', dataIndex: 'resource_count', key: 'resource_count' },
        { title: '用户数', dataIndex: 'user_count', key: 'user_count' },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: InviteLink) => (
                <Space>
                    {record.source_channel_id ? (
                        <Tooltip title="解绑频道">
                            <Button
                                icon={<DisconnectOutlined />}
                                size="small"
                                onClick={() => handleUnbindChannel(record)}
                            />
                        </Tooltip>
                    ) : (
                        <Tooltip title="绑定频道">
                            <Button
                                icon={<LinkOutlined />}
                                size="small"
                                type="primary"
                                onClick={() => handleBindChannel(record)}
                            />
                        </Tooltip>
                    )}
                    <Button icon={<EditOutlined />} size="small" onClick={() => handleEdit(record)} />
                    <Button icon={<DeleteOutlined />} size="small" danger onClick={() => handleDelete(record.id)} />
                </Space>
            ),
        },
    ];

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h1 className="text-2xl font-bold">邀请链接管理</h1>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                    创建链接
                </Button>
            </div>

            <Table
                columns={columns}
                dataSource={links}
                rowKey="id"
                loading={loading}
            />

            {/* 创建/编辑链接弹窗 */}
            <Modal
                title={editingLink ? '编辑链接' : '创建链接'}
                open={modalOpen}
                onOk={handleSubmit}
                onCancel={() => setModalOpen(false)}
            >
                <Form form={form} layout="vertical">
                    <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
                        <Input placeholder="例如: 百度推广" />
                    </Form.Item>
                    {!editingLink && (
                        <Form.Item name="code" label="邀请码 (可选)">
                            <Input placeholder="留空则自动生成" />
                        </Form.Item>
                    )}
                    {editingLink && (
                        <Form.Item name="is_active" label="状态" valuePropName="checked">
                            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
                        </Form.Item>
                    )}
                </Form>
            </Modal>

            {/* 频道绑定弹窗 */}
            <Modal
                title="绑定采集频道"
                open={channelModalOpen}
                onOk={handleChannelSubmit}
                onCancel={() => setChannelModalOpen(false)}
            >
                <Form form={channelForm} layout="vertical">
                    <Form.Item
                        name="channel_id"
                        label="频道 ID"
                        rules={[{ required: true, message: '请输入频道ID' }]}
                        extra="频道ID通常为负数，如 -1001234567890。可通过转发频道消息给 @userinfobot 获取"
                    >
                        <InputNumber
                            style={{ width: '100%' }}
                            placeholder="例如: -1001234567890"
                        />
                    </Form.Item>
                    <Form.Item
                        name="channel_username"
                        label="频道用户名 (可选)"
                        extra="如 @channel_name，仅用于显示"
                    >
                        <Input placeholder="例如: my_channel" />
                    </Form.Item>
                    <Form.Item
                        name="auto_collect_enabled"
                        label="自动采集"
                        valuePropName="checked"
                        extra="开启后，Bot 会自动将频道内的媒体消息采集为资源"
                    >
                        <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
