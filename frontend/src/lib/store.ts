/**
 * 全局状态管理
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
    token: string | null;
    user: { id: number; username: string; email?: string } | null;
    setAuth: (token: string, user: any) => void;
    logout: () => void;
    isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            token: null,
            user: null,
            setAuth: (token, user) => {
                localStorage.setItem('token', token);
                set({ token, user });
            },
            logout: () => {
                localStorage.removeItem('token');
                set({ token: null, user: null });
            },
            isAuthenticated: () => !!get().token,
        }),
        {
            name: 'auth-storage',
        }
    )
);
