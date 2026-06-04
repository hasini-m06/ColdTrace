import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

export const refreshData = async () => {
    const response = await axios.post(`${API_URL}/refresh`);
    return response.data;
};
