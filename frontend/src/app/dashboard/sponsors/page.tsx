'use client';

import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Switch, message, Space, Tag, Tabs, Popconfirm, Select } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, LinkOutlined } from '@ant-design/icons';
import { sponsorsApi, inviteLinksApi } from '@/lib/api';

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

    const [groupForm] = Form.useForm();
    const [sponsorForm] = Form.useForm();
    const [linkForm] = Form.useForm();

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
        sponsorForm.setFieldsValue({ ad_group_id: selectedGroupId, is_active: true });
        setSponsorModalOpen(true);
    };

    const handleEditSponsor = (sponsor: Sponsor) => {
        setEditingSponsor(sponsor);
        sponsorForm.setFieldsValue(sponsor);
        setSponsorModalOpen(true);
    };

    const handleSubmitSponsor = async () => {
        const values = await sponsorForm.validateFields();
        try {
            if (editingSponsor) {
                await sponsorsApi.update(editingSponsor.id, values);
                message.success('更新成功');
            } else {
                await sponsorsApi.create({ ...values, ad_group_id: selectedGroupId });
                message.success('创建成功');
            }
            setSponsorModalOpen(false);
            loadSponsors();
        } catch (error) {
            message.error('操作失败');
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

    const columns = [
        { title: '排序', dataIndex: 'display_order', key: 'display_order', width: 60 },
        { title: '标题', dataIndex: 'title', key: 'title' },
        {
            title: '按钮',
            key: 'button',
            render: (_: any, r: Sponsor) => r.button_text ? `${r.button_text} → ${r.button_url?.slice(0, 30)}...` : '-',
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

                    <Table columns={columns} dataSource={sponsors} rowKey="id" loading={loading} />
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
            <Modal title={editingSponsor ? '编辑广告' : '添加广告'} open={sponsorModalOpen} onOk={handleSubmitSponsor} onCancel={() => setSponsorModalOpen(false)} width={600}>
                <Form form={sponsorForm} layout="vertical">
                    <Form.Item name="title" label="标题" rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item name="description" label="描述">
                        <Input.TextArea rows={2} />
                    </Form.Item>
                    <Form.Item name="button_text" label="按钮文字">
                        <Input placeholder="例如: 立即访问" />
                    </Form.Item>
                    <Form.Item name="button_url" label="跳转链接">
                        <Input placeholder="https://..." />
                    </Form.Item>
                    <Form.Item name="display_order" label="排序">
                        <Input type="number" defaultValue={0} />
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
