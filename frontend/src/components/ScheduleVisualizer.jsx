import React, { useState } from 'react';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

// Define color scheme for different grades
const gradeColors = {
  'Base': 'rgba(75, 192, 192, 0.7)',
  'A': 'rgba(255, 99, 132, 0.7)',
  'B': 'rgba(54, 162, 235, 0.7)',
  'C': 'rgba(255, 206, 86, 0.7)',
  'D': 'rgba(153, 102, 255, 0.7)',
  'E': 'rgba(255, 159, 64, 0.7)',
  'F': 'rgba(199, 199, 199, 0.7)'
};

// Define base tank colors
const tankColors = {
  'Tank 1': 'rgba(255, 205, 86, 0.7)',   // Yellow
  'Tank 2': 'rgba(86, 255, 159, 0.7)',   // Green
  'Tank 3': 'rgba(86, 173, 255, 0.7)',   // Blue
  'Tank 4': 'rgba(255, 86, 86, 0.7)',    // Red
  'Tank 5': 'rgba(153, 102, 255, 0.7)',  // Purple
  'Tank 6': 'rgba(255, 159, 64, 0.7)',   // Orange
  'Tank 7': 'rgba(75, 192, 192, 0.7)',   // Teal
  'Tank 8': 'rgba(199, 199, 199, 0.7)'   // Gray
};

// Generate colors for tanks dynamically
const generateTankColor = (tankName) => {
  // Use existing colors if defined
  if (tankColors[tankName]) {
    return tankColors[tankName];
  }
  
  // Extract tank number if possible
  const tankNumber = parseInt(tankName.replace(/\D/g, ''), 10);
  
  // Base colors we can use
  const baseColors = [
    'rgba(255, 205, 86, 0.7)',   // Yellow
    'rgba(86, 255, 159, 0.7)',   // Green
    'rgba(86, 173, 255, 0.7)',   // Blue
    'rgba(255, 86, 86, 0.7)',    // Red
    'rgba(153, 102, 255, 0.7)',  // Purple
    'rgba(255, 159, 64, 0.7)',   // Orange
    'rgba(75, 192, 192, 0.7)',   // Teal
    'rgba(199, 199, 199, 0.7)',  // Gray
  ];
  
  // Use modulo to cycle through colors for additional tanks
  return baseColors[(tankNumber - 1) % baseColors.length] || baseColors[0];
};

