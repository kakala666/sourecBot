/**
 * API 客户端配置
 */
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9000';

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加 Token
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// 响应拦截器 - 处理 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// API 方法
export const authApi = {
  login: async (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },
  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

export const inviteLinksApi = {
  list: async () => {
    const response = await api.get('/invite-links');
    return response.data;
  },
  create: async (data: { name: string; code?: string }) => {
    const response = await api.post('/invite-links', data);
    return response.data;
  },
  update: async (id: number, data: { name?: string; is_active?: boolean }) => {
    const response = await api.patch(`/invite-links/${id}`, data);
    return response.data;
  },
  delete: async (id: number) => {
    await api.delete(`/invite-links/${id}`);
  },
};

export const resourcesApi = {
  list: async (inviteLinkId?: number) => {
    const params = inviteLinkId ? { invite_link_id: inviteLinkId } : {};
    const response = await api.get('/resources', { params });
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/resources', data);
    return response.data;
  },
  update: async (id: number, data: any) => {
    const response = await api.patch(`/resources/${id}`, data);
    return response.data;
  },
  delete: async (id: number) => {
    await api.delete(`/resources/${id}`);
  },
  setCover: async (id: number) => {
    const response = await api.post(`/resources/${id}/set-cover`);
    return response.data;
  },
};

export const sponsorsApi = {
  listGroups: async () => {
    const response = await api.get('/sponsors/groups');
    return response.data;
  },
  createGroup: async (name: string) => {
    const response = await api.post('/sponsors/groups', { name });
    return response.data;
  },
  deleteGroup: async (id: number) => {
    await api.delete(`/sponsors/groups/${id}`);
  },
  list: async (adGroupId?: number) => {
    const params = adGroupId ? { ad_group_id: adGroupId } : {};
    const response = await api.get('/sponsors', { params });
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/sponsors', data);
    return response.data;
  },
  update: async (id: number, data: any) => {
    const response = await api.patch(`/sponsors/${id}`, data);
    return response.data;
  },
  delete: async (id: number) => {
    await api.delete(`/sponsors/${id}`);
  },
  link: async (inviteLinkId: number, adGroupId: number) => {
    const response = await api.post('/sponsors/link', { invite_link_id: inviteLinkId, ad_group_id: adGroupId });
    return response.data;
  },
  unlink: async (inviteLinkId: number, adGroupId: number) => {
    await api.delete('/sponsors/link', { params: { invite_link_id: inviteLinkId, ad_group_id: adGroupId } });
  },
};

export const statisticsApi = {
  overview: async () => {
    const response = await api.get('/statistics/overview');
    return response.data;
  },
  links: async () => {
    const response = await api.get('/statistics/links');
    return response.data;
  },
  ads: async () => {
    const response = await api.get('/statistics/ads');
    return response.data;
  },
  daily: async (days: number = 7, inviteCode?: string) => {
    const params: any = { days };
    if (inviteCode) params.invite_code = inviteCode;
    const response = await api.get('/statistics/daily', { params });
    return response.data;
  },
};

export default api;
