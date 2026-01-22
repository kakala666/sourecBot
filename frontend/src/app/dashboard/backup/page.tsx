'use client';

import { useEffect, useState, useCallback } from 'react';
import {
    Card,
    Button,
    message,
    Spin,
    Alert,
    Input,
    Modal,
    Progress,
    Tag,
    Descriptions,
    Space,
    Popconfirm,
} from 'antd';
import {
    CloudSyncOutlined,
    DeleteOutlined,
    SwapOutlined,
    PlayCircleOutlined,
    PauseCircleOutlined,
    CheckCircleOutlined,
    ExclamationCircleOutlined,
    SyncOutlined,
} from '@ant-design/icons';
import { api } from '@/lib/api';

interface BackupConfig {
    id: number;
    backup_bot_username: string | null;
    backup_bot_id: number | null;
    is_active: boolean;
    sync_status: string;
    total_count: number;
    synced_count: number;
    failed_count: number;
    error_message: string | null;
    last_synced_at: string | null;
    created_at: string;
}

interface BackupStatus {
    has_config: boolean;
    config: BackupConfig | null;
    is_syncing: boolean;
}

export default function BackupPage() {
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState<BackupStatus | null>(null);
    const [tokenInput, setTokenInput] = useState('');
    const [creating, setCreating] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);

    const loadStatus = useCallback(async () => {
        try {
            const response = await api.get('/backup/status');
            setStatus(response.data);
        } catch (error) {
            message.error('加载备份状态失败');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadStatus();
    }, [loadStatus]);

    // 同步中时自动刷新
    useEffect(() => {
        if (status?.is_syncing) {
            const interval = setInterval(loadStatus, 3000);
            return () => clearInterval(interval);
        }
    }, [status?.is_syncing, loadStatus]);

    const handleCreate = async () => {
        if (!tokenInput.trim()) {
            message.error('请输入备份 Bot Token');
            return;
        }

        setCreating(true);
        try {
            await api.post('/backup/config', { token: tokenInput.trim() });
            message.success('备份配置已创建');
            setShowCreateModal(false);
            setTokenInput('');
            loadStatus();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '创建失败');
        } finally {
            setCreating(false);
        }
    };

    const handleDelete = async () => {
        try {
            await api.delete('/backup/config');
            message.success('备份配置已删除');
            loadStatus();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '删除失败');
        }
    };

    const handleStartSync = async () => {
        try {
            await api.post('/backup/sync/start');
            message.success('同步任务已启动');
            loadStatus();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '启动失败');
        }
    };

    const handleStopSync = async () => {
        try {
            await api.post('/backup/sync/stop');
            message.info('正在停止同步...');
            loadStatus();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '停止失败');
        }
    };

    const handleSwitchToBackup = async () => {
        try {
            await api.post('/backup/switch/backup');
            message.success('已切换到备份 Bot');
            loadStatus();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '切换失败');
        }
    };

    const handleSwitchToPrimary = async () => {
        try {
            await api.post('/backup/switch/primary');
            message.success('已切换回主 Bot');
            loadStatus();
        } catch (error: any) {
            message.error(error.response?.data?.detail || '切换失败');
        }
    };

    const getSyncStatusTag = (syncStatus: string) => {
        switch (syncStatus) {
            case 'pending':
                return <Tag icon={<ExclamationCircleOutlined />} color="warning">待同步</Tag>;
            case 'syncing':
                return <Tag icon={<SyncOutlined spin />} color="processing">同步中</Tag>;
            case 'synced':
                return <Tag icon={<CheckCircleOutlined />} color="success">已同步</Tag>;
            case 'error':
                return <Tag icon={<ExclamationCircleOutlined />} color="error">同步失败</Tag>;
            default:
                return <Tag>{syncStatus}</Tag>;
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Spin size="large" />
            </div>
        );
    }

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">备份管理</h1>
            </div>

            <Alert
                message="备份 Bot 功能说明"
                description={
                    <div>
                        <p>当主 Bot 因各种原因无法使用时，可以切换到备份 Bot 继续服务。</p>
                        <p className="mt-2">使用步骤：</p>
                        <ol className="list-decimal list-inside mt-1">
                            <li>创建一个新的 Telegram Bot 作为备份</li>
                            <li>将备份 Bot 添加为存储频道的管理员</li>
                            <li>在此页面配置备份 Bot Token</li>
                            <li>执行同步操作，将文件 ID 映射到备份 Bot</li>
                            <li>需要时点击"切换到备份 Bot"</li>
                        </ol>
                    </div>
                }
                type="info"
                showIcon
                className="mb-6"
            />

            {!status?.has_config ? (
                <Card>
                    <div className="text-center py-8">
                        <CloudSyncOutlined className="text-6xl text-gray-300 mb-4" />
                        <p className="text-gray-500 mb-4">尚未配置备份 Bot</p>
                        <Button type="primary" onClick={() => setShowCreateModal(true)}>
                            添加备份 Bot
                        </Button>
                    </div>
                </Card>
            ) : (
                <div className="space-y-6">
                    {/* 状态卡片 */}
                    <Card
                        title={
                            <Space>
                                <span>备份 Bot 状态</span>
                                {status.config?.is_active && (
                                    <Tag color="green">当前使用中</Tag>
                                )}
                            </Space>
                        }
                        extra={
                            <Space>
                                {!status.config?.is_active ? (
                                    <Popconfirm
                                        title="切换到备份 Bot"
                                        description="切换后所有资源和广告将通过备份 Bot 发送，确定切换吗？"
                                        onConfirm={handleSwitchToBackup}
                                        okText="确定"
                                        cancelText="取消"
                                    >
                                        <Button
                                            type="primary"
                                            icon={<SwapOutlined />}
                                            disabled={status.config?.sync_status !== 'synced'}
                                        >
                                            切换到备份 Bot
                                        </Button>
                                    </Popconfirm>
                                ) : (
                                    <Popconfirm
                                        title="切换回主 Bot"
                                        description="切换后所有资源和广告将通过主 Bot 发送，确定切换吗？"
                                        onConfirm={handleSwitchToPrimary}
                                        okText="确定"
                                        cancelText="取消"
                                    >
                                        <Button icon={<SwapOutlined />}>
                                            切换回主 Bot
                                        </Button>
                                    </Popconfirm>
                                )}
                                <Popconfirm
                                    title="删除备份配置"
                                    description="删除后所有同步数据将丢失，确定删除吗？"
                                    onConfirm={handleDelete}
                                    okText="确定"
                                    cancelText="取消"
                                    disabled={status.config?.is_active}
                                >
                                    <Button
                                        danger
                                        icon={<DeleteOutlined />}
                                        disabled={status.config?.is_active}
                                    >
                                        删除配置
                                    </Button>
                                </Popconfirm>
                            </Space>
                        }
                    >
                        <Descriptions column={2}>
                            <Descriptions.Item label="Bot 用户名">
                                @{status.config?.backup_bot_username || '-'}
                            </Descriptions.Item>
                            <Descriptions.Item label="Bot ID">
                                {status.config?.backup_bot_id || '-'}
                            </Descriptions.Item>
                            <Descriptions.Item label="同步状态">
                                {getSyncStatusTag(status.config?.sync_status || 'pending')}
                            </Descriptions.Item>
                            <Descriptions.Item label="创建时间">
                                {status.config?.created_at
                                    ? new Date(status.config.created_at).toLocaleString('zh-CN')
                                    : '-'}
                            </Descriptions.Item>
                            <Descriptions.Item label="最后同步">
                                {status.config?.last_synced_at
                                    ? new Date(status.config.last_synced_at).toLocaleString('zh-CN')
                                    : '从未同步'}
                            </Descriptions.Item>
                            <Descriptions.Item label="错误信息">
                                {status.config?.error_message || '-'}
                            </Descriptions.Item>
                        </Descriptions>
                    </Card>

                    {/* 同步进度卡片 */}
                    <Card title="文件同步">
                        <div className="mb-4">
                            <div className="flex justify-between mb-2">
                                <span>同步进度</span>
                                <span>
                                    {status.config?.synced_count || 0} / {status.config?.total_count || 0}
                                    {status.config?.failed_count ? (
                                        <span className="text-red-500 ml-2">
                                            ({status.config.failed_count} 失败)
                                        </span>
                                    ) : null}
                                </span>
                            </div>
                            <Progress
                                percent={
                                    status.config?.total_count
                                        ? Math.round(
                                              ((status.config?.synced_count || 0) /
                                                  status.config.total_count) *
                                                  100
                                          )
                                        : 0
                                }
                                status={
                                    status.config?.sync_status === 'error'
                                        ? 'exception'
                                        : status.config?.sync_status === 'synced'
                                        ? 'success'
                                        : 'active'
                                }
                            />
                        </div>

                        <Space>
                            {!status.is_syncing ? (
                                <Button
                                    type="primary"
                                    icon={<PlayCircleOutlined />}
                                    onClick={handleStartSync}
                                >
                                    开始同步
                                </Button>
                            ) : (
                                <Button
                                    icon={<PauseCircleOutlined />}
                                    onClick={handleStopSync}
                                >
                                    停止同步
                                </Button>
                            )}
                            <span className="text-gray-500">
                                {status.is_syncing
                                    ? '同步进行中，请勿关闭页面...'
                                    : '点击开始同步将文件 ID 映射到备份 Bot'}
                            </span>
                        </Space>
                    </Card>
                </div>
            )}

            {/* 创建配置弹窗 */}
            <Modal
                title="添加备份 Bot"
                open={showCreateModal}
                onOk={handleCreate}
                onCancel={() => {
                    setShowCreateModal(false);
                    setTokenInput('');
                }}
                confirmLoading={creating}
                okText="创建"
                cancelText="取消"
            >
                <Alert
                    message="前置条件"
                    description={
                        <ol className="list-decimal list-inside">
                            <li>已通过 @BotFather 创建新的 Bot</li>
                            <li>已将新 Bot 添加为存储频道的管理员</li>
                        </ol>
                    }
                    type="warning"
                    showIcon
                    className="mb-4"
                />
                <div>
                    <label className="block mb-2 font-medium">备份 Bot Token</label>
                    <Input.Password
                        placeholder="请输入备份 Bot 的 Token"
                        value={tokenInput}
                        onChange={(e) => setTokenInput(e.target.value)}
                    />
                    <p className="text-gray-500 text-sm mt-2">
                        从 @BotFather 获取的 Bot Token，格式如：123456789:ABCdefGHIjklMNOpqrsTUVwxyz
                    </p>
                </div>
            </Modal>
        </div>
    );
}