const ScheduleVisualizer = ({ scheduleData }) => {
  const [viewMode, setViewMode] = useState('chart'); // 'chart' or 'table'
  const [chartType, setChartType] = useState('processing'); // 'processing', 'inventory', or 'vessels'
  
  // Extract days from the schedule data
  const days = Object.keys(scheduleData?.daily_plan || {}).sort((a, b) => parseInt(a) - parseInt(b));
  const tankNames = Object.keys(scheduleData?.daily_plan?.[days[0]]?.tanks || {});
  
  // Prepare processing rates data
  const prepareProcessingRatesData = () => {
    const datasets = Object.keys(gradeColors).map(grade => {
      const data = days.map(day => {
        return scheduleData?.daily_plan[day]?.processing_rates[grade] || 0;
      });
      
      return {
        label: `Grade ${grade}`,
        data,
        borderColor: gradeColors[grade].replace('0.7', '1'),
        backgroundColor: gradeColors[grade],
        borderWidth: 2,
        tension: 0.3
      };
    });
    
    // Calculate total processing rate
    const totalData = days.map(day => {
      const rates = scheduleData?.daily_plan[day]?.processing_rates || {};
      return Object.values(rates).reduce((sum, rate) => sum + rate, 0);
    });
    
    datasets.push({
      label: 'Total',
      data: totalData,
      borderColor: 'rgba(0, 0, 0, 1)',
      backgroundColor: 'rgba(0, 0, 0, 0.1)',
      borderWidth: 3,
      borderDash: [5, 5],
      tension: 0.3
    });
    
    return {
      labels: days.map(day => `Day ${day}`),
      datasets
    };
  };
  
  // Prepare inventory data
  const prepareInventoryData = () => {
    const datasets = Object.keys(gradeColors).map(grade => {
      const data = days.map(day => {
        return scheduleData?.daily_plan[day]?.inventory_by_grade[grade] || 0;
      });
      
      return {
        label: `Grade ${grade}`,
        data,
        borderColor: gradeColors[grade].replace('0.7', '1'),
        backgroundColor: gradeColors[grade],
        borderWidth: 2,
        tension: 0.3
      };
    });
    
    // Add total inventory
    const totalData = days.map(day => {
      return scheduleData?.daily_plan[day]?.inventory || 0;
    });
    
    datasets.push({
      label: 'Total Inventory',
      data: totalData,
      borderColor: 'rgba(0, 0, 0, 1)',
      backgroundColor: 'rgba(0, 0, 0, 0.1)',
      borderWidth: 3,
      borderDash: [5, 5],
      tension: 0.3
    });
    
    return {
      labels: days.map(day => `Day ${day}`),
      datasets
    };
  };
  
  // Prepare vessel arrivals data
  const prepareVesselArrivalsData = () => {
    // Create a map to store total cargo volume for each day
    const vesselVolumes = {};
    const gradeVolumes = {};
    
    // Initialize with zeros for all days
    days.forEach(day => {
      vesselVolumes[day] = 0;
      gradeVolumes[day] = {};
      Object.keys(gradeColors).forEach(grade => {
        gradeVolumes[day][grade] = 0;
      });
    });
    
    // Fill in the vessel arrival data
    scheduleData?.vessel_arrivals?.forEach(vessel => {
      const day = vessel.arrival_day.toString();
      
      if (!vesselVolumes[day]) {
        vesselVolumes[day] = 0;
      }
      
      vessel.cargo.forEach(cargo => {
        vesselVolumes[day] += cargo.volume;
        
        if (!gradeVolumes[day][cargo.grade]) {
          gradeVolumes[day][cargo.grade] = 0;
        }
        
        gradeVolumes[day][cargo.grade] += cargo.volume;
      });
    });
    
    // Create datasets for each grade
    const datasets = Object.keys(gradeColors).map(grade => {
      const data = days.map(day => gradeVolumes[day][grade] || 0);
      
      return {
        label: `Grade ${grade}`,
        data,
        backgroundColor: gradeColors[grade]
      };
    });
    
    return {
      labels: days.map(day => `Day ${day}`),
      datasets
    };
  };
  
  // Prepare tank inventory data (total volumes)
  const prepareTankInventoryData = () => {
    const datasets = tankNames.map(tankName => {
      const data = days.map(day => {
        if (!scheduleData?.daily_plan[day]?.tanks || !scheduleData?.daily_plan[day]?.tanks[tankName]) {
          return 0;
        }
        
        // Calculate total volume in this tank by summing all contents
        const tankContents = scheduleData.daily_plan[day].tanks[tankName].contents || [];
        const totalVolume = tankContents.reduce((sum, content) => sum + content.volume, 0);
        
        return totalVolume;
      });
      
      // Use generateTankColor to get the color
      const tankColor = generateTankColor(tankName);
      
      return {
        label: tankName,
        data,
        borderColor: tankColor.replace('0.7', '1'), 
        backgroundColor: tankColor,
        borderWidth: 2,
        tension: 0.3
      };
    });
    
    // Add capacity lines for each tank
    tankNames.forEach(tankName => {
      // Find the first day with data for this tank
      const firstDay = days.find(day => 
        scheduleData?.daily_plan[day]?.tanks && 
        scheduleData?.daily_plan[day]?.tanks[tankName]
      );
      
      if (firstDay && scheduleData.daily_plan[firstDay].tanks[tankName].capacity) {
        const capacity = scheduleData.daily_plan[firstDay].tanks[tankName].capacity;
        const tankColor = generateTankColor(tankName);
        
        datasets.push({
          label: `${tankName} Capacity`,
          data: days.map(() => capacity),
          borderColor: tankColor.replace('0.7', '0.3'),
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderDash: [5, 5],
          pointRadius: 0,
          tension: 0
        });
      }
    });
    
    return {
      labels: days.map(day => `Day ${day}`),
      datasets
    };
  };
  
  // Add this function to prepare stacked tank data showing grade composition
  const prepareTankGradeData = () => {
    // Get all grades
    const allGrades = Object.keys(gradeColors);
    
    // Create datasets for each grade within tanks
    const datasets = [];
    
    // Process each tank
    tankNames.forEach((tankName, tankIndex) => {
      // For each grade, create a dataset showing its volume in this tank
      allGrades.forEach(grade => {
        // Collect data for this grade in this tank across all days
        const data = days.map(day => {
          if (!scheduleData?.daily_plan[day]?.tanks || !scheduleData?.daily_plan[day]?.tanks[tankName]) {
            return 0;
          }
          
          // Find content with this grade
          const tankContents = scheduleData.daily_plan[day].tanks[tankName].contents || [];
          const gradeContent = tankContents.find(content => content.grade === grade);
          
          return gradeContent ? gradeContent.volume : 0;
        });
        
        // Only create dataset if this grade appears in this tank
        if (data.some(volume => volume > 0)) {
          datasets.push({
            label: `${tankName} - ${grade}`,
            data,
            backgroundColor: gradeColors[grade],
            borderColor: gradeColors[grade].replace('0.7', '1'),
            stack: tankName, // Stack by tank name so grades in same tank stack together
            order: tankIndex // Keep tanks in order
          });
        }
      });
      
      // Add capacity line for each tank
      const firstDay = days.find(day => 
        scheduleData?.daily_plan[day]?.tanks && 
        scheduleData?.daily_plan[day]?.tanks[tankName]
      );
      
      if (firstDay && scheduleData.daily_plan[firstDay].tanks[tankName].capacity) {
        const capacity = scheduleData.daily_plan[firstDay].tanks[tankName].capacity;
        
        // Use generateTankColor instead of tankColors
        const tankColor = generateTankColor(tankName);
        
        datasets.push({
          label: `${tankName} Capacity`,
          data: days.map(() => capacity),
          borderColor: tankColor.replace('0.7', '0.5'),
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 0,
          tension: 0,
          type: 'line',
          stack: 'capacity',
          order: 1
        });
      }
    });
    
    return {
      labels: days.map(day => `Day ${day}`),
      datasets
    };
  };
  
  // Options for processing rates chart
  const processingRatesOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Daily Processing Rates by Grade'
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Processing Rate'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Day'
        }
      }
    }
  };
  
  // Options for inventory chart
  const inventoryOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Daily Inventory by Grade'
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Volume'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Day'
        }
      }
    }
  };
  
  // Options for vessel arrivals chart
  const vesselOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Vessel Arrivals by Grade'
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Volume'
        },
        stacked: true
      },
      x: {
        title: {
          display: true,
          text: 'Day'
        },
        stacked: true
      }
    }
  };
  
  // Options for tank inventory chart
  const getMaxTankCapacity = () => {
    let maxCapacity = 300; // Default fallback
    
    // Find the maximum tank capacity
    tankNames.forEach(tankName => {
      for (const day of days) {
        const tankData = scheduleData?.daily_plan[day]?.tanks?.[tankName];
        if (tankData && tankData.capacity) {
          maxCapacity = Math.max(maxCapacity, tankData.capacity);
        }
      }
    });
    
    // Add 10% padding
    return Math.ceil(maxCapacity * 1.1);
  };

  // Calculate max capacity once
  const maxTankCapacity = getMaxTankCapacity();

  const tankInventoryOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Tank Inventory'
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        suggestedMax: maxTankCapacity, // Add this line
        title: {
          display: true,
          text: 'Volume'
        },
        stacked: false // Change to false if you don't want stacked values
      },
      x: {
        title: {
          display: true,
          text: 'Day'
        },
        stacked: false // Change to false if you don't want stacked values
      }
    }
  };
  
  // Options for tank grade visualization
  const tankGradeOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Tank Contents by Grade'
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
          }
        }
      },
      legend: {
        position: 'right',
        align: 'start',
        labels: {
          boxWidth: 12,
          usePointStyle: true
        }
      }
    },
    scales: {
      y: {
        stacked: true,
        beginAtZero: true,
        suggestedMax: maxTankCapacity, // Add this line
        title: {
          display: true,
          text: 'Volume'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Day'
        }
      }
    }
  };
  
  // Render the processing rates table
  const renderProcessingRatesTable = () => {
    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Day</th>
              {Object.keys(gradeColors).map(grade => (
                <th key={grade} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Grade {grade}
                </th>
              ))}
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {days.map(day => {
              const rates = scheduleData.daily_plan[day].processing_rates;
              const total = Object.values(rates).reduce((sum, rate) => sum + rate, 0);
              
              return (
                <tr key={day} className="hover:bg-gray-50">
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">Day {day}</td>
                  {Object.keys(gradeColors).map(grade => (
                    <td key={grade} className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                      {(rates[grade] || 0).toFixed(2)}
                    </td>
                  ))}
                  <td className="px-3 py-2 whitespace-nowrap text-sm font-bold text-gray-900">
                    {total.toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };
  
  // Render the inventory table
  const renderInventoryTable = () => {
    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Day</th>
              {Object.keys(gradeColors).map(grade => (
                <th key={grade} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Grade {grade}
                </th>
              ))}
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {days.map(day => {
              const inventory = scheduleData.daily_plan[day].inventory_by_grade;
              const total = scheduleData.daily_plan[day].inventory;
              
              return (
                <tr key={day} className="hover:bg-gray-50">
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">Day {day}</td>
                  {Object.keys(gradeColors).map(grade => (
                    <td key={grade} className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                      {(inventory[grade] || 0).toFixed(2)}
                    </td>
                  ))}
                  <td className="px-3 py-2 whitespace-nowrap text-sm font-bold text-gray-900">
                    {total.toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };
  
  // Render the vessel arrivals table
  const renderVesselArrivalsTable = () => {
    if (!scheduleData.vessel_arrivals || scheduleData.vessel_arrivals.length === 0) {
      return <div className="p-4">No vessel arrival data available</div>;
    }
    
    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Arrival Day</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Loading Date Range</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cargo</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Volume</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {scheduleData.vessel_arrivals.map((vessel, index) => {
              const totalVolume = vessel.cargo.reduce((sum, cargo) => sum + cargo.volume, 0);
              
              return (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">Day {vessel.arrival_day}</td>
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{vessel.ldr_text || 'N/A'}</td>
                  <td className="px-3 py-2 text-sm text-gray-900">
                    {vessel.cargo.map((cargo, i) => (
                      <div key={i}>
                        Grade {cargo.grade}: {cargo.volume.toFixed(2)} ({cargo.origin || 'Unknown'})
                      </div>
                    ))}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-sm font-bold text-gray-900">
                    {totalVolume.toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };
  
  // Also create a table view for tank grades
  const renderTankGradeTable = () => {
    if (!tankNames.length) {
      return <div className="p-4">No tank data available</div>;
    }
    
    // Get all grades
    const allGrades = Object.keys(gradeColors).filter(grade => {
      // Only include grades that appear in tanks
      return days.some(day => {
        if (!scheduleData?.daily_plan[day]?.tanks) return false;
        return Object.values(scheduleData.daily_plan[day].tanks).some(tank => {
          return (tank.contents || []).some(content => content.grade === grade);
        });
      });
    });
    
    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Day</th>
              {tankNames.map(tankName => (
                <th key={tankName} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {tankName}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {days.map(day => {
              return (
                <tr key={day} className="hover:bg-gray-50">
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">Day {day}</td>
                  {tankNames.map(tankName => {
                    const tankData = scheduleData?.daily_plan[day]?.tanks?.[tankName];
                    const contents = tankData?.contents || [];
                    const capacity = tankData?.capacity || 0;
                    
                    // Calculate total volume in this tank
                    const totalVolume = contents.reduce((sum, content) => sum + content.volume, 0);
                    
                    // Format the content display
                    const contentDisplay = contents.map(content => 
                      `${content.grade}: ${content.volume.toFixed(1)}`
                    ).join(', ');
                    
                    // Calculate fill percentage
                    const fillPercent = capacity > 0 ? Math.round((totalVolume / capacity) * 100) : 0;
                    
                    return (
                      <td key={tankName} className="px-3 py-2 text-sm text-gray-900">
                        <div className="flex flex-col">
                          {contentDisplay || 'Empty'}
                          {capacity > 0 && (
                            <div className="w-full bg-gray-200 rounded-full h-2.5 mt-1">
                              <div 
                                className={`h-2.5 rounded-full ${fillPercent > 90 ? 'bg-red-500' : 'bg-blue-500'}`}
                                style={{ width: `${fillPercent}%` }}
                              />
                            </div>
                          )}
                          <span className="text-xs text-gray-500">
                            {totalVolume.toFixed(1)} / {capacity} ({fillPercent}%)
                          </span>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };
  
  // Render the tank inventory table
  const renderTankInventoryTable = () => {
    if (!tankNames.length) {
      return <div className="p-4">No tank data available</div>;
    }
    
    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Day</th>
              {tankNames.map(tankName => (
                <th key={tankName} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {tankName}
                </th>
              ))}
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {days.map(day => {
              // Calculate total volume for each tank on this day
              const tankVolumes = {};
              let total = 0;
              
              tankNames.forEach(tankName => {
                if (!scheduleData.daily_plan[day]?.tanks || !scheduleData.daily_plan[day].tanks[tankName]) {
                  tankVolumes[tankName] = 0;
                  return;
                }
                
                const tankContents = scheduleData.daily_plan[day].tanks[tankName].contents || [];
                const tankVolume = tankContents.reduce((sum, content) => sum + content.volume, 0);
                tankVolumes[tankName] = tankVolume;
                total += tankVolume;
              });
              
              return (
                <tr key={day} className="hover:bg-gray-50">
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">Day {day}</td>
                  {tankNames.map(tankName => (
                    <td key={tankName} className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                      {tankVolumes[tankName].toFixed(2)}
                    </td>
                  ))}
                  <td className="px-3 py-2 whitespace-nowrap text-sm font-bold text-gray-900">
                    {total.toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };
  
  // Render the active chart based on the selected chart type
  const renderChart = () => {
    switch (chartType) {
      case 'processing':
        return <Line data={prepareProcessingRatesData()} options={processingRatesOptions} />;
      case 'inventory':
        return <Line data={prepareInventoryData()} options={inventoryOptions} />;
      case 'tanks':
        return <Line data={prepareTankInventoryData()} options={tankInventoryOptions} />;
      case 'tanks-by-grade':
        return <Bar data={prepareTankGradeData()} options={tankGradeOptions} />;
      case 'vessels':
        return <Bar data={prepareVesselArrivalsData()} options={vesselOptions} />;
      default:
        return <div>Select a chart type</div>;
    }
  };
  
  // Render the active table based on the selected chart type
  const renderTable = () => {
    switch (chartType) {
      case 'processing':
        return renderProcessingRatesTable();
      case 'inventory':
        return renderInventoryTable();
      case 'tanks':
        return renderTankInventoryTable();
      case 'tanks-by-grade':
        return renderTankGradeTable();
      case 'vessels':
        return renderVesselArrivalsTable();
      default:
        return <div>Select a table type</div>;
    }
  };

  return (
    <div className="p-4">
      {/* Controls */}
      <div className="flex flex-col space-y-4 sm:flex-row sm:justify-between sm:space-y-0 sm:space-x-4 items-end mb-6"> {/* Increased bottom margin */}
        <div>
          <p className="text-xs text-gray-500 mb-1">Display Type</p>
          <div className="inline-flex rounded-md shadow-md" role="group">
            {/* Chart/Table buttons */}
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium ${
                viewMode === 'chart' 
                  ? 'bg-blue-600 text-blue-700' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              } border border-gray-200 rounded-l-lg`}
              onClick={() => setViewMode('chart')}
            >
              Chart
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium ${
                viewMode === 'table' 
                  ? 'bg-blue-600 text-blue-700' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              } border border-gray-200 rounded-r-lg`}
              onClick={() => setViewMode('table')}
            >
              Table
            </button>
          </div>
        </div>
        
        <div>
          <p className="text-xs text-gray-500 mb-1">Data View</p>
          <div className="inline-flex rounded-md shadow-md" role="group">
            {/* Processing/Inventory/etc buttons */}
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium ${
                chartType === 'processing' 
                  ? 'bg-blue-600 text-blue-700' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              } border border-gray-200 rounded-l-lg`}
              onClick={() => setChartType('processing')}
            >
              Processing
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium ${
                chartType === 'inventory' 
                  ? 'bg-blue-600 text-blue-700' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              } border-t border-b border-gray-200`}
              onClick={() => setChartType('inventory')}
            >
              Inventory
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium ${
                chartType === 'tanks' 
                  ? 'bg-blue-600 text-blue-700' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              } border-t border-b border-gray-200`}
              onClick={() => setChartType('tanks')}
            >
              Tanks
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium ${
                chartType === 'tanks-by-grade' 
                  ? 'bg-blue-600 text-blue-700' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              } border-t border-b border-gray-200`}
              onClick={() => setChartType('tanks-by-grade')}
            >
              Tank Grades
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium ${
                chartType === 'vessels' 
                  ? 'bg-blue-600 text-blue-700' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              } border border-gray-200 rounded-r-lg`}
              onClick={() => setChartType('vessels')}
            >
              Vessels
            </button>
          </div>
        </div>
      </div>
      
      {/* Summary stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6"> {/* Increased gap from 2 to 4, and bottom margin from 4 to 6 */}
        <div className="bg-blue-50 p-3 rounded-lg shadow-sm"> {/* Reduced padding from p-4 to p-3, added shadow-sm */}
          <h3 className="text-sm font-medium text-blue-700 mb-1">Vessel Optimization</h3>
          <p className="text-xl font-bold">{scheduleData.vessel_optimization.vessel_count} vessels</p> {/* Reduced from text-2xl to text-xl */}
          <p className="text-xs text-blue-600">${scheduleData.vessel_optimization.freight_cost.toLocaleString()} freight cost</p> {/* Changed from text-sm to text-xs */}
        </div>
        <div className="bg-green-50 p-3 rounded-lg shadow-sm"> {/* Reduced padding from p-4 to p-3, added shadow-sm */}
          <h3 className="text-sm font-medium text-green-700 mb-1">Processing Rate</h3>
          <p className="text-xl font-bold"> {/* Reduced from text-2xl to text-xl */}
            {(() => {
              const rates = Object.values(scheduleData.daily_plan).map(day => 
                Object.values(day.processing_rates).reduce((sum, rate) => sum + rate, 0)
              );
              const avgRate = rates.reduce((sum, rate) => sum + rate, 0) / rates.length;
              return avgRate.toFixed(2);
            })()}
          </p>
          <p className="text-xs text-green-600">Average daily processing rate</p> {/* Changed from text-sm to text-xs */}
        </div>
        <div className="bg-purple-50 p-3 rounded-lg shadow-sm"> {/* Reduced padding from p-4 to p-3, added shadow-sm */}
          <h3 className="text-sm font-medium text-purple-700 mb-1">Total Days</h3>
          <p className="text-xl font-bold">{days.length}</p> {/* Reduced from text-2xl to text-xl */}
          <p className="text-xs text-purple-600">Days in schedule</p> {/* Changed from text-sm to text-xs */}
        </div>
      </div>
      
      {/* Chart or Table display */}
      <div className="bg-white border rounded-lg p-4" style={{ height: '500px' }}>
        <div className="w-full h-full overflow-auto">
          {viewMode === 'chart' ? renderChart() : renderTable()}
        </div>
      </div>
    </div>
  );
};

export default ScheduleVisualizer;