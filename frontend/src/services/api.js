import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
// NOTE: No admin key read here. /refresh is public, protected by server-side
// rate limiting (5/hour per IP via slowapi). VITE_ vars are compiled into
// the public bundle and visible in devtools — never use them as secrets.

export const getRiskScores = async () => {
    const response = await axios.get(`${API_URL}/risk-scores`);
    return response.data;
};

export const getHistory = async (locationId) => {
    const response = await axios.get(`${API_URL}/history/${locationId}`);
    return response.data;
};

export const getDashboardSummary = async () => {
    const response = await axios.get(`${API_URL}/dashboard-summary`);
    return response.data;
};

export const getAlerts = async () => {
    const response = await axios.get(`${API_URL}/alert-status`);
    return response.data;
};

export const refreshData = async () => {
    // Plain public POST — no auth header. Rate-limited server-side to 5/hour per IP.
    const response = await axios.post(`${API_URL}/refresh`);
    return response.data;
};
