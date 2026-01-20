'use client';

import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Switch, message, Space, Tag, Tabs, Popconfirm, Select, Upload } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, LinkOutlined, UploadOutlined, HolderOutlined } from '@ant-design/icons';
import { sponsorsApi, inviteLinksApi, api } from '@/lib/api';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface AdGroup {
    id: number;
    name: string;
    sponsors: Sponsor[];
    linked_invite_links: number[];
}

interface Sponsor {
    id: number;
    ad_group_id: number;
    title: string;
    description: string | null;
    media_type: string | null;
    telegram_file_id: string | null;
    button_text: string | null;
    button_url: string | null;
    is_active: boolean;
    display_order: number;
}

interface InviteLink {
    id: number;
    code: string;
    name: string;
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

export default function SponsorsPage() {
    const [loading, setLoading] = useState(true);
    const [adGroups, setAdGroups] = useState<AdGroup[]>([]);
    const [sponsors, setSponsors] = useState<Sponsor[]>([]);
    const [links, setLinks] = useState<InviteLink[]>([]);
    const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);

    const [groupModalOpen, setGroupModalOpen] = useState(false);
    const [sponsorModalOpen, setSponsorModalOpen] = useState(false);
    const [linkModalOpen, setLinkModalOpen] = useState(false);
    const [editingSponsor, setEditingSponsor] = useState<Sponsor | null>(null);
    const [uploading, setUploading] = useState(false);

    const [groupForm] = Form.useForm();
    const [sponsorForm] = Form.useForm();
    const [linkForm] = Form.useForm();

    // 拖拽传感器配置
    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

    useEffect(() => {
        loadData();
    }, []);

    useEffect(() => {
        if (selectedGroupId) {
            loadSponsors();
        }
    }, [selectedGroupId]);

    const loadData = async () => {
        try {
            const [groupsData, linksData] = await Promise.all([
                sponsorsApi.listGroups(),
                inviteLinksApi.list(),
            ]);
            setAdGroups(groupsData);
            setLinks(linksData);
            if (groupsData.length > 0) {
                setSelectedGroupId(groupsData[0].id);
            }
        } catch (error) {
            message.error('加载失败');
        } finally {
            setLoading(false);
        }
    };

    const loadSponsors = async () => {
        if (!selectedGroupId) return;
        try {
            const data = await sponsorsApi.list(selectedGroupId);
            setSponsors(data);
        } catch (error) {
            message.error('加载广告失败');
        }
    };

    // 广告组操作
    const handleCreateGroup = async () => {
        const values = await groupForm.validateFields();
        try {
            await sponsorsApi.createGroup(values.name);
            message.success('创建成功');
            setGroupModalOpen(false);
            loadData();
        } catch (error) {
            message.error('创建失败');
        }
    };

    const handleDeleteGroup = async (id: number) => {
        try {
            await sponsorsApi.deleteGroup(id);
            message.success('删除成功');
            loadData();
        } catch (error) {
            message.error('删除失败');
        }
    };

    // 广告操作
    const handleCreateSponsor = () => {
        setEditingSponsor(null);
        sponsorForm.resetFields();
        sponsorForm.setFieldsValue({ is_active: true });
        setSponsorModalOpen(true);
    };

    const handleEditSponsor = (sponsor: Sponsor) => {
        setEditingSponsor(sponsor);
        sponsorForm.setFieldsValue(sponsor);
        setSponsorModalOpen(true);
    };

