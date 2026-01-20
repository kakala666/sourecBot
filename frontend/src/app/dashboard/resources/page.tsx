'use client';

import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Upload, Switch, message, Space, Tag, Select, Tooltip, Popconfirm } from 'antd';
import { PlusOutlined, UploadOutlined, EditOutlined, DeleteOutlined, StarOutlined, StarFilled } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { resourcesApi, inviteLinksApi, api } from '@/lib/api';

interface InviteLink {
    id: number;
    code: string;
    name: string;
}

interface MediaFile {
    id: number;
    file_type: string;
    telegram_file_id: string;
    position: number;
}

interface Resource {
    id: number;
    invite_link_id: number;
    title: string | null;
    description: string | null;
    media_type: string;
    display_order: number;
    is_cover: boolean;
    media_files: MediaFile[];
}

export default function ResourcesPage() {
    const [loading, setLoading] = useState(true);
    const [resources, setResources] = useState<Resource[]>([]);
    const [links, setLinks] = useState<InviteLink[]>([]);
    const [selectedLinkId, setSelectedLinkId] = useState<number | null>(null);
    const [modalOpen, setModalOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [form] = Form.useForm();

    useEffect(() => {
        loadLinks();
    }, []);

    useEffect(() => {
        if (selectedLinkId) {
            loadResources();
        }
    }, [selectedLinkId]);

    const loadLinks = async () => {
        try {
            const data = await inviteLinksApi.list();
            setLinks(data);
            if (data.length > 0) {
                setSelectedLinkId(data[0].id);
            }
        } catch (error) {
            message.error('加载链接失败');
        } finally {
            setLoading(false);
        }
    };

    const loadResources = async () => {
        if (!selectedLinkId) return;
        setLoading(true);
        try {
            const data = await resourcesApi.list(selectedLinkId);
            setResources(data);
        } catch (error) {
            message.error('加载资源失败');
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = () => {
        form.resetFields();
        setModalOpen(true);
    };

    const handleSubmit = async () => {
        const values = await form.validateFields();
        const { file, title, description, is_cover } = values;

        if (!file || !file.length) {
            message.error('请选择文件');
            return;
        }

        setUploading(true);
        const formData = new FormData();
        formData.append('file', file[0].originFileObj);
        formData.append('invite_link_id', String(selectedLinkId));
        if (title) formData.append('title', title);
        if (description) formData.append('description', description);
        formData.append('is_cover', String(is_cover || false));

        try {
            await api.post('/upload/file', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            message.success('上传成功');
            setModalOpen(false);
            loadResources();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '上传失败');
        } finally {
            setUploading(false);
        }
    };

    const handleSetCover = async (id: number) => {
        try {
            await resourcesApi.setCover(id);
            message.success('已设置为封面');
            loadResources();
        } catch (error) {
            message.error('设置失败');
        }
    };

    const handleDelete = async (id: number) => {
        try {
            await resourcesApi.delete(id);
            message.success('删除成功');
            loadResources();
        } catch (error) {
            message.error('删除失败');
        }
    };

    const columns = [
        { title: '排序', dataIndex: 'display_order', key: 'display_order', width: 60 },
        {
            title: '标题',
            dataIndex: 'title',
            key: 'title',
            render: (text: string | null) => text || <span className="text-gray-400">无标题</span>,
        },
        {
            title: '类型',
            dataIndex: 'media_type',
            key: 'media_type',
            render: (type: string) => {
                const colors: Record<string, string> = { photo: 'blue', video: 'purple', media_group: 'green' };
                const labels: Record<string, string> = { photo: '图片', video: '视频', media_group: '媒体组' };
                return <Tag color={colors[type]}>{labels[type] || type}</Tag>;
            },
        },
        {
            title: '文件数',
            key: 'files',
            render: (_: any, record: Resource) => record.media_files?.length || 0,
        },
        {
            title: '封面',
            dataIndex: 'is_cover',
            key: 'is_cover',
            render: (isCover: boolean, record: Resource) => (
                <Button
                    type="text"
                    icon={isCover ? <StarFilled className="text-yellow-500" /> : <StarOutlined />}
                    onClick={() => !isCover && handleSetCover(record.id)}
                />
            ),
        },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: Resource) => (
                <Space>
                    <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
                        <Button icon={<DeleteOutlined />} size="small" danger />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    const normFile = (e: any) => {
        if (Array.isArray(e)) return e;
        return e?.fileList;
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-4">
                    <h1 className="text-2xl font-bold">资源管理</h1>
                    <Select
                        style={{ width: 200 }}
                        placeholder="选择邀请链接"
                        value={selectedLinkId}
                        onChange={setSelectedLinkId}
                        options={links.map(l => ({ value: l.id, label: l.name }))}
                    />
                </div>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleUpload} disabled={!selectedLinkId}>
                    上传资源
                </Button>
            </div>

            {!selectedLinkId ? (
                <div className="text-center text-gray-500 py-20">请先选择或创建邀请链接</div>
            ) : (
                <Table
                    columns={columns}
                    dataSource={resources}
                    rowKey="id"
                    loading={loading}
                />
            )}

            <Modal
                title="上传资源"
                open={modalOpen}
                onOk={handleSubmit}
                onCancel={() => setModalOpen(false)}
                confirmLoading={uploading}
            >
                <Form form={form} layout="vertical">
                    <Form.Item
                        name="file"
                        label="选择文件"
                        valuePropName="fileList"
                        getValueFromEvent={normFile}
                        rules={[{ required: true, message: '请选择文件' }]}
                    >
                        <Upload beforeUpload={() => false} maxCount={1} accept="image/*,video/*">
                            <Button icon={<UploadOutlined />}>选择图片或视频</Button>
                        </Upload>
                    </Form.Item>
                    <Form.Item name="title" label="标题">
                        <Input placeholder="可选" />
                    </Form.Item>
                    <Form.Item name="description" label="描述/文案">
                        <Input.TextArea placeholder="可选" rows={3} />
                    </Form.Item>
                    <Form.Item name="is_cover" label="设为封面" valuePropName="checked">
                        <Switch />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
