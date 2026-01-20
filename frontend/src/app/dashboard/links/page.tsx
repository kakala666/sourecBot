'use client';

import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Switch, message, Space, Tag, Tooltip } from 'antd';
import { PlusOutlined, CopyOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { inviteLinksApi } from '@/lib/api';

interface InviteLink {
    id: number;
    code: string;
    name: string;
    is_active: boolean;
    deep_link: string;
    resource_count: number;
    user_count: number;
}

export default function LinksPage() {
    const [loading, setLoading] = useState(true);
    const [links, setLinks] = useState<InviteLink[]>([]);
    const [modalOpen, setModalOpen] = useState(false);
    const [editingLink, setEditingLink] = useState<InviteLink | null>(null);
    const [form] = Form.useForm();

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
        { title: '资源数', dataIndex: 'resource_count', key: 'resource_count' },
        { title: '用户数', dataIndex: 'user_count', key: 'user_count' },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: InviteLink) => (
                <Space>
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
        </div>
    );
}
