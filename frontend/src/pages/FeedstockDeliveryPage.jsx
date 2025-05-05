import React from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import FeedstockDeliveryForm from '../components/FeedstockDeliveryForm';
import logoAegis from '../assets/logo_aegis.png';

const FeedstockDeliveryPage = () => {
  const navigate = useNavigate();
  
  const handleScheduleGenerated = (schedule) => {
    // Store the generated schedule in localStorage to be accessible from Dashboard
    localStorage.setItem('generatedSchedule', JSON.stringify(schedule));
    
    // Show success message
    toast.success('Schedule generated successfully!');
    
    // Navigate back to dashboard
    navigate('/');
  };

  return (
    <div className="w-full px-4 py-6 sm:px-6 lg:px-8">
      {/* Header with logo and back button */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <img 
            src={logoAegis} 
            alt="Aegis Optimizer Logo" 
            className="h-20 w-auto object-contain mr-3" 
            title="Aegis Optimizer"
          />
          <span className="text-lg text-gray-600 font-medium">Refinery Optimizer</span>
        </div>
        
        <button 
          onClick={() => navigate('/')}
          className="bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold py-2 px-4 rounded inline-flex items-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
          </svg>
          Back to Dashboard
        </button>
      </div>
      
      <div className="bg-white shadow-md rounded-lg p-6 mb-6">
        <h1 className="text-3xl font-bold mb-2">Custom Delivery Program</h1>
        <p className="mb-6 text-gray-700">
          Create your own feedstock delivery program by specifying crude grades, loading date ranges, and volumes.
          The system will generate an optimized schedule based on your input while maintaining all other refinery constraints.
        </p>
        
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">Important</h3>
              <p className="text-sm text-blue-700">
                The system requires a minimum of 80 kb/day processing for a 30-day period (2,400 kb total).
              </p>
            </div>
          </div>
        </div>
        
        <FeedstockDeliveryForm onScheduleGenerated={handleScheduleGenerated} />
      </div>
    </div>
  );
};

export default FeedstockDeliveryPage;