'use client';

import { useEffect, useState } from 'react';
import { Table, Input, Select, Card, Tag, Space, message } from 'antd';
import { SearchOutlined, UserOutlined } from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import dayjs from 'dayjs';
import api from '@/lib/api';

const { Search } = Input;

// 用户类型定义
interface User {
    id: number;
    telegram_id: number;
    username: string | null;
    first_name: string | null;
    last_name: string | null;
    full_name: string;
    invite_code: string | null;
    invite_link_name: string | null;
    first_seen: string | null;
    last_active: string | null;
    current_page: number | null;
    wait_count: number | null;
}

interface UserListResponse {
    items: User[];
    total: number;
    page: number;
    page_size: number;
}

interface InviteLink {
    id: number;
    code: string;
    name: string;
}

export default function UsersPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [search, setSearch] = useState('');
    const [inviteCode, setInviteCode] = useState<string | undefined>(undefined);
    const [inviteLinks, setInviteLinks] = useState<InviteLink[]>([]);

    // 加载邀请链接列表（用于筛选）
    const loadInviteLinks = async () => {
        try {
            const res = await api.get('/invite-links');
            setInviteLinks(res.data);
        } catch (err) {
            console.error('加载邀请链接失败:', err);
        }
    };

    // 加载用户列表
    const loadUsers = async () => {
        setLoading(true);
        try {
            const params: Record<string, unknown> = {
                page,
                page_size: pageSize,
            };
            if (search) params.search = search;
            if (inviteCode) params.invite_code = inviteCode;

            const res = await api.get<UserListResponse>('/users', { params });
            setUsers(res.data.items);
            setTotal(res.data.total);
        } catch (err) {
            message.error('加载用户列表失败');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadInviteLinks();
    }, []);

    useEffect(() => {
        loadUsers();
    }, [page, pageSize, search, inviteCode]);

    // 处理搜索
    const handleSearch = (value: string) => {
        setSearch(value);
        setPage(1);
    };

    // 处理来源筛选
    const handleInviteCodeChange = (value: string | undefined) => {
        setInviteCode(value);
        setPage(1);
    };

    // 处理分页变化
    const handleTableChange = (pagination: TablePaginationConfig) => {
        setPage(pagination.current || 1);
        setPageSize(pagination.pageSize || 20);
    };

    // 表格列定义
    const columns: ColumnsType<User> = [
        {
            title: 'Telegram ID',
            dataIndex: 'telegram_id',
            key: 'telegram_id',
            width: 140,
            render: (id: number) => (
                <a
                    href={`https://t.me/${id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontFamily: 'monospace' }}
                >
                    {id}
                </a>
            ),
        },
        {
            title: '用户名',
            dataIndex: 'username',
            key: 'username',
            width: 140,
            render: (username: string | null) =>
                username ? (
                    <a
                        href={`https://t.me/${username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        @{username}
                    </a>
                ) : (
                    <span style={{ color: '#999' }}>-</span>
                ),
        },
        {
            title: '姓名',
            dataIndex: 'full_name',
            key: 'full_name',
            width: 160,
            ellipsis: true,
        },
        {
            title: '来源链接',
            key: 'invite_link',
            width: 160,
            render: (_, record) =>
                record.invite_link_name ? (
                    <Tag color="blue">{record.invite_link_name}</Tag>
                ) : record.invite_code ? (
                    <Tag>{record.invite_code}</Tag>
                ) : (
                    <span style={{ color: '#999' }}>直接访问</span>
                ),
        },
        {
            title: '浏览进度',
            key: 'progress',
            width: 120,
            render: (_, record) => {
                if (record.current_page === null) {
                    return <span style={{ color: '#999' }}>-</span>;
                }
                return (
                    <Space>
                        <span>第 {record.current_page} 页</span>
                        {record.wait_count !== null && record.wait_count > 0 && (
                            <Tag color="orange">等待 {record.wait_count} 次</Tag>
                        )}
                    </Space>
                );
            },
        },
        {
            title: '首次使用',
            dataIndex: 'first_seen',
            key: 'first_seen',
            width: 160,
            render: (time: string | null) =>
                time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-',
        },
        {
            title: '最后活跃',
            dataIndex: 'last_active',
            key: 'last_active',
            width: 160,
            render: (time: string | null) =>
                time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-',
        },
    ];

    return (
        <div>
            <Card className="mb-4">
                <Space size="middle" wrap>
                    <Search
                        placeholder="搜索用户名/姓名"
                        allowClear
                        enterButton={<SearchOutlined />}
                        style={{ width: 280 }}
                        onSearch={handleSearch}
                    />
                    <Select
                        placeholder="按来源链接筛选"
                        allowClear
                        style={{ width: 200 }}
                        value={inviteCode}
                        onChange={handleInviteCodeChange}
                        options={inviteLinks.map((link) => ({
                            value: link.code,
                            label: link.name,
                        }))}
                    />
                    <span style={{ color: '#666' }}>
                        共 {total} 个用户
                    </span>
                </Space>
            </Card>

            <Card>
                <Table
                    columns={columns}
                    dataSource={users}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        current: page,
                        pageSize: pageSize,
                        total: total,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (t) => `共 ${t} 条`,
                        pageSizeOptions: ['10', '20', '50', '100'],
                    }}
                    onChange={handleTableChange}
                    scroll={{ x: 1000 }}
                />
            </Card>
        </div>
    );
}
