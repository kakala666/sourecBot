'use client';

import { useEffect, useState } from 'react';
import { Table, Card, Spin, Statistic, Row, Col, Tabs, Select } from 'antd';
import dynamic from 'next/dynamic';
import { statisticsApi, inviteLinksApi, api } from '@/lib/api';

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

interface LinkStats {
    link_id: number;
    link_name: string;
    link_code: string;
    users_7d: number;
    users_30d: number;
    users_total: number;
    views_7d: number;
    views_30d: number;
    ad_views_7d: number;
    ad_clicks_7d: number;
    ctr: number;
}

interface FunnelStep {
    step: string;
    page: number;
    users: number;
    rate: number;
    total_rate: number;
}

interface FunnelStats {
    total_starts: number;
    steps: FunnelStep[];
}

interface InviteLink {
    id: number;
    code: string;
    name: string;
}

export default function StatisticsPage() {
    const [loading, setLoading] = useState(true);
    const [linkStats, setLinkStats] = useState<LinkStats[]>([]);
    const [funnelStats, setFunnelStats] = useState<FunnelStats | null>(null);
    const [links, setLinks] = useState<InviteLink[]>([]);
    const [selectedLinkCode, setSelectedLinkCode] = useState<string | undefined>(undefined);
    const [funnelDays, setFunnelDays] = useState(7);

    useEffect(() => {
        loadData();
    }, []);

    useEffect(() => {
        loadFunnel();
    }, [selectedLinkCode, funnelDays]);

    const loadData = async () => {
        try {
            const [linksData, statsData] = await Promise.all([
                inviteLinksApi.list(),
                statisticsApi.links(),
            ]);
            setLinks(linksData);
            setLinkStats(statsData);
        } catch (error) {
            console.error('加载失败:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadFunnel = async () => {
        try {
            const params: any = { days: funnelDays };
            if (selectedLinkCode) params.invite_code = selectedLinkCode;
            const response = await api.get('/statistics/funnel', { params });
            setFunnelStats(response.data);
        } catch (error) {
            console.error('加载漏斗数据失败:', error);
        }
    };

    const columns = [
        { title: '链接名称', dataIndex: 'link_name', key: 'link_name' },
        { title: '邀请码', dataIndex: 'link_code', key: 'link_code' },
        { title: '7天新用户', dataIndex: 'users_7d', key: 'users_7d' },
        { title: '30天新用户', dataIndex: 'users_30d', key: 'users_30d' },
        { title: '总用户', dataIndex: 'users_total', key: 'users_total' },
        { title: '7天浏览量', dataIndex: 'views_7d', key: 'views_7d' },
        { title: '7天广告展示', dataIndex: 'ad_views_7d', key: 'ad_views_7d' },
        { title: '7天广告点击', dataIndex: 'ad_clicks_7d', key: 'ad_clicks_7d' },
        {
            title: '点击率',
            dataIndex: 'ctr',
            key: 'ctr',
            render: (v: number) => `${v.toFixed(2)}%`,
        },
    ];

    // 漏斗图配置
    const getFunnelOption = () => {
        if (!funnelStats) return {};

        const data = [
            { name: '启动用户', value: funnelStats.total_starts },
            ...funnelStats.steps.map(s => ({ name: s.step, value: s.users })),
        ];

        return {
            title: {
                text: '用户留存漏斗',
                left: 'center',
            },
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} 人',
            },
            series: [
                {
                    name: '漏斗',
                    type: 'funnel',
                    left: '10%',
                    top: 60,
                    bottom: 60,
                    width: '80%',
                    min: 0,
                    max: funnelStats.total_starts || 100,
                    minSize: '0%',
                    maxSize: '100%',
                    sort: 'descending',
                    gap: 2,
                    label: {
                        show: true,
                        position: 'inside',
                        formatter: (params: any) => {
                            const rate = funnelStats.total_starts > 0
                                ? (params.value / funnelStats.total_starts * 100).toFixed(1)
                                : 0;
                            return `${params.name}\n${params.value}人 (${rate}%)`;
                        },
                    },
                    itemStyle: {
                        borderColor: '#fff',
                        borderWidth: 1,
                    },
                    data,
                },
            ],
        };
    };

    // 流失分析表格
    const funnelColumns = [
        { title: '步骤', dataIndex: 'step', key: 'step' },
        { title: '用户数', dataIndex: 'users', key: 'users' },
        {
            title: '相对留存率',
            dataIndex: 'rate',
            key: 'rate',
            render: (v: number) => `${v}%`,
        },
        {
            title: '总体转化率',
            dataIndex: 'total_rate',
            key: 'total_rate',
            render: (v: number) => `${v}%`,
        },
        {
            title: '流失率',
            key: 'churn',
            render: (_: any, r: FunnelStep) => `${(100 - r.rate).toFixed(1)}%`,
        },
    ];

    if (loading) {
        return <div className="flex justify-center items-center h-64"><Spin size="large" /></div>;
    }

    // 汇总统计
    const totalUsers = linkStats.reduce((sum, l) => sum + l.users_total, 0);
    const totalViews7d = linkStats.reduce((sum, l) => sum + l.views_7d, 0);
    const totalAdViews = linkStats.reduce((sum, l) => sum + l.ad_views_7d, 0);
    const totalAdClicks = linkStats.reduce((sum, l) => sum + l.ad_clicks_7d, 0);
    const avgCtr = totalAdViews > 0 ? (totalAdClicks / totalAdViews * 100) : 0;

    return (
        <div>
            <h1 className="text-2xl font-bold mb-6">统计报表</h1>

            <Row gutter={16} className="mb-6">
                <Col span={6}>
                    <Card><Statistic title="总用户" value={totalUsers} /></Card>
                </Col>
                <Col span={6}>
                    <Card><Statistic title="7天浏览量" value={totalViews7d} /></Card>
                </Col>
                <Col span={6}>
                    <Card><Statistic title="7天广告展示" value={totalAdViews} /></Card>
                </Col>
                <Col span={6}>
                    <Card><Statistic title="平均点击率" value={avgCtr.toFixed(2)} suffix="%" /></Card>
                </Col>
            </Row>

            <Tabs
                items={[
                    {
                        key: 'links',
                        label: '链接统计',
                        children: (
                            <Card>
                                <Table
                                    columns={columns}
                                    dataSource={linkStats}
                                    rowKey="link_id"
                                    pagination={false}
                                />
                            </Card>
                        ),
                    },
                    {
                        key: 'funnel',
                        label: '用户行为漏斗',
                        children: (
                            <Card>
                                <div className="flex gap-4 mb-4">
                                    <Select
                                        style={{ width: 200 }}
                                        placeholder="全部链接"
                                        allowClear
                                        value={selectedLinkCode}
                                        onChange={setSelectedLinkCode}
                                        options={links.map(l => ({ value: l.code, label: l.name }))}
                                    />
                                    <Select
                                        style={{ width: 120 }}
                                        value={funnelDays}
                                        onChange={setFunnelDays}
                                        options={[
                                            { value: 7, label: '最近7天' },
                                            { value: 30, label: '最近30天' },
                                            { value: 90, label: '最近90天' },
                                        ]}
                                    />
                                </div>

                                <Row gutter={24}>
                                    <Col span={12}>
                                        <ReactECharts option={getFunnelOption()} style={{ height: 400 }} />
                                    </Col>
                                    <Col span={12}>
                                        <h3 className="text-lg font-semibold mb-4">流失节点分析</h3>
                                        <Table
                                            columns={funnelColumns}
                                            dataSource={funnelStats?.steps || []}
                                            rowKey="page"
                                            pagination={false}
                                            size="small"
                                        />
                                        {funnelStats && funnelStats.total_starts > 0 && (
                                            <div className="mt-4 p-4 bg-gray-50 rounded">
                                                <p className="font-semibold">分析洞察:</p>
                                                {funnelStats.steps.map((s, i) => {
                                                    const churn = 100 - s.rate;
                                                    if (churn > 50 && i > 0) {
                                                        return (
                                                            <p key={s.page} className="text-red-600">
                                                                ⚠️ {s.step} 流失率较高 ({churn.toFixed(1)}%),建议优化该页内容
                                                            </p>
                                                        );
                                                    }
                                                    return null;
                                                })}
                                                {funnelStats.steps.every(s => 100 - s.rate <= 50) && (
                                                    <p className="text-green-600">✅ 各步骤留存率良好</p>
                                                )}
                                            </div>
                                        )}
                                    </Col>
                                </Row>
                            </Card>
                        ),
                    },
                ]}
            />
        </div>
    );
}
