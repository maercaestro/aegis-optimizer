import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

const api = {
  // Get schedule data from the backend
  getSchedule: async (filename = 'latest_schedule_output.json') => {
    try {
      const response = await axios.get(`${API_URL}/results/${filename}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching schedule data:', error);
      throw error;
    }
  },

  // Other API calls can be added here
};

export default api;