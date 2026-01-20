'use client';

import { useEffect, useState } from 'react';
import { Layout, Menu, Button, Avatar, Dropdown, message } from 'antd';
import {
    DashboardOutlined,
    LinkOutlined,
    FileImageOutlined,
    NotificationOutlined,
    BarChartOutlined,
    LogoutOutlined,
    UserOutlined,
    SettingOutlined,
} from '@ant-design/icons';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/store';

const { Header, Sider, Content } = Layout;

interface DashboardLayoutProps {
    children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
    const router = useRouter();
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);
    const { user, logout, isAuthenticated } = useAuthStore();

    useEffect(() => {
        if (!isAuthenticated()) {
            router.push('/login');
        }
    }, [isAuthenticated, router]);

    const handleLogout = () => {
        logout();
        message.success('已退出登录');
        router.push('/login');
    };

    const menuItems = [
        { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
        { key: '/dashboard/links', icon: <LinkOutlined />, label: '邀请链接' },
        { key: '/dashboard/resources', icon: <FileImageOutlined />, label: '资源管理' },
        { key: '/dashboard/sponsors', icon: <NotificationOutlined />, label: '广告管理' },
        { key: '/dashboard/statistics', icon: <BarChartOutlined />, label: '统计报表' },
        { key: '/dashboard/settings', icon: <SettingOutlined />, label: '系统设置' },
    ];

    const userMenuItems = [
        { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
    ];

    return (
        <Layout className="min-h-screen">
            <Sider
                collapsible
                collapsed={collapsed}
                onCollapse={setCollapsed}
                theme="dark"
                className="!fixed left-0 top-0 bottom-0 z-10"
            >
                <div className="h-16 flex items-center justify-center text-white text-xl font-bold">
                    {collapsed ? 'SB' : 'SourceBot'}
                </div>
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[pathname]}
                    items={menuItems}
                    onClick={({ key }) => router.push(key)}
                />
            </Sider>

            <Layout className={collapsed ? 'ml-20' : 'ml-52'} style={{ transition: 'margin-left 0.2s' }}>
                <Header className="!bg-white !px-6 flex items-center justify-between shadow-sm">
                    <div className="text-lg font-medium">
                        {menuItems.find(item => item.key === pathname)?.label || '管理后台'}
                    </div>
                    <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                        <div className="flex items-center gap-2 cursor-pointer">
                            <Avatar icon={<UserOutlined />} />
                            <span>{user?.username || 'admin'}</span>
                        </div>
                    </Dropdown>
                </Header>

                <Content className="m-6 p-6 bg-white rounded-lg min-h-[calc(100vh-112px)]">
                    {children}
                </Content>
            </Layout>
        </Layout>
    );
}
