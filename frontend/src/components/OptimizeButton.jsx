import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import axios from 'axios';

const OptimizeButton = ({ scheduleData, onScheduleOptimized }) => {
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [optimizationSummary, setOptimizationSummary] = useState(null);
  const [optimizeParams, setOptimizeParams] = useState({
    min_threshold: 80.0,
    max_daily_change: 10.0
  });

  const handleParamChange = (e) => {
    const { name, value } = e.target;
    setOptimizeParams({
      ...optimizeParams,
      [name]: parseFloat(value)
    });
  };
  
  // Calculate key metrics from schedule data
  const calculateMetrics = (schedule) => {
    if (!schedule || !schedule.daily_plan) return null;
    
    const days = Object.keys(schedule.daily_plan);
    
    // Calculate total processing volume
    let totalProcessing = 0;
    let minDailyRate = Infinity;
    let maxDailyRate = 0;
    
    days.forEach(day => {
      const rates = schedule.daily_plan[day].processing_rates || {};
      const dayTotal = Object.values(rates).reduce((sum, rate) => sum + rate, 0);
      
      totalProcessing += dayTotal;
      minDailyRate = Math.min(minDailyRate, dayTotal);
      maxDailyRate = Math.max(maxDailyRate, dayTotal);
    });
    
    return {
      totalProcessing: Math.round(totalProcessing),
      minDailyRate: Math.round(minDailyRate),
      maxDailyRate: Math.round(maxDailyRate),
      avgDailyRate: Math.round(totalProcessing / days.length),
      daysCount: days.length
    };
  };

  const handleOptimize = async () => {
    try {
      setIsOptimizing(true);
      toast.loading('Optimizing schedule...', { id: 'optimize' });
      
      // Calculate metrics before optimization
      const beforeMetrics = calculateMetrics(scheduleData);

      const response = await axios.post('http://localhost:5001/optimize-schedule', optimizeParams);
      
      if (response.data.status === 'success') {
        toast.success('Schedule optimized successfully!', { id: 'optimize' });
        
        const optimizedSchedule = response.data.schedule;
        
        // Calculate metrics after optimization
        const afterMetrics = calculateMetrics(optimizedSchedule);
        
        // Compare before/after and show summary
        if (beforeMetrics && afterMetrics) {
          setOptimizationSummary({
            before: beforeMetrics,
            after: afterMetrics,
            improvement: {
              totalProcessing: afterMetrics.totalProcessing - beforeMetrics.totalProcessing,
              minDailyRate: afterMetrics.minDailyRate - beforeMetrics.minDailyRate,
              maxDailyRate: afterMetrics.maxDailyRate - beforeMetrics.maxDailyRate,
              avgDailyRate: afterMetrics.avgDailyRate - beforeMetrics.avgDailyRate
            }
          });
        }
        
        if (onScheduleOptimized && optimizedSchedule) {
          onScheduleOptimized(optimizedSchedule);
        }
      } else {
        toast.error(`Optimization failed: ${response.data.message}`, { id: 'optimize' });
      }
    } catch (error) {
      console.error('Optimization error:', error);
      toast.error(`Optimization failed: ${error.response?.data?.message || error.message}`, { id: 'optimize' });
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">LP Optimization</h3>
        <button
          className="text-sm text-blue-600 hover:text-blue-800"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
        </button>
      </div>

      {showAdvanced && (
        <div className="mb-4 grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Min Processing (kb/day)
            </label>
            <input
              type="number"
              name="min_threshold"
              value={optimizeParams.min_threshold}
              onChange={handleParamChange}
              className="w-full border rounded-md px-3 py-2"
              min="0"
              step="5"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Daily Change (kb)
            </label>
            <input
              type="number"
              name="max_daily_change"
              value={optimizeParams.max_daily_change}
              onChange={handleParamChange}
              className="w-full border rounded-md px-3 py-2"
              min="0"
              step="1"
            />
          </div>
        </div>
      )}
      
      {optimizationSummary && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md">
          <h4 className="font-medium text-green-800 mb-2">Optimization Results</h4>
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div className="text-gray-500">Metric</div>
            <div className="text-gray-500">Before → After</div>
            <div className="text-gray-500">Improvement</div>
            
            <div>Total Processing</div>
            <div>{optimizationSummary.before.totalProcessing} → {optimizationSummary.after.totalProcessing} kb</div>
            <div className={optimizationSummary.improvement.totalProcessing >= 0 ? "text-green-600" : "text-red-600"}>
              {optimizationSummary.improvement.totalProcessing > 0 ? "+" : ""}
              {optimizationSummary.improvement.totalProcessing} kb
            </div>
            
            <div>Min Daily Rate</div>
            <div>{optimizationSummary.before.minDailyRate} → {optimizationSummary.after.minDailyRate} kb/day</div>
            <div className={optimizationSummary.improvement.minDailyRate >= 0 ? "text-green-600" : "text-red-600"}>
              {optimizationSummary.improvement.minDailyRate > 0 ? "+" : ""}
              {optimizationSummary.improvement.minDailyRate} kb/day
            </div>
            
            <div>Avg Daily Rate</div>
            <div>{optimizationSummary.before.avgDailyRate} → {optimizationSummary.after.avgDailyRate} kb/day</div>
            <div className={optimizationSummary.improvement.avgDailyRate >= 0 ? "text-green-600" : "text-red-600"}>
              {optimizationSummary.improvement.avgDailyRate > 0 ? "+" : ""}
              {optimizationSummary.improvement.avgDailyRate} kb/day
            </div>
          </div>
        </div>
      )}

      <button
        className={`w-full flex justify-center items-center space-x-2 px-4 py-2 rounded-md ${
          isOptimizing
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-green-600 hover:bg-green-700 text-gray-700'
        }`}
        onClick={handleOptimize}
        disabled={isOptimizing}
      >
        {isOptimizing ? (
          <>
            <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Optimizing...</span>
          </>
        ) : (
          <>
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                clipRule="evenodd"
              />
            </svg>
            <span>Optimize Schedule with LP</span>
          </>
        )}
      </button>

      <p className="text-xs text-gray-500 mt-2">
        Uses linear programming to maximize processing rates while maintaining operational constraints
      </p>
    </div>
  );
};

export default OptimizeButton;