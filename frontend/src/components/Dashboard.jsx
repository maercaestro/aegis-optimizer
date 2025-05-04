import React, { useState, useEffect } from 'react';
import ScheduleVisualizer from './ScheduleVisualizer';
import ChatBox from './ChatBox';
import api from '../services/api';
import { toast } from 'react-hot-toast';
// Import the logo
import logoAegis from '../assets/logo_aegis.png';

const Dashboard = () => {
  const [scheduleData, setScheduleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchScheduleData = async () => {
      try {
        setLoading(true);
        // Get the schedule data from the API
        const data = await api.getSchedule('latest_schedule_output.json');
        setScheduleData(data);
      } catch (err) {
        console.error('Error fetching schedule data:', err);
        setError('Failed to load schedule data');
        toast.error('Failed to load schedule data');
      } finally {
        setLoading(false);
      }
    };

    fetchScheduleData();
  }, []);

  return (
    <div className="w-full px-4 py-6 sm:px-6 lg:px-8">
      {/* Header with logo on left */}
      <div className="flex items-center mb-6">
        <img 
          src={logoAegis} 
          alt="Aegis Optimizer Logo" 
          className="h-20 w-auto object-contain mr-3 transition-transform hover:scale-105" 
          title="Aegis Optimizer"
        />
        <span className="text-lg text-gray-600 font-medium">Refinery Optimizer</span>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content area - 2/3 width on large screens */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow-md">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            </div>
          ) : error ? (
            <div className="p-6 text-red-500">{error}</div>
          ) : scheduleData ? (
            <ScheduleVisualizer scheduleData={scheduleData} />
          ) : (
            <div className="p-6">No data available</div>
          )}
        </div>
        
        {/* Chatbox - 1/3 width on large screens */}
        <div className="lg:col-span-1 bg-white rounded-lg shadow-md">
          <ChatBox scheduleData={scheduleData} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;