import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// All requests send cookies automatically (withCredentials required for
// cross-origin httpOnly cookie auth between Vercel and Render).
const api = axios.create({
    baseURL: API_URL,
    withCredentials: true,
});

// ── Data endpoints ────────────────────────────────────────────────────────────
export const getRiskScores      = async () => (await api.get('/risk-scores')).data;
export const getHistory         = async (id) => (await api.get(`/history/${id}`)).data;
export const getDashboardSummary = async () => (await api.get('/dashboard-summary')).data;
export const getAlerts          = async () => (await api.get('/alert-status')).data;
export const refreshData        = async () => (await api.post('/refresh')).data;

// ── Auth endpoints ────────────────────────────────────────────────────────────
export const authRegister = async (email, password) =>
    (await api.post('/auth/register', { email, password })).data;

export const authLogin = async (email, password) =>
    (await api.post('/auth/login', { email, password })).data;

export const authLogout = async () =>
    (await api.post('/auth/logout')).data;

export const authRefreshToken = async () =>
    (await api.post('/auth/refresh-token')).data;

export const authMe = async () =>
    (await api.get('/auth/me')).data;

export const authForgotPassword = async (email) =>
    (await api.post('/auth/forgot-password', { email })).data;

export const authResetPassword = async (token, new_password) =>
    (await api.post('/auth/reset-password', { token, new_password })).data;
