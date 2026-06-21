import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// All requests send cookies automatically (withCredentials required for
// cross-origin httpOnly cookie auth between Vercel and Render).
const api = axios.create({
    baseURL: API_URL,
    withCredentials: true,
});

// Response interceptor to handle token refresh automatically
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        
        // If error is 401 and we haven't already retried this request
        if (error.response && error.response.status === 401 && !originalRequest._retry) {
            // Check if this request was the refresh request itself to avoid infinite loop
            if (originalRequest.url === '/auth/refresh' || originalRequest.url === '/auth/refresh-token') {
                return Promise.reject(error);
            }
            
            originalRequest._retry = true;
            try {
                // Attempt to refresh the access token cookie using the refresh token cookie
                await api.post('/auth/refresh');
                // Retry the original request
                return api(originalRequest);
            } catch (refreshError) {
                // If refreshing fails, clear user session and redirect to login
                window.location.href = '/login';
                return Promise.reject(refreshError);
            }
        }
        return Promise.reject(error);
    }
);

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

export const authVerifyEmail = async (token) =>
    (await api.get(`/auth/verify-email?token=${token}`)).data;

// ── Alert subscription endpoints ──────────────────────────────────────────────
export const getMySubscriptions = async () => 
    (await api.get('/alerts/my-subscriptions')).data;

export const subscribeToAlerts = async (locationId = null) => 
    (await api.post('/alerts/subscribe', { location_id: locationId })).data;

export const unsubscribeFromAlerts = async (preferenceId) => 
    (await api.delete(`/alerts/subscribe/${preferenceId}`)).data;


