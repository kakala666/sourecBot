'use client';

import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Upload, Switch, message, Space, Tag, Select, Popconfirm, Radio, Alert } from 'antd';
import { PlusOutlined, UploadOutlined, DeleteOutlined, StarOutlined, StarFilled, HolderOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { resourcesApi, inviteLinksApi, api } from '@/lib/api';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

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

// 可排序行组件
function SortableRow({ children, ...props }: any) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
        id: props['data-row-key'],
    });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        cursor: 'move',
    };

    return (
        <tr {...props} ref={setNodeRef} style={style} {...attributes} {...listeners}>
            {children}
        </tr>
    );
}

export default function ResourcesPage() {
    const [loading, setLoading] = useState(true);
    const [resources, setResources] = useState<Resource[]>([]);
    const [links, setLinks] = useState<InviteLink[]>([]);
    const [selectedLinkId, setSelectedLinkId] = useState<number | null>(null);
    const [modalOpen, setModalOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadMode, setUploadMode] = useState<'single' | 'group'>('single');
    const [form] = Form.useForm();

    // 拖拽传感器配置
    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

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
        setUploadMode('single');
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
        formData.append('invite_link_id', String(selectedLinkId));
        if (title) formData.append('title', title);
        if (description) formData.append('description', description);

        try {
            if (uploadMode === 'single') {
                // 单文件上传
                formData.append('file', file[0].originFileObj);
                formData.append('is_cover', String(is_cover || false));
                await api.post('/upload/file', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
            } else {
                // 媒体组上传
                if (file.length < 2) {
                    message.error('媒体组至少需要 2 个文件');
                    setUploading(false);
                    return;
                }
                if (file.length > 10) {
                    message.error('媒体组最多 10 个文件');
                    setUploading(false);
                    return;
                }
                file.forEach((f: UploadFile) => {
                    formData.append('files', f.originFileObj as File);
                });
                await api.post('/upload/media-group', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
            }
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

    // 处理拖拽排序
    const handleDragEnd = async (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over || active.id === over.id) return;

        const oldIndex = resources.findIndex((r) => r.id === active.id);
        const newIndex = resources.findIndex((r) => r.id === over.id);
        const newResources = arrayMove(resources, oldIndex, newIndex);
        setResources(newResources);

        // 调用 API 保存排序
        try {
            await api.patch('/resources/reorder', {
                resource_ids: newResources.map((r) => r.id),
            });
            message.success('排序已保存');
        } catch (error) {
            message.error('保存排序失败');
            loadResources(); // 恢复原排序
        }
    };

    const columns = [
        {
            title: '',
            key: 'drag',
            width: 40,
            render: () => <HolderOutlined style={{ cursor: 'grab', color: '#999' }} />,
        },
        { title: '序号', dataIndex: 'display_order', key: 'display_order', width: 60 },
        {
            title: '标题',
            dataIndex: 'title',
            key: 'title',
            render: (text: string | null) => text || <span className="text-gray-400">无标题</span>,
        },
        {
            title: '描述/文案',
            dataIndex: 'description',
            key: 'description',
            ellipsis: true,
            render: (text: string | null) => text || <span className="text-gray-400">无描述</span>,
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
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                    <SortableContext items={resources.map((r) => r.id)} strategy={verticalListSortingStrategy}>
                        <Table
                            columns={columns}
                            dataSource={resources}
                            rowKey="id"
                            loading={loading}
                            components={{
                                body: {
                                    row: SortableRow,
                                },
                            }}
                            pagination={false}
                        />
                    </SortableContext>
                </DndContext>
            )}

            <Modal
                title="上传资源"
                open={modalOpen}
                onOk={handleSubmit}
                onCancel={() => setModalOpen(false)}
                confirmLoading={uploading}
                width={500}
            >
                <Form form={form} layout="vertical">
                    <Form.Item label="上传模式">
                        <Radio.Group value={uploadMode} onChange={(e) => setUploadMode(e.target.value)}>
                            <Radio.Button value="single">单个文件</Radio.Button>
                            <Radio.Button value="group">媒体组 (2-10个)</Radio.Button>
                        </Radio.Group>
                    </Form.Item>

                    {uploadMode === 'group' && (
                        <Alert
                            message="媒体组将作为一组发送,最少2个,最多10个文件"
                            type="info"
                            showIcon
                            className="mb-4"
                        />
                    )}

                    <Form.Item
                        name="file"
                        label="选择文件"
                        valuePropName="fileList"
                        getValueFromEvent={normFile}
                        rules={[{ required: true, message: '请选择文件' }]}
                    >
                        <Upload
                            beforeUpload={() => false}
                            maxCount={uploadMode === 'single' ? 1 : 10}
                            multiple={uploadMode === 'group'}
                            accept="image/*,video/*"
                            listType="picture"
                        >
                            <Button icon={<UploadOutlined />}>
                                {uploadMode === 'single' ? '选择图片或视频' : '选择多个文件'}
                            </Button>
                        </Upload>
                    </Form.Item>
                    <Form.Item name="title" label="标题">
                        <Input placeholder="可选" />
                    </Form.Item>
                    <Form.Item name="description" label="描述/文案">
                        <Input.TextArea placeholder="可选" rows={3} />
                    </Form.Item>
                    {uploadMode === 'single' && (
                        <Form.Item name="is_cover" label="设为封面" valuePropName="checked">
                            <Switch />
                        </Form.Item>
                    )}
                </Form>
            </Modal>
        </div>
    );
}
