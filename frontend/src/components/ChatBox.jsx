import React, { useState, useRef, useEffect, useMemo } from 'react';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import MCPClient from './MCPClient';

const ChatBox = ({ scheduleData }) => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I can help you analyze the schedule data. What would you like to know?'
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  
  // Store indexed schedule data for retrieval
  const [indexedData, setIndexedData] = useState(null);
  
  // MCP servers configuration
  const mcpServers = {
    dayAnalyzer: {
      name: "Day Processing Analyzer",
      description: "Analyzes processing rates across days",
      capabilities: ["findLowestProcessingDay", "findHighestProcessingDay", "compareDays"]
    },
    vesselTracker: {
      name: "Vessel Tracker",
      description: "Tracks vessel arrivals and cargo contents",
      capabilities: ["getVesselSchedule", "getVesselCargo", "findVesselByDay"]
    },
    tankManager: {
      name: "Tank Inventory Manager",
      description: "Manages tank capacities and contents",
      capabilities: ["getTankCapacities", "getTankContents", "checkTankUtilization"]
    },
    gradeProcessor: {
      name: "Crude Grade Processor",
      description: "Analyzes crude grade processing",
      capabilities: ["getGradeVolumes", "compareGrades", "trackGradeByDay"]
    }
  };

  // Create indexed data from schedule data when component mounts or scheduleData changes
  useEffect(() => {
    if (scheduleData) {
      createIndexedData();
    }
  }, [scheduleData]);

  // Scroll to bottom of messages when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Create indexed data from schedule for RAG implementation
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

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Add user message to chat
    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      // Before first API call, ensure schedule data is sent to backend if needed
      if (scheduleData && !backendHasSchedule.current) {
        try {
          const setScheduleResponse = await fetch('http://localhost:5001/set-schedule', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(scheduleData)
          });
          
          if (setScheduleResponse.ok) {
            backendHasSchedule.current = true;
          }
        } catch (error) {
          console.error('Error setting schedule data:', error);
        }
      }

      // Try smart query endpoint first
      let response = await fetch('http://localhost:5001/smart-query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: input
        })
      });

      // If smart query fails, fall back to regular chat
      if (!response.ok) {
        const conversation = messages.map(msg => ({
          role: msg.role,
          content: msg.content
        }));
        conversation.push(userMessage);

        response = await fetch('http://localhost:5001/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            messages: conversation
          })
        });
      }

      if (!response.ok) {
        throw new Error('Failed to get response from API');
      }

      const data = await response.json();
      
      // Add assistant response to chat
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.response || 'I processed your request but couldn\'t generate a response.'
      }]);
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to get response from AI');
      
      // Add error message
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error while processing your request. Please try again later.',
        error: true
      }]);
    } finally {
      setIsTyping(false);
    }
  };
  
  // Properly create an MCPClient instance with the new class
  const mcpClient = useMemo(() => 
    new MCPClient({ 
      apiEndpoint: 'http://localhost:5001',
      onMessage: (message) => console.log('MCP Client:', message),
      onError: (error) => console.error('MCP Client Error:', error)
    }), 
  []);

  // Extract tool calls from the LLM response
  const extractToolCalls = (text) => {
    const calls = [];
    const regex = /CALL:\s*(\w+)\.(\w+)\(({.*?})\)/gs;
    let match;
    
    while ((match = regex.exec(text)) !== null) {
      try {
        const server = match[1];
        const capability = match[2];
        const paramsJson = match[3];
        const params = JSON.parse(paramsJson);
        
        calls.push({
          server,
          capability,
          params
        });
      } catch (e) {
        console.error('Error parsing tool call:', e);
      }
    }
    
    return calls;
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Add this at the beginning of your component
  const backendHasSchedule = useRef(false);

  // Add this effect to check if backend has schedule data
  useEffect(() => {
    const checkServerStatus = async () => {
      try {
        const response = await fetch('http://localhost:5001/status');
        if (response.ok) {
          const data = await response.json();
          backendHasSchedule.current = data.has_schedule_data;
        }
      } catch (error) {
        console.error('Error checking server status:', error);
      }
    };
    
    checkServerStatus();
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="bg-gray-100 p-4 border-b">
        <h2 className="text-lg font-semibold">Schedule Assistant</h2>
      </div>
      
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div 
            key={index} 
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'assistant' && (
              <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center text-white mr-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-6-3a2 2 0 11-4 0 2 2 0 014 0zm-2 4a5 5 0 00-4.546 2.916A5.986 5.986 0 005 10a6 6 0 0012 0c0-.352-.035-.696-.1-1.03A5 5 0 0010 11z" clipRule="evenodd" />
                </svg>
              </div>
            )}
            
            <div 
              className={`rounded-lg px-4 py-2 max-w-[75%] ${
                message.role === 'user' 
                  ? 'bg-blue-500 text-white' 
                  : message.error 
                    ? 'bg-red-100 text-red-800 border border-red-300' 
                    : 'bg-gray-100 text-gray-800 border border-gray-200'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            </div>
            
            {message.role === 'user' && (
              <div className="h-8 w-8 rounded-full bg-gray-600 flex items-center justify-center text-white ml-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                </svg>
              </div>
            )}
          </div>
        ))}
        
        {isTyping && (
          <div className="flex justify-start">
            <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center text-white mr-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-6-3a2 2 0 11-4 0 2 2 0 014 0zm-2 4a5 5 0 00-4.546 2.916A5.986 5.986 0 005 10a6 6 0 0012 0c0-.352-.035-.696-.1-1.03A5 5 0 0010 11z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="rounded-lg px-4 py-2 bg-gray-100 text-gray-800 border border-gray-200">
              <div className="flex space-x-1">
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce"></div>
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input area */}
      <div className="p-4 border-t">
        <div className="flex">
          <textarea
            className="flex-1 border rounded-l-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            rows="2"
            placeholder="Ask me about the schedule data..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          ></textarea>
          <button
            className={`px-4 rounded-r-md ${
              !input.trim() || isTyping
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
            onClick={handleSendMessage}
            disabled={!input.trim() || isTyping}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBox;