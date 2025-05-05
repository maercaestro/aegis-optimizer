import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import axios from 'axios';

const FeedstockDeliveryForm = ({ onScheduleGenerated }) => {
  const [grades, setGrades] = useState([
    'Base', 'A', 'B', 'C', 'D', 'E', 'F'
  ]);
  
  const [deliveryProgram, setDeliveryProgram] = useState([
    {
      id: 'grade-base',
      grade: 'Base',
      parcels: [
        { id: 'base-1', startDay: 1, endDay: 3, volume: 400 },
        { id: 'base-2', startDay: 17, endDay: 19, volume: 360 }
      ]
    },
    {
      id: 'grade-a',
      grade: 'A',
      parcels: [
        { id: 'a-1', startDay: 1, endDay: 3, volume: 150 }
      ]
    }
    // Default with two grades only - user can add more
  ]);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState(null);
  const [calculationResult, setCalculationResult] = useState(null);

  // Add a new grade to the delivery program
  const addGrade = () => {
    // Find unused grades
    const usedGrades = deliveryProgram.map(item => item.grade);
    const unusedGrades = grades.filter(grade => !usedGrades.includes(grade));
    
    if (unusedGrades.length === 0) {
      toast.error('All available grades have been added');
      return;
    }
    
    const newGrade = unusedGrades[0];
    const newId = `grade-${newGrade.toLowerCase()}`;
    
    setDeliveryProgram([
      ...deliveryProgram,
      {
        id: newId,
        grade: newGrade,
        parcels: [
          { id: `${newGrade.toLowerCase()}-1`, startDay: 1, endDay: 3, volume: 200 }
        ]
      }
    ]);
  };

  // Remove a grade from the program
  const removeGrade = (gradeId) => {
    setDeliveryProgram(deliveryProgram.filter(item => item.id !== gradeId));
  };

  // Add a new parcel to a grade
  const addParcel = (gradeId) => {
    setDeliveryProgram(deliveryProgram.map(item => {
      if (item.id === gradeId) {
        const parcels = [...item.parcels];
        const lastParcel = parcels[parcels.length - 1];
        const newParcelId = `${item.grade.toLowerCase()}-${parcels.length + 1}`;
        
        // Default to a reasonable time frame
        const newStartDay = lastParcel ? lastParcel.endDay + 3 : 1;
        
        parcels.push({
          id: newParcelId,
          startDay: newStartDay,
          endDay: newStartDay + 2, // Default 3-day window
          volume: 200 // Default volume
        });
        
        return { ...item, parcels };
      }
      return item;
    }));
  };

  // Remove a parcel from a grade
  const removeParcel = (gradeId, parcelId) => {
    setDeliveryProgram(deliveryProgram.map(item => {
      if (item.id === gradeId) {
        if (item.parcels.length <= 1) {
          toast.error(`Cannot remove the only parcel for ${item.grade}. Remove the grade instead.`);
          return item;
        }
        return {
          ...item,
          parcels: item.parcels.filter(p => p.id !== parcelId)
        };
      }
      return item;
    }));
  };

  // Update a parcel's property
  const updateParcel = (gradeId, parcelId, field, value) => {
    setDeliveryProgram(deliveryProgram.map(item => {
      if (item.id === gradeId) {
        return {
          ...item,
          parcels: item.parcels.map(p => {
            if (p.id === parcelId) {
              let newValue = field === 'volume' ? Number(value) : value;
              
              // Special handling for date ranges
              if (field === 'endDay') {
                newValue = Math.max(p.startDay, Number(value));
              }
              
              return { ...p, [field]: newValue };
            }
            return p;
          })
        };
      }
      return item;
    }));
    
    // Clear validation
    setValidationError(null);
    setCalculationResult(null);
  };

  // Validate the form
  const validateForm = () => {
    if (deliveryProgram.length === 0) {
      setValidationError("At least one grade is required");
      return false;
    }
    
    for (const item of deliveryProgram) {
      if (item.parcels.length === 0) {
        setValidationError(`Grade ${item.grade} needs at least one parcel`);
        return false;
      }
      
      for (const parcel of item.parcels) {
        if (parcel.volume <= 0) {
          setValidationError(`All parcels must have a positive volume`);
          return false;
        }
        
        if (parcel.endDay < parcel.startDay) {
          setValidationError(`End day must be after or equal to start day for all parcels`);
          return false;
        }
        
        if (parcel.startDay < 1 || parcel.endDay > 31) {
          setValidationError(`Day values must be between 1 and 31`);
          return false;
        }
      }
    }
    
    return true;
  };

  // Format data for the backend
  const formatForBackend = () => {
    return deliveryProgram.map(item => {
      const ldrArray = item.parcels.map(p => `${p.startDay}-${p.endDay} Oct`);
      const parcelSizesArray = item.parcels.map(p => p.volume);
      
      const totalVolume = parcelSizesArray.reduce((sum, vol) => sum + vol, 0);
      
      return {
        grade: item.grade,
        volume_kb: totalVolume,
        ldr: ldrArray,
        parcel_sizes_kb: parcelSizesArray
      };
    });
  };

  // Submit the form
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // Format delivery program for backend
      const formattedProgram = formatForBackend();
      
      // Check volume sufficiency
      const totalVolume = formattedProgram.reduce((sum, grade) => 
        sum + grade.parcel_sizes_kb.reduce((s, vol) => s + vol, 0), 0);
      
      const requiredVolume = 30 * 80; // 30 days at 80 kb/day
      const isSufficient = totalVolume >= requiredVolume;
      const shortfall = Math.max(0, requiredVolume - totalVolume);
      
      setCalculationResult({
        isSufficient,
        totalVolume,
        requiredVolume,
        shortfall
      });
      
      if (!isSufficient) {
        toast.error(`Insufficient volume: ${totalVolume}kb. Need ${requiredVolume}kb (shortfall: ${shortfall}kb)`);
        setIsSubmitting(false);
        return;
      }
      
      // Send to backend to generate schedule
      const response = await axios.post('http://localhost:5001/generate-schedule-with-program', {
        feedstock_delivery_program: formattedProgram
      });
      
      toast.success('Schedule generated successfully!');
      
      // Pass to parent component
      if (onScheduleGenerated && response.data) {
        onScheduleGenerated(response.data);
      }
    } catch (error) {
      console.error('Error generating schedule:', error);
      toast.error('Failed to generate schedule: ' + (error.response?.data?.error || error.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white p-5 rounded-lg shadow-md">
      <h2 className="text-xl font-semibold mb-4">Feedstock Delivery Program</h2>
      
      <form onSubmit={handleSubmit}>
        {validationError && (
          <div className="bg-red-50 text-red-600 p-3 mb-4 rounded-md">
            {validationError}
          </div>
        )}
        
        {calculationResult && (
          <div className={`p-3 mb-4 rounded-md ${
            calculationResult.isSufficient ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-600'
          }`}>
            <p><strong>Total Volume:</strong> {calculationResult.totalVolume} kb</p>
            <p><strong>Required Volume:</strong> {calculationResult.requiredVolume} kb (30 days @ 80 kb/day)</p>
            {!calculationResult.isSufficient && (
              <p className="font-semibold mt-2">
                Please add {calculationResult.shortfall} kb more crude to meet minimum requirements
              </p>
            )}
          </div>
        )}
        
        {deliveryProgram.map(item => (
          <div key={item.id} className="mb-6 border rounded-md p-4 bg-gray-50">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-medium">
                Grade: <span className="text-blue-700">{item.grade}</span>
              </h3>
              <button 
                type="button"
                onClick={() => removeGrade(item.id)}
                className="text-red-600 hover:text-red-800"
              >
                Remove Grade
              </button>
            </div>
            
            <div className="space-y-3">
              {item.parcels.map(parcel => (
                <div key={parcel.id} className="flex flex-wrap gap-2 p-3 border rounded-md bg-white">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Start Day</label>
                    <input 
                      type="number" 
                      value={parcel.startDay}
                      onChange={(e) => updateParcel(item.id, parcel.id, 'startDay', parseInt(e.target.value, 10))}
                      min="1"
                      max="31"
                      className="w-24 border rounded-md px-3 py-2"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">End Day</label>
                    <input 
                      type="number" 
                      value={parcel.endDay}
                      onChange={(e) => updateParcel(item.id, parcel.id, 'endDay', parseInt(e.target.value, 10))}
                      min={parcel.startDay}
                      max="31"
                      className="w-24 border rounded-md px-3 py-2"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Volume (kb)</label>
                    <input 
                      type="number" 
                      value={parcel.volume}
                      onChange={(e) => updateParcel(item.id, parcel.id, 'volume', parseInt(e.target.value, 10))}
                      min="1"
                      className="w-32 border rounded-md px-3 py-2"
                    />
                  </div>
                  
                  <div className="ml-auto flex items-end">
                    <button 
                      type="button" 
                      onClick={() => removeParcel(item.id, parcel.id)}
                      className="bg-red-600 text-white px-3 py-2 rounded-md hover:bg-red-700 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
              
              <button
                type="button"
                onClick={() => addParcel(item.id)}
                className="mt-2 bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600"
              >
                Add Parcel to {item.grade}
              </button>
            </div>
            
            <div className="mt-3 pt-3 border-t">
              <p className="text-sm font-medium">
                Total Volume for {item.grade}: 
                <span className="ml-1 text-blue-700">
                  {item.parcels.reduce((sum, p) => sum + p.volume, 0)} kb
                </span>
              </p>
            </div>
          </div>
        ))}
        
        <div className="mb-6">
          <button
            type="button"
            onClick={addGrade}
            className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
            disabled={deliveryProgram.length >= grades.length}
          >
            Add Grade
          </button>
        </div>
        
        <div className="flex justify-end">
          <button 
            type="submit" 
            className={`px-4 py-2 rounded-md ${
              isSubmitting 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Processing...' : 'Generate Schedule'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default FeedstockDeliveryForm;