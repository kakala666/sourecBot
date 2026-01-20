'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { authApi } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

const { Title } = Typography;

export default function LoginPage() {
    const [loading, setLoading] = useState(false);
    const router = useRouter();
    const setAuth = useAuthStore((state) => state.setAuth);

    const onFinish = async (values: { username: string; password: string }) => {
        setLoading(true);
        try {
            const data = await authApi.login(values.username, values.password);
            // 先保存 token,再调用 getMe
            localStorage.setItem('token', data.access_token);
            const user = await authApi.getMe();
            setAuth(data.access_token, user);
            message.success('登录成功');
            router.push('/dashboard');
        } catch (error: any) {
            message.error(error.response?.data?.detail || '登录失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600">
            <Card className="w-full max-w-md shadow-2xl">
                <div className="text-center mb-8">
                    <Title level={2} className="!mb-2">SourceBot</Title>
                    <p className="text-gray-500">邀请链接追踪管理后台</p>
                </div>

                <Form
                    name="login"
                    onFinish={onFinish}
                    autoComplete="off"
                    size="large"
                >
                    <Form.Item
                        name="username"
                        rules={[{ required: true, message: '请输入用户名' }]}
                    >
                        <Input prefix={<UserOutlined />} placeholder="用户名" />
                    </Form.Item>

                    <Form.Item
                        name="password"
                        rules={[{ required: true, message: '请输入密码' }]}
                    >
                        <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" loading={loading} block>
                            登录
                        </Button>
                    </Form.Item>
                </Form>

                <div className="text-center text-gray-400 text-sm">
                    默认账号: admin / admin123
                </div>
            </Card>
        </div>
    );
}