    const handleSubmitSponsor = async () => {
        const values = await sponsorForm.validateFields();
        setUploading(true);

        try {
            if (editingSponsor) {
                // 编辑模式 - 使用 JSON
                await sponsorsApi.update(editingSponsor.id, values);
                message.success('更新成功');
            } else {
                // 创建模式 - 使用 FormData 支持文件上传
                const formData = new FormData();
                formData.append('ad_group_id', String(selectedGroupId));
                formData.append('title', values.title);
                formData.append('button_text', values.button_text || '');
                formData.append('button_url', values.button_url || '');
                formData.append('is_active', String(values.is_active ?? true));
                if (values.description) formData.append('description', values.description);

                // 支持多文件上传
                if (values.media && values.media.length > 0) {
                    values.media.forEach((file: any) => {
                        formData.append('files', file.originFileObj);
                    });
                    await api.post('/sponsors/with-media-group', formData, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                    });
                } else {
                    // 无媒体时使用 JSON 创建
                    await sponsorsApi.create({
                        ad_group_id: selectedGroupId,
                        title: values.title,
                        description: values.description,
                        button_text: values.button_text,
                        button_url: values.button_url,
                        is_active: values.is_active ?? true,
                    });
                }
                message.success('创建成功');
            }
            setSponsorModalOpen(false);
            loadSponsors();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '操作失败');
        } finally {
            setUploading(false);
        }
    };

    const handleDeleteSponsor = async (id: number) => {
        try {
            await sponsorsApi.delete(id);
            message.success('删除成功');
            loadSponsors();
        } catch (error) {
            message.error('删除失败');
        }
    };

    // 处理拖拽排序
    const handleDragEnd = async (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over || active.id === over.id) return;

        const oldIndex = sponsors.findIndex((s) => s.id === active.id);
        const newIndex = sponsors.findIndex((s) => s.id === over.id);
        const newSponsors = arrayMove(sponsors, oldIndex, newIndex);
        setSponsors(newSponsors);

        // 调用 API 保存排序
        try {
            await api.patch('/sponsors/reorder', {
                sponsor_ids: newSponsors.map((s) => s.id),
            });
            message.success('排序已保存');
        } catch (error) {
            message.error('保存排序失败');
            loadSponsors();
        }
    };

    // 绑定操作
    const handleLink = () => {
        linkForm.resetFields();
        linkForm.setFieldsValue({ ad_group_id: selectedGroupId });
        setLinkModalOpen(true);
    };

    const handleSubmitLink = async () => {
        const values = await linkForm.validateFields();
        try {
            await sponsorsApi.link(values.invite_link_id, selectedGroupId!);
            message.success('绑定成功');
            setLinkModalOpen(false);
            loadData();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '绑定失败');
        }
    };

    const selectedGroup = adGroups.find(g => g.id === selectedGroupId);

    const normFile = (e: any) => {
        if (Array.isArray(e)) return e;
        return e?.fileList;
    };

    const columns = [
        {
            title: '',
            key: 'drag',
            width: 40,
            render: () => <HolderOutlined style={{ cursor: 'grab', color: '#999' }} />,
        },
        { title: '序号', dataIndex: 'display_order', key: 'display_order', width: 60 },
        { title: '标题', dataIndex: 'title', key: 'title' },
        {
            title: '媒体',
            key: 'media',
            render: (_: any, r: Sponsor) => r.telegram_file_id ? <Tag color="blue">{r.media_type}</Tag> : <span className="text-gray-400">无</span>,
        },
        {
            title: '按钮',
            key: 'button',
            render: (_: any, r: Sponsor) => r.button_text ? `${r.button_text}` : '-',
        },
        {
            title: '状态',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (active: boolean) => <Tag color={active ? 'green' : 'red'}>{active ? '启用' : '禁用'}</Tag>,
        },
        {
            title: '操作',
            key: 'action',
            render: (_: any, r: Sponsor) => (
                <Space>
                    <Button icon={<EditOutlined />} size="small" onClick={() => handleEditSponsor(r)} />
                    <Popconfirm title="确定删除?" onConfirm={() => handleDeleteSponsor(r.id)}>
                        <Button icon={<DeleteOutlined />} size="small" danger />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h1 className="text-2xl font-bold">广告管理</h1>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => { groupForm.resetFields(); setGroupModalOpen(true); }}>
                    创建广告组
                </Button>
            </div>

            <Tabs
                activeKey={String(selectedGroupId)}
                onChange={(key) => setSelectedGroupId(Number(key))}
                items={adGroups.map(g => ({
                    key: String(g.id),
                    label: (
                        <span>
                            {g.name}
                            <Tag className="ml-2">{g.sponsors?.length || 0}</Tag>
                        </span>
                    ),
                }))}
            />

            {selectedGroupId && (
                <>
                    <div className="flex justify-between items-center my-4">
                        <div>
                            <span className="text-gray-500">已绑定链接: </span>
                            {selectedGroup?.linked_invite_links.map(id => {
                                const link = links.find(l => l.id === id);
                                return link ? <Tag key={id}>{link.name}</Tag> : null;
                            })}
                            {!selectedGroup?.linked_invite_links.length && <span className="text-gray-400">无</span>}
                        </div>
                        <Space>
                            <Button icon={<LinkOutlined />} onClick={handleLink}>绑定链接</Button>
                            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateSponsor}>添加广告</Button>
                        </Space>
                    </div>

                    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                        <SortableContext items={sponsors.map((s) => s.id)} strategy={verticalListSortingStrategy}>
                            <Table
                                columns={columns}
                                dataSource={sponsors}
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
                </>
            )}

            {/* 广告组 Modal */}
            <Modal title="创建广告组" open={groupModalOpen} onOk={handleCreateGroup} onCancel={() => setGroupModalOpen(false)}>
                <Form form={groupForm} layout="vertical">
                    <Form.Item name="name" label="名称" rules={[{ required: true }]}>
                        <Input placeholder="广告组名称" />
                    </Form.Item>
                </Form>
            </Modal>

            {/* 广告 Modal */}
            <Modal
                title={editingSponsor ? '编辑广告' : '添加广告'}
                open={sponsorModalOpen}
                onOk={handleSubmitSponsor}
                onCancel={() => setSponsorModalOpen(false)}
                width={600}
                confirmLoading={uploading}
            >
                <Form form={sponsorForm} layout="vertical">
                    <Form.Item name="title" label="标题" rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item name="description" label="描述">
                        <Input.TextArea rows={2} />
                    </Form.Item>
                    {!editingSponsor && (
                        <Form.Item
                            name="media"
                            label="广告素材 (可选,支持多个)"
                            valuePropName="fileList"
                            getValueFromEvent={normFile}
                            extra="可上传 1-10 个图片或视频,多个文件将作为媒体组发送"
                        >
                            <Upload beforeUpload={() => false} maxCount={10} multiple accept="image/*,video/*" listType="picture">
                                <Button icon={<UploadOutlined />}>选择图片或视频</Button>
                            </Upload>
                        </Form.Item>
                    )}
                    <Form.Item name="button_text" label="按钮文字" rules={[{ required: true }]}>
                        <Input placeholder="例如: 立即访问" />
                    </Form.Item>
                    <Form.Item name="button_url" label="跳转链接" rules={[{ required: true }]}>
                        <Input placeholder="https://..." />
                    </Form.Item>
                    <Form.Item name="is_active" label="启用" valuePropName="checked">
                        <Switch />
                    </Form.Item>
                </Form>
            </Modal>

            {/* 绑定 Modal */}
            <Modal title="绑定邀请链接" open={linkModalOpen} onOk={handleSubmitLink} onCancel={() => setLinkModalOpen(false)}>
                <Form form={linkForm} layout="vertical">
                    <Form.Item name="invite_link_id" label="选择链接" rules={[{ required: true }]}>
                        <Select options={links.map(l => ({ value: l.id, label: l.name }))} />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
