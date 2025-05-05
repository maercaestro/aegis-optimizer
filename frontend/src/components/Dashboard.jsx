import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ScheduleVisualizer from './ScheduleVisualizer';
import ChatBox from './ChatBox';
import api from '../services/api';
import { toast } from 'react-hot-toast';
// Import the logo
import logoAegis from '../assets/logo_aegis.png';
// Import the OptimizeButton component
import OptimizeButton from './OptimizeButton';

const Dashboard = () => {
  const [scheduleData, setScheduleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchScheduleData = async () => {
      try {
        setLoading(true);
        
        // Check if there's a generated schedule from the Feedstock page
        const savedSchedule = localStorage.getItem('generatedSchedule');
        if (savedSchedule) {
          // Use the saved schedule
          setScheduleData(JSON.parse(savedSchedule));
          // Clear it from localStorage so we don't use it again on refresh
          localStorage.removeItem('generatedSchedule');
          toast.success('Loaded newly generated schedule');
          setLoading(false);
          return;
        }
        
        // Otherwise get the schedule data from the API
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
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <img 
            src={logoAegis} 
            alt="Aegis Optimizer Logo" 
            className="h-20 w-auto object-contain mr-3 transition-transform hover:scale-105" 
            title="Aegis Optimizer"
          />
          <span className="text-lg text-gray-600 font-medium">Refinery Optimizer</span>
        </div>
        
        <Link 
          to="/feedstock"
          className="bg-blue-100 hover:bg-blue-300 text-gray-700 font-medium py-2 px-4 rounded inline-flex items-center transition-all"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          Create Custom Delivery Program
        </Link>
      </div>
      
      {/* Remove the Custom Delivery Program Section that contained the form */}
      
      {/* Add an info card highlighting the feature */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Info card from previous implementation */}
        <div className="bg-white shadow-md rounded-lg p-6">
          <div className="md:flex md:items-center">
            <div className="md:flex-shrink-0 flex items-center justify-center">
              <div className="rounded-full bg-blue-100 p-3">
                <svg className="h-8 w-8 text-blue-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
            </div>
            <div className="mt-4 md:mt-0 md:ml-6">
              <div className="text-xl font-bold text-gray-900">Schedule Visualization</div>
              <p className="mt-2 text-base text-gray-600">
                View the refinery schedule below. Need to work with different crude parcels? 
                Use the <Link to="/feedstock" className="text-blue-600 hover:underline font-medium">Custom Delivery Program</Link> tool.
              </p>
            </div>
          </div>
        </div>
        
        {/* Optimization button */}
        <OptimizeButton 
          scheduleData={scheduleData} 
          onScheduleOptimized={(optimizedSchedule) => {
            setScheduleData(optimizedSchedule);
            // Save to localStorage as a backup
            localStorage.setItem('latestScheduleData', JSON.stringify(optimizedSchedule));
          }} 
        />
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
        <div className="lg:col-span-1 bg-white rounded-lg shadow-md overflow-hidden">
          {/* Use overflow-hidden on the parent */}
          <div className="flex flex-col h-[calc(100vh-200px)] min-h-[600px] max-h-[800px]">
            {/* Add max-height to prevent excessive height */}
            <ChatBox scheduleData={scheduleData} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;