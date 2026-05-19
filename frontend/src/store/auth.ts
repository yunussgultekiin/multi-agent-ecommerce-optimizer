import { create } from 'zustand';
import Cookies from 'js-cookie';
import api from '@/lib/api';
import type { User, QuotaInfo } from '@/types';

const QUOTA_LIMIT = 500;

interface AuthState {
  user: User | null;
  quota: QuotaInfo | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  fetchQuota: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  quota: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password });
    const { access_token, refresh_token } = res.data;
    Cookies.set('access_token', access_token, { expires: 1 });
    Cookies.set('refresh_token', refresh_token, { expires: 7 });
    set({ isAuthenticated: true, isLoading: false, user: { id: '', email } });
  },

  register: async (email: string, password: string) => {
    await api.post('/auth/register', { email, password });
  },

  logout: () => {
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
    set({ user: null, quota: null, isAuthenticated: false });
    if (typeof window !== 'undefined') {
      window.location.href = '/';
    }
  },

  fetchUser: async () => {
    try {
      const token = Cookies.get('access_token');
      if (!token) {
        set({ isLoading: false, isAuthenticated: false });
        return;
      }
      const res = await api.get('/auth/me');
      set({ user: res.data, isLoading: false, isAuthenticated: true });
    } catch {
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      set({ user: null, isLoading: false, isAuthenticated: false });
    }
  },

  fetchQuota: async () => {
    try {
      const res = await api.get('/analyze');
      const items: { status: string }[] = res.data?.items ?? [];
      const used = items.length;
      const remaining = Math.max(0, QUOTA_LIMIT - used);
      set({ quota: { used, limit: QUOTA_LIMIT, remaining } });
    } catch {
    }
  },
}));
