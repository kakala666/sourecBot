'use client';

import { useEffect, useState } from 'react';
import { Table, Card, Spin, Statistic, Row, Col } from 'antd';
import dynamic from 'next/dynamic';
import { statisticsApi } from '@/lib/api';

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

export default function StatisticsPage() {
    const [loading, setLoading] = useState(true);
    const [linkStats, setLinkStats] = useState<LinkStats[]>([]);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const data = await statisticsApi.links();
            setLinkStats(data);
        } catch (error) {
            console.error('加载失败:', error);
        } finally {
            setLoading(false);
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

            <Card title="各链接统计">
                <Table
                    columns={columns}
                    dataSource={linkStats}
                    rowKey="link_id"
                    pagination={false}
                />
            </Card>
        </div>
    );
}
