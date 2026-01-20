'use client';

import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Spin } from 'antd';
import {
    UserOutlined,
    EyeOutlined,
    LinkOutlined,
    FileImageOutlined,
} from '@ant-design/icons';
import dynamic from 'next/dynamic';
import { statisticsApi } from '@/lib/api';

// 动态导入 ECharts 避免 SSR 问题
const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

interface OverviewStats {
    total_users: number;
    users_today: number;
    total_views: number;
    views_today: number;
    active_links: number;
    total_resources: number;
}

interface DailyStats {
    date: string;
    users: number;
    views: number;
    ad_clicks: number;
}

export default function DashboardPage() {
    const [loading, setLoading] = useState(true);
    const [overview, setOverview] = useState<OverviewStats | null>(null);
    const [dailyStats, setDailyStats] = useState<DailyStats[]>([]);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [overviewData, dailyData] = await Promise.all([
                statisticsApi.overview(),
                statisticsApi.daily(7),
            ]);
            setOverview(overviewData);
            setDailyStats(dailyData.reverse());
        } catch (error) {
            console.error('加载数据失败:', error);
        } finally {
            setLoading(false);
        }
    };

    const chartOption = {
        tooltip: { trigger: 'axis' },
        legend: { data: ['新用户', '浏览量', '广告点击'] },
        xAxis: {
            type: 'category',
            data: dailyStats.map(d => d.date.slice(5)),
        },
        yAxis: { type: 'value' },
        series: [
            { name: '新用户', type: 'line', data: dailyStats.map(d => d.users), smooth: true },
            { name: '浏览量', type: 'line', data: dailyStats.map(d => d.views), smooth: true },
            { name: '广告点击', type: 'line', data: dailyStats.map(d => d.ad_clicks), smooth: true },
        ],
    };

    if (loading) {
        return <div className="flex justify-center items-center h-64"><Spin size="large" /></div>;
    }

    return (
        <div>
            <h1 className="text-2xl font-bold mb-6">仪表盘</h1>

            <Row gutter={16} className="mb-6">
                <Col span={6}>
                    <Card>
                        <Statistic
                            title="总用户数"
                            value={overview?.total_users || 0}
                            prefix={<UserOutlined />}
                            suffix={<span className="text-sm text-green-500">今日 +{overview?.users_today || 0}</span>}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card>
                        <Statistic
                            title="总浏览量"
                            value={overview?.total_views || 0}
                            prefix={<EyeOutlined />}
                            suffix={<span className="text-sm text-green-500">今日 +{overview?.views_today || 0}</span>}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card>
                        <Statistic
                            title="活跃链接"
                            value={overview?.active_links || 0}
                            prefix={<LinkOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card>
                        <Statistic
                            title="总资源数"
                            value={overview?.total_resources || 0}
                            prefix={<FileImageOutlined />}
                        />
                    </Card>
                </Col>
            </Row>

            <Card title="近 7 天趋势">
                <ReactECharts option={chartOption} style={{ height: 300 }} />
            </Card>
        </div>
    );
}
