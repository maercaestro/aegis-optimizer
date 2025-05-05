import React, { useState, useRef, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import api from '../services/api';

const ChatBox = ({ scheduleData }) => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I can help you analyze the schedule data and suggest optimizations. You can ask me about vessels, tanks, processing rates, or say "optimize the schedule" to run the LP optimizer.'
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  
  // Store indexed schedule data for retrieval
  const [indexedData, setIndexedData] = useState(null);
  
  // Track if backend has received the schedule data
  const [backendHasSchedule, setBackendHasSchedule] = useState(false);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-scroll to bottom of chat when new messages arrive
  useEffect(() => {
    if (!chatContainerRef.current || !messagesEndRef.current) return;
    
    // Calculate if we should auto-scroll
    const container = chatContainerRef.current;
    const { scrollTop, scrollHeight, clientHeight } = container;
    
    // Only auto-scroll if user is already near the bottom (within 100px)
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    
    // Auto-scroll if the last message is from the AI or if user was already at bottom
    const lastMessage = messages[messages.length - 1];
    const shouldAutoScroll = 
      isNearBottom || 
      lastMessage?.role === 'assistant' || 
      messages.length <= 1;
      
    if (shouldAutoScroll) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Create indexed data from schedule data when component mounts or scheduleData changes
  useEffect(() => {
    if (scheduleData) {
      createIndexedData();
      sendScheduleDataToServer();
    }
  }, [scheduleData]);
  
  // Check if backend has schedule data
  useEffect(() => {
    const checkServerStatus = async () => {
      try {
        const response = await fetch('http://localhost:5001/status');
        if (response.ok) {
          const data = await response.json();
          setBackendHasSchedule(data.has_schedule_data);
        }
      } catch (error) {
        console.error('Error checking server status:', error);
      }
    };
    
    checkServerStatus();
    // Check periodically
    const interval = setInterval(checkServerStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // Send schedule data to server
  const sendScheduleDataToServer = async () => {
    if (!scheduleData) return;
    
    try {
      console.log('Sending schedule data to Flask API...');
      const response = await fetch('http://localhost:5001/upload-schedule', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(scheduleData)
      });
      
      if (!response.ok) {
        throw new Error(`Failed to upload schedule data: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Schedule data uploaded successfully:', result);
      toast.success('Schedule data uploaded to AI');
      setBackendHasSchedule(true);
    } catch (error) {
      console.error('Error uploading schedule data:', error);
      toast.error('Failed to upload schedule data to AI');
    }
  };

  // Create indexed data from schedule for RAG implementation (local fallback)
  const createIndexedData = () => {
    if (!scheduleData) return;
    
    try {
      // Create a structured index of the schedule data
      const index = {
        summary: createSummary(),
        vessels: indexVessels(),
        tanks: indexTanks(),
        grades: indexGrades(),
        dailyPlans: indexDailyPlans(),
        metrics: calculateMetrics()
      };
      
      setIndexedData(index);
    } catch (error) {
      console.error('Error creating indexed data:', error);
    }
  };
  
  // Create summary information
  const createSummary = () => {
    const days = Object.keys(scheduleData.daily_plan || {}).length;
    const vesselCount = scheduleData.vessel_optimization?.vessel_count || 0;
    const freightCost = scheduleData.vessel_optimization?.freight_cost || 0;
    
    return {
      days,
      vesselCount,
      freightCost,
      text: `Schedule spans ${days} days with ${vesselCount} vessels and $${freightCost.toLocaleString()} freight cost.`
    };
  };
  
  // Index vessel data
  const indexVessels = () => {
    const vessels = scheduleData.vessel_arrivals || [];
    return vessels.map(v => ({
      id: v.vessel_id,
      arrivalDay: v.arrival_day,
      cargo: v.cargo,
      text: `Vessel ${v.vessel_id} arrives on day ${v.arrival_day} carrying ${Object.keys(v.cargo || {}).join(', ')}.`
    }));
  };
  
  // Index tank data
  const indexTanks = () => {
    const tanks = {};
    
    Object.entries(scheduleData.daily_plan || {}).forEach(([day, data]) => {
      if (data.tanks) {
        Object.entries(data.tanks).forEach(([tankName, tankData]) => {
          if (!tanks[tankName]) {
            tanks[tankName] = {
              name: tankName,
              capacity: tankData.capacity,
              contentsByDay: {},
              text: `${tankName} has capacity of ${tankData.capacity}.`
            };
          }
          
          tanks[tankName].contentsByDay[day] = tankData.contents || [];
        });
      }
    });
    
    return Object.values(tanks);
  };
  
  // Index grade data
  const indexGrades = () => {
    const grades = {};
    
    Object.entries(scheduleData.daily_plan || {}).forEach(([day, data]) => {
      if (data.processing_rates) {
        Object.entries(data.processing_rates).forEach(([grade, rate]) => {
          if (!grades[grade]) {
            grades[grade] = {
              name: grade,
              ratesByDay: {},
              totalProcessed: 0,
              text: `${grade} is one of the crude grades processed in this schedule.`
            };
          }
          
          grades[grade].ratesByDay[day] = rate;
          grades[grade].totalProcessed += rate;
        });
      }
    });
    
    // Update text with total processed
    Object.values(grades).forEach(grade => {
      grade.text = `${grade.name} has total processing volume of ${grade.totalProcessed.toFixed(2)}.`;
    });
    
    return Object.values(grades);
  };
  
  // Index daily plans
  const indexDailyPlans = () => {
    return Object.entries(scheduleData.daily_plan || {}).map(([day, data]) => {
      const totalProcessing = data.processing_rates 
        ? Object.values(data.processing_rates).reduce((sum, rate) => sum + rate, 0) 
        : 0;
        
      return {
        day,
        processingRates: data.processing_rates || {},
        totalProcessing,
        tanks: data.tanks || {},
        text: `Day ${day} processes ${totalProcessing.toFixed(2)} total volume.`
      };
    });
  };
  
  // Calculate overall metrics
  const calculateMetrics = () => {
    // Average processing rate
    let totalProcessingRate = 0;
    let dayCount = 0;
    
    Object.values(scheduleData.daily_plan || {}).forEach(day => {
      if (day.processing_rates) {
        const dayTotal = Object.values(day.processing_rates).reduce((sum, rate) => sum + rate, 0);
        totalProcessingRate += dayTotal;
        dayCount++;
      }
    });
    
    const averageProcessingRate = dayCount > 0 ? totalProcessingRate / dayCount : 0;
    
    return {
      averageProcessingRate,
      text: `Average daily processing rate is ${averageProcessingRate.toFixed(2)}.`
    };
  };

  // Query the indexed data based on user's question
  const retrieveRelevantData = (query) => {
    if (!indexedData) return '';
    
    // Convert query to lowercase for case-insensitive matching
    const queryLower = query.toLowerCase();
    
    // Array to collect relevant pieces of information
    const relevantInfo = [];
    
    // Check for general schedule inquiries
    if (queryLower.includes('schedule') || queryLower.includes('overview') || queryLower.includes('summary')) {
      relevantInfo.push(indexedData.summary.text);
      relevantInfo.push(`Average daily processing rate: ${indexedData.metrics.averageProcessingRate.toFixed(2)}`);
    }
    
    // Check for vessel-related queries
    if (queryLower.includes('vessel') || queryLower.includes('ship') || queryLower.includes('arrival')) {
      indexedData.vessels.forEach(vessel => {
        relevantInfo.push(vessel.text);
      });
    }
    
    // Check for specific vessel inquiries by ID
    const vesselIdMatch = queryLower.match(/vessel\s+(\d+)/);
    if (vesselIdMatch) {
      const vesselId = vesselIdMatch[1];
      const vessel = indexedData.vessels.find(v => v.id.toString() === vesselId);
      if (vessel) {
        relevantInfo.push(vessel.text);
        relevantInfo.push(`Vessel ${vesselId} cargo details: ${JSON.stringify(vessel.cargo)}`);
      }
    }
    
    // Check for tank-related queries
    if (queryLower.includes('tank')) {
      // If asking about a specific tank
      const tankMatch = queryLower.match(/tank\s+(\d+|[a-z]+)/i);
      if (tankMatch) {
        const tankName = `Tank ${tankMatch[1]}`;
        const tank = indexedData.tanks.find(t => t.name.toLowerCase() === tankName.toLowerCase());
        if (tank) {
          relevantInfo.push(tank.text);
          relevantInfo.push(`${tankName} contains different crude grades on different days.`);
        }
      } else {
        // General tank info
        indexedData.tanks.forEach(tank => {
          relevantInfo.push(tank.text);
        });
      }
    }
    
    // Check for grade-related queries
    if (queryLower.includes('grade') || queryLower.includes('crude')) {
      indexedData.grades.forEach(grade => {
        relevantInfo.push(grade.text);
      });
      
      // Look for specific grade names in the query
      indexedData.grades.forEach(grade => {
        if (queryLower.includes(grade.name.toLowerCase())) {
          relevantInfo.push(`${grade.name} details: processed ${grade.totalProcessed.toFixed(2)} total volume.`);
        }
      });
    }
    
    // Check for day-specific queries
    const dayMatch = queryLower.match(/day\s+(\d+)/);
    if (dayMatch) {
      const day = dayMatch[1];
      const dayPlan = indexedData.dailyPlans.find(d => d.day === day);
      if (dayPlan) {
        relevantInfo.push(dayPlan.text);
        
        // Add processing rates for this day
        const rates = Object.entries(dayPlan.processingRates)
          .map(([grade, rate]) => `${grade}: ${rate.toFixed(2)}`)
          .join(', ');
        if (rates) {
          relevantInfo.push(`Day ${day} processing rates: ${rates}`);
        }
        
        // Add tank information for this day
        const tankInfo = Object.keys(dayPlan.tanks).join(', ');
        if (tankInfo) {
          relevantInfo.push(`Day ${day} active tanks: ${tankInfo}`);
        }
      }
    }
    
    // If we haven't found anything relevant yet, provide general information
    if (relevantInfo.length === 0) {
      relevantInfo.push(indexedData.summary.text);
      relevantInfo.push(`Average daily processing rate: ${indexedData.metrics.averageProcessingRate.toFixed(2)}`);
      relevantInfo.push(`Schedule includes ${indexedData.vessels.length} vessels.`);
      relevantInfo.push(`Schedule uses ${indexedData.tanks.length} tanks.`);
      relevantInfo.push(`Schedule processes ${indexedData.grades.length} different crude grades.`);
    }
    
    // Return concatenated relevant information
    return relevantInfo.join('\n\n');
  };

  // Execute MCP tool requests
  const executeMcpTool = (server, capability, params) => {
    console.log(`Executing ${capability} on ${server} with params:`, params);
    
    // Day Analyzer server functions
    if (server === 'dayAnalyzer') {
      if (capability === 'findLowestProcessingDay') {
        const dailyPlans = indexedData.dailyPlans;
        // Sort by processing rate ascending
        dailyPlans.sort((a, b) => a.totalProcessing - b.totalProcessing);
        const lowestDay = dailyPlans[0];
        
        return {
          day: lowestDay.day,
          processingRate: lowestDay.totalProcessing,
          breakdown: lowestDay.processingRates,
          result: `Day ${lowestDay.day} has the lowest processing rate at ${lowestDay.totalProcessing.toFixed(2)}.`
        };
      }
      
      if (capability === 'findHighestProcessingDay') {
        const dailyPlans = indexedData.dailyPlans;
        // Sort by processing rate descending
        dailyPlans.sort((a, b) => b.totalProcessing - a.totalProcessing);
        const highestDay = dailyPlans[0];
        
        return {
          day: highestDay.day,
          processingRate: highestDay.totalProcessing,
          breakdown: highestDay.processingRates,
          result: `Day ${highestDay.day} has the highest processing rate at ${highestDay.totalProcessing.toFixed(2)}.`
        };
      }
      
      if (capability === 'compareDays') {
        const { day1, day2 } = params;
        const dailyPlan1 = indexedData.dailyPlans.find(d => d.day === day1);
        const dailyPlan2 = indexedData.dailyPlans.find(d => d.day === day2);
        
        if (!dailyPlan1 || !dailyPlan2) {
          return { error: "One or both days not found" };
        }
        
        const difference = dailyPlan1.totalProcessing - dailyPlan2.totalProcessing;
        
        return {
          day1: {
            day: dailyPlan1.day,
            processing: dailyPlan1.totalProcessing
          },
          day2: {
            day: dailyPlan2.day,
            processing: dailyPlan2.totalProcessing
          },
          difference,
          result: `Day ${dailyPlan1.day} processes ${Math.abs(difference).toFixed(2)} ${difference > 0 ? 'more' : 'less'} than Day ${dailyPlan2.day}.`
        };
      }
    }
    
    // Vessel Tracker server functions
    if (server === 'vesselTracker') {
      if (capability === 'getVesselSchedule') {
        return {
          vessels: indexedData.vessels.map(v => ({
            id: v.id,
            arrivalDay: v.arrivalDay
          })),
          result: `Found ${indexedData.vessels.length} vessels in the schedule.`
        };
      }
      
      if (capability === 'getVesselCargo') {
        const { vesselId } = params;
        const vessel = indexedData.vessels.find(v => v.id.toString() === vesselId.toString());
        
        if (!vessel) {
          return { error: `Vessel ${vesselId} not found` };
        }
        
        return {
          vessel: vessel.id,
          cargo: vessel.cargo,
          result: `Vessel ${vessel.id} carries ${Object.keys(vessel.cargo).join(', ')}.`
        };
      }
    }
    
    // Implement other servers and capabilities...
    
    return { error: `Capability ${capability} not implemented for ${server}` };
  };

  // Handle sending messages - Updated to use Flask API with fallback
  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      // First try the Flask API with OpenAI function calling
      if (backendHasSchedule) {
        const apiResponse = await fetch('http://localhost:5001/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            messages: [...messages, userMessage]
          })
        });
        
        if (apiResponse.ok) {
          const result = await apiResponse.json();
          console.log('Received API response:', result);
          
          setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: result.response,
            source: 'api'
          }]);
          setIsTyping(false);
          return;
        } else {
          console.warn('API response not OK, falling back to local processing');
        }
      } else {
        console.log('Backend does not have schedule data, using local processing');
      }
      
      // Fallback to local RAG implementation
      if (indexedData) {
        const localResponse = retrieveRelevantData(input);
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: localResponse,
          source: 'local'
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: "I don't have any schedule data to analyze yet. Please make sure schedule data is loaded.",
          source: 'local',
          error: true
        }]);
      }
    } catch (error) {
      console.error('Error in chat:', error);
      
      // Try local fallback if API failed
      if (indexedData) {
        const localResponse = retrieveRelevantData(input);
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: `API error - falling back to local processing:\n\n${localResponse}`,
          source: 'local'
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${error.message}`,
          error: true
        }]);
      }
    } finally {
      setIsTyping(false);
    }
  };
  
  // Handle key press
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Render hints for optimization queries
  const renderHints = (message) => {
    if (message.role === 'user' && 
        message.content.toLowerCase().includes('optimize') && 
        !message.content.toLowerCase().includes('lp')) {
      return (
        <div className="text-xs text-gray-500 mt-1 italic">
          Tip: You can ask me to "optimize the schedule using LP" for advanced optimization
        </div>
      );
    }
    return null;
  };

  // Add this effect to handle scroll detection
  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;
    
    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      // Show button when scrolled up more than 200px from bottom
      const isScrolledUp = scrollHeight - scrollTop - clientHeight > 200;
      setShowScrollButton(isScrolledUp);
    };
    
    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  // Add this function to handle manual scrolling
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="flex flex-col h-full" style={{ minHeight: "80vh" }}>
      <div className="bg-gray-100 p-4 border-b flex justify-between items-center">
        <h2 className="text-lg font-semibold">Schedule Assistant</h2>
        <div>
          {backendHasSchedule ? (
            <span className="text-sm bg-green-100 text-green-800 py-1 px-2 rounded-full flex items-center">
              <span className="h-2 w-2 bg-green-500 rounded-full mr-1"></span>
              AI Connected
            </span>
          ) : (
            <span className="text-sm bg-yellow-100 text-yellow-800 py-1 px-2 rounded-full flex items-center">
              <span className="h-2 w-2 bg-yellow-500 rounded-full mr-1"></span>
              Local Mode
            </span>
          )}
        </div>
      </div>
      
      {/* Messages area */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 relative" 
        style={{ 
          height: "calc(100% - 60px)",  // Adjust based on your input area height
          overflowX: "hidden"  // Prevent horizontal scrolling
        }}
      >
        {messages.map((message, index) => (
          <div 
            key={index}
            className={`${
              message.role === 'user' ? 'ml-auto bg-blue-100' : 'mr-auto bg-gray-100'
            } rounded-lg p-3 max-w-[85%] break-words`}  // Add break-words to handle long text
          >
            <p className="text-sm">{message.content}</p>
          </div>
        ))}
        
        {/* Make sure the typing indicator has constraints */}
        {isTyping && (
          <div className="mr-auto bg-gray-100 rounded-lg p-3 max-w-[85%]">
            <div className="flex space-x-1">
              <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce"></div>
              <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce delay-75"></div>
              <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce delay-150"></div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
        
        {/* Scroll to bottom button */}
        {showScrollButton && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-5 right-5 rounded-full bg-blue-500 text-white p-2 shadow-lg hover:bg-blue-600 transition-all"
            aria-label="Scroll to bottom"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>
      
      {/* Input area */}
      <div className="flex items-center p-3 border-t border-gray-200 h-[60px]">
        {/* Fixed height input area */}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Ask me about the schedule..."
          className="flex-1 px-3 py-2 border rounded-l-lg focus:outline-none"
        />
        <button
          onClick={handleSendMessage}
          className="bg-blue-500 text-gray-700 px-4 py-2 rounded-r-lg hover:bg-blue-600 transition"
          disabled={isTyping || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatBox;