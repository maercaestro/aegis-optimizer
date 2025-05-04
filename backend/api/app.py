#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Flask API for the Aegis Refinery Optimizer with MCP implementation.
Exposes the optimization capabilities via HTTP endpoints.
"""
from datetime import datetime
import json
import os
from dotenv import load_dotenv
import logging


from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Global variable to store schedule data
current_schedule_data = None

# MCP server implementations
class MCPServer:
    """Base class for MCP servers"""
    def __init__(self, name, description, capabilities):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        
    def execute(self, capability, params, schedule_data):
        """Execute a capability with the given parameters"""
        if capability not in self.capabilities:
            return {"error": f"Capability {capability} not found in {self.name}"}
        
        method = getattr(self, capability, None)
        if not method:
            return {"error": f"Implementation for {capability} not found in {self.name}"}
        
        return method(params, schedule_data)
        
    def get_description(self):
        """Get server description for MCP prompt"""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": [c for c in self.capabilities]
        }

class DayProcessingAnalyzer(MCPServer):
    """Server for analyzing processing rates across days"""
    
    def __init__(self):
        super().__init__(
            "Day Processing Analyzer",
            "Analyzes processing rates across days",
            ["findLowestProcessingDay", "findHighestProcessingDay", "compareDays", "getAverageProcessingRates", "analyzeProcessingTrends"]
        )
    
    
    
    def findLowestProcessingDay(self, params, schedule_data):
        """Find the day with the lowest processing rate"""
        try:
            daily_plans = self._index_daily_plans(schedule_data)
            if not daily_plans:
                return {"error": "No daily plan data available"}
                
            # Sort by processing rate ascending
            daily_plans.sort(key=lambda x: x["totalProcessing"])
            lowest_day = daily_plans[0]
            
            return {
                "day": lowest_day["day"],
                "processingRate": lowest_day["totalProcessing"],
                "breakdown": lowest_day["processingRates"],
                "result": f"Day {lowest_day['day']} has the lowest processing rate at {lowest_day['totalProcessing']:.2f}."
            }
        except Exception as e:
            logger.error(f"Error in findLowestProcessingDay: {str(e)}")
            return {"error": str(e)}
    
    def _index_daily_plans(self, schedule_data):

        """Helper method to index daily plans"""
        if not schedule_data or "daily_plan" not in schedule_data:
            return []
            
        daily_plans = []
        for day, data in schedule_data.get("daily_plan", {}).items():
            processing_rates = data.get("processing_rates", {})
            total_processing = sum(processing_rates.values()) if processing_rates else 0
            
            daily_plans.append({
                "day": day,
                "processingRates": processing_rates,
                "totalProcessing": total_processing,
                "tanks": data.get("tanks", {}),
            })
            
        return daily_plans
    
    def findHighestProcessingDay(self, params, schedule_data):
        """Find the day with the highest processing rate"""
        try:
            daily_plans = self._index_daily_plans(schedule_data)
            if not daily_plans:
                return {"error": "No daily plan data available"}
                
            # Sort by processing rate descending
            daily_plans.sort(key=lambda x: x["totalProcessing"], reverse=True)
            highest_day = daily_plans[0]
            
            return {
                "day": highest_day["day"],
                "processingRate": highest_day["totalProcessing"],
                "breakdown": highest_day["processingRates"],
                "result": f"Day {highest_day['day']} has the highest processing rate at {highest_day['totalProcessing']:.2f}."
            }
        except Exception as e:
            logger.error(f"Error in findHighestProcessingDay: {str(e)}")
            return {"error": str(e)}
    
    def compareDays(self, params, schedule_data):
        """Compare processing rates between two days"""
        try:
            day1 = params.get("day1")
            day2 = params.get("day2")
            
            if not day1 or not day2:
                return {"error": "Missing day1 or day2 parameters"}
            
            daily_plans = self._index_daily_plans(schedule_data)
            daily_plan1 = next((d for d in daily_plans if d["day"] == day1), None)
            daily_plan2 = next((d for d in daily_plans if d["day"] == day2), None)
            
            if not daily_plan1 or not daily_plan2:
                return {"error": "One or both days not found"}
            
            difference = daily_plan1["totalProcessing"] - daily_plan2["totalProcessing"]
            
            return {
                "day1": {
                    "day": daily_plan1["day"],
                    "processing": daily_plan1["totalProcessing"]
                },
                "day2": {
                    "day": daily_plan2["day"],
                    "processing": daily_plan2["totalProcessing"]
                },
                "difference": difference,
                "result": f"Day {daily_plan1['day']} processes {abs(difference):.2f} {'more' if difference > 0 else 'less'} than Day {daily_plan2['day']}."
            }
        except Exception as e:
            logger.error(f"Error in compareDays: {str(e)}")
            return {"error": str(e)}
    
    def getAverageProcessingRates(self, params, schedule_data):
        """Calculate average processing rates by grade and overall"""
        try:
            # Add debugging
            print(f"Starting getAverageProcessingRates with params: {params}")
            print(f"Schedule data keys: {list(schedule_data.keys() if schedule_data else [])}")
            
            daily_plans = self._index_daily_plans(schedule_data)
            print(f"Got {len(daily_plans)} daily plans")
            
            if not daily_plans:
                print("No daily plan data available")
                return {"error": "No daily plan data available"}
            
            # Get all unique grades
            all_grades = set()
            for day_plan in daily_plans:
                print(f"Processing day {day_plan.get('day')}")
                all_grades.update(day_plan.get("processingRates", {}).keys())
            
            print(f"Found grades: {all_grades}")
            
            # Calculate averages by grade
            grade_totals = {grade: 0 for grade in all_grades}
            grade_counts = {grade: 0 for grade in all_grades}
            
            for day_plan in daily_plans:
                for grade, rate in day_plan.get("processingRates", {}).items():
                    if rate > 0:  # Only count days where the grade was processed
                        grade_totals[grade] += rate
                        grade_counts[grade] += 1
            
            # Calculate the averages
            grade_averages = {}
            for grade in all_grades:
                if grade_counts[grade] > 0:
                    grade_averages[grade] = grade_totals[grade] / grade_counts[grade]
                else:
                    grade_averages[grade] = 0
            
            # Calculate overall average
            overall_total = sum(day_plan.get("totalProcessing", 0) for day_plan in daily_plans)
            overall_average = overall_total / len(daily_plans) if daily_plans else 0
            
            print(f"Calculated overall average: {overall_average}")
            print(f"Grade averages: {grade_averages}")
            
            return {
                "overallAverage": overall_average,
                "gradeAverages": grade_averages,
                "totalDays": len(daily_plans),
                "result": f"Overall average processing rate is {overall_average:.2f} across {len(daily_plans)} days. Grade averages: {', '.join([f'{g}: {grade_averages[g]:.2f}' for g in grade_averages])}"
            }
        except Exception as e:
            print(f"ERROR in getAverageProcessingRates: {str(e)}")
            logger.error(f"Error in getAverageProcessingRates: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def analyzeProcessingTrends(self, params, schedule_data):
        """Analyze trends in processing rates over time"""
        try:
            daily_plans = self._index_daily_plans(schedule_data)
            if not daily_plans:
                return {"error": "No daily plan data available"}
            
            # Sort by day
            daily_plans.sort(key=lambda x: int(x["day"]))
            
            # Get processing trend
            trend_data = {
                "days": [plan["day"] for plan in daily_plans],
                "rates": [plan["totalProcessing"] for plan in daily_plans]
            }
            
            # Calculate trend statistics
            avg_rate = sum(trend_data["rates"]) / len(trend_data["rates"]) if trend_data["rates"] else 0
            
            # Find periods of increase or decrease
            changes = []
            for i in range(1, len(trend_data["days"])):
                prev_rate = trend_data["rates"][i-1]
                curr_rate = trend_data["rates"][i]
                if curr_rate > prev_rate:
                    changes.append(f"Increase from day {trend_data['days'][i-1]} to {trend_data['days'][i]} by {curr_rate - prev_rate:.2f}")
                elif curr_rate < prev_rate:
                    changes.append(f"Decrease from day {trend_data['days'][i-1]} to {trend_data['days'][i]} by {prev_rate - curr_rate:.2f}")
            
            # Find most stable and most volatile periods
            if len(trend_data["rates"]) >= 3:
                volatility = []
                for i in range(1, len(trend_data["rates"])-1):
                    vol = abs(trend_data["rates"][i+1] - trend_data["rates"][i]) + abs(trend_data["rates"][i] - trend_data["rates"][i-1])
                    volatility.append((trend_data["days"][i], vol))
                
                volatility.sort(key=lambda x: x[1])
                most_stable = volatility[0][0]
                most_volatile = volatility[-1][0]
            else:
                most_stable = "insufficient data"
                most_volatile = "insufficient data"
            
            return {
                "trendData": trend_data,
                "averageRate": avg_rate,
                "significantChanges": changes[:3] if len(changes) > 3 else changes,
                "mostStableDay": most_stable,
                "mostVolatileDay": most_volatile,
                "result": f"Average processing rate over time is {avg_rate:.2f}. Notable changes include: {'; '.join(changes[:2] if len(changes) > 2 else changes)}."
            }
        except Exception as e:
            logger.error(f"Error in analyzeProcessingTrends: {str(e)}")
            return {"error": str(e)}

class VesselTracker(MCPServer):
    """Server for tracking vessels and their cargo"""
    
    def __init__(self):
        super().__init__(
            "Vessel Tracker",
            "Tracks vessel arrivals and cargo contents",
            ["getVesselSchedule", "getVesselCargo", "findVesselByDay"]
        )
    
    def getVesselSchedule(self, params, schedule_data):
        """Get the schedule of all vessels"""
        try:
            vessels = schedule_data.get("vessel_arrivals", [])
            return {
                "vessels": [{"id": v["vessel_id"], "arrivalDay": v["arrival_day"]} for v in vessels],
                "result": f"Found {len(vessels)} vessels in the schedule."
            }
        except Exception as e:
            logger.error(f"Error in getVesselSchedule: {str(e)}")
            return {"error": str(e)}
    
    def getVesselCargo(self, params, schedule_data):
        """Get cargo details for a specific vessel"""
        try:
            vessel_id = params.get("vesselId")
            if not vessel_id:
                return {"error": "Missing vesselId parameter"}
                
            vessels = schedule_data.get("vessel_arrivals", [])
            vessel = next((v for v in vessels if str(v["vessel_id"]) == str(vessel_id)), None)
            
            if not vessel:
                return {"error": f"Vessel {vessel_id} not found"}
            
            return {
                "vessel": vessel["vessel_id"],
                "cargo": vessel.get("cargo", {}),
                "result": f"Vessel {vessel['vessel_id']} carries {', '.join(vessel.get('cargo', {}).keys())}."
            }
        except Exception as e:
            logger.error(f"Error in getVesselCargo: {str(e)}")
            return {"error": str(e)}
    
    def findVesselByDay(self, params, schedule_data):
        """Find vessels arriving on a specific day"""
        try:
            day = params.get("day")
            if not day:
                return {"error": "Missing day parameter"}
                
            vessels = schedule_data.get("vessel_arrivals", [])
            matching_vessels = [v for v in vessels if str(v["arrival_day"]) == str(day)]
            
            return {
                "day": day,
                "vessels": [{"id": v["vessel_id"], "cargo": v.get("cargo", {})} for v in matching_vessels],
                "result": f"Found {len(matching_vessels)} vessels arriving on day {day}."
            }
        except Exception as e:
            logger.error(f"Error in findVesselByDay: {str(e)}")
            return {"error": str(e)}

class TankInventoryManager(MCPServer):
    """Server for managing tank inventory"""
    
    def __init__(self):
        super().__init__(
            "Tank Inventory Manager", 
            "Manages tank capacities and contents",
            ["getTankCapacities", "getTankContents", "checkTankUtilization"]
        )
    
    def getTankCapacities(self, params, schedule_data):
        """Get capacities for all tanks"""
        try:
            # We need to extract tank capacities from the daily plan
            tanks = {}
            for day, data in schedule_data.get("daily_plan", {}).items():
                if "tanks" in data:
                    for tank_name, tank_data in data["tanks"].items():
                        if tank_name not in tanks and "capacity" in tank_data:
                            tanks[tank_name] = tank_data["capacity"]
            
            return {
                "tanks": [{"name": name, "capacity": capacity} for name, capacity in tanks.items()],
                "result": f"Found {len(tanks)} tanks with their capacities."
            }
        except Exception as e:
            logger.error(f"Error in getTankCapacities: {str(e)}")
            return {"error": str(e)}
    
    def getTankContents(self, params, schedule_data):
        """Get contents of a specific tank on a specific day"""
        try:
            tank_name = params.get("tankName")
            day = params.get("day")
            
            if not tank_name or not day:
                return {"error": "Missing tankName or day parameter"}
                
            daily_plan = schedule_data.get("daily_plan", {}).get(str(day), {})
            tank_data = daily_plan.get("tanks", {}).get(tank_name, {})
            
            if not tank_data:
                return {"error": f"Tank {tank_name} not found on day {day}"}
            
            return {
                "tank": tank_name,
                "day": day,
                "capacity": tank_data.get("capacity", 0),
                "contents": tank_data.get("contents", []),
                "result": f"Tank {tank_name} on day {day} contains {', '.join(tank_data.get('contents', []))}."
            }
        except Exception as e:
            logger.error(f"Error in getTankContents: {str(e)}")
            return {"error": str(e)}
    
    def checkTankUtilization(self, params, schedule_data):
        """Check utilization of tanks across the schedule"""
        try:
            # Get tank capacities first
            tank_capacities = {}
            for day, data in schedule_data.get("daily_plan", {}).items():
                if "tanks" in data:
                    for tank_name, tank_data in data["tanks"].items():
                        if tank_name not in tank_capacities and "capacity" in tank_data:
                            tank_capacities[tank_name] = tank_data["capacity"]
            
            # Track tank utilization by day
            utilization = {}
            for day, data in schedule_data.get("daily_plan", {}).items():
                if "tanks" in data:
                    for tank_name, tank_data in data["tanks"].items():
                        if "contents" not in tank_data:
                            continue
                            
                        contents = tank_data.get("contents", [])
                        utilized = len(contents) > 0
                        
                        if tank_name not in utilization:
                            utilization[tank_name] = {"total_days": 0, "utilized_days": 0}
                        
                        utilization[tank_name]["total_days"] += 1
                        if utilized:
                            utilization[tank_name]["utilized_days"] += 1
            
            # Calculate utilization percentages
            for tank_name in utilization:
                total = utilization[tank_name]["total_days"]
                used = utilization[tank_name]["utilized_days"]
                utilization[tank_name]["utilization_rate"] = (used / total) * 100 if total > 0 else 0
            
            return {
                "utilization": utilization,
                "result": f"Analyzed utilization for {len(utilization)} tanks across the schedule."
            }
        except Exception as e:
            logger.error(f"Error in checkTankUtilization: {str(e)}")
            return {"error": str(e)}

class CrudeGradeProcessor(MCPServer):
    """Server for analyzing crude grade processing"""
    
    def __init__(self):
        super().__init__(
            "Crude Grade Processor",
            "Analyzes crude grade processing",
            ["getGradeVolumes", "compareGrades", "trackGradeByDay"]
        )
    
    def getGradeVolumes(self, params, schedule_data):
        """Get total volumes for all grades"""
        try:
            grades = {}
            
            for day, data in schedule_data.get("daily_plan", {}).items():
                if "processing_rates" in data:
                    for grade, rate in data["processing_rates"].items():
                        if grade not in grades:
                            grades[grade] = {"name": grade, "totalProcessed": 0}
                        
                        grades[grade]["totalProcessed"] += rate
            
            return {
                "grades": [{"name": grade_data["name"], "totalProcessed": grade_data["totalProcessed"]} 
                        for grade_data in grades.values()],
                "result": f"Processed {len(grades)} different crude grades."
            }
        except Exception as e:
            logger.error(f"Error in getGradeVolumes: {str(e)}")
            return {"error": str(e)}
    
    def compareGrades(self, params, schedule_data):
        """Compare processing volumes between two grades"""
        try:
            grade1 = params.get("grade1")
            grade2 = params.get("grade2")
            
            if not grade1 or not grade2:
                return {"error": "Missing grade1 or grade2 parameter"}
            
            # Calculate total processing for each grade
            grades = {}
            
            for day, data in schedule_data.get("daily_plan", {}).items():
                if "processing_rates" in data:
                    for grade, rate in data["processing_rates"].items():
                        if grade not in grades:
                            grades[grade] = {"name": grade, "totalProcessed": 0}
                        
                        grades[grade]["totalProcessed"] += rate
            
            if grade1 not in grades:
                return {"error": f"Grade {grade1} not found in schedule"}
            
            if grade2 not in grades:
                return {"error": f"Grade {grade2} not found in schedule"}
                
            vol1 = grades[grade1]["totalProcessed"]
            vol2 = grades[grade2]["totalProcessed"] 
            difference = vol1 - vol2
            
            return {
                "grade1": {
                    "name": grade1,
                    "totalProcessed": vol1
                },
                "grade2": {
                    "name": grade2,
                    "totalProcessed": vol2
                },
                "difference": difference,
                "result": f"{grade1} is processed {abs(difference):.2f} {'more' if difference > 0 else 'less'} than {grade2}."
            }
        except Exception as e:
            logger.error(f"Error in compareGrades: {str(e)}")
            return {"error": str(e)}
    
    def trackGradeByDay(self, params, schedule_data):
        """Track processing of a specific grade across days"""
        try:
            grade = params.get("grade")
            
            if not grade:
                return {"error": "Missing grade parameter"}
            
            # Track processing by day
            processing_by_day = {}
            
            for day, data in schedule_data.get("daily_plan", {}).items():
                if "processing_rates" in data and grade in data["processing_rates"]:
                    processing_by_day[day] = data["processing_rates"][grade]
            
            if not processing_by_day:
                return {"error": f"Grade {grade} not found in schedule"}
                
            # Calculate stats
            days_processed = len(processing_by_day)
            total_processed = sum(processing_by_day.values())
            avg_rate = total_processed / days_processed if days_processed > 0 else 0
            
            return {
                "grade": grade,
                "processingByDay": processing_by_day,
                "daysProcessed": days_processed,
                "totalProcessed": total_processed,
                "averageRate": avg_rate,
                "result": f"{grade} was processed on {days_processed} days with average rate of {avg_rate:.2f}."
            }
        except Exception as e:
            logger.error(f"Error in trackGradeByDay: {str(e)}")
            return {"error": str(e)}

# Initialize MCP servers
mcp_servers = {
    "dayAnalyzer": DayProcessingAnalyzer(),
    "vesselTracker": VesselTracker(),
    "tankManager": TankInventoryManager(),
    "gradeProcessor": CrudeGradeProcessor()
}

def generate_mcp_prompt():
    """Generate the MCP system prompt"""
    servers_description = []
    
    for server_id, server in mcp_servers.items():
        desc = server.get_description()
        servers_description.append(
            f"- {desc['name']} ({server_id}): {desc['description']}\n"
            f"  Capabilities: {', '.join(desc['capabilities'])}"
        )
    
    # Join the descriptions first, then use in the f-string
    joined_descriptions = "\n".join(servers_description)
    
    return f"""You're an AI assistant using the Model Context Protocol (MCP) to analyze refinery schedule data.

AVAILABLE MCP SERVERS:
{joined_descriptions}

PROCESS:
1. Understand what the user is asking about the schedule data
2. Determine which MCP server and capability to use
3. Call the appropriate capability with parameters
4. Format response based on the returned data

IMPORTANT: Be flexible in your approach. If a question doesn't exactly match a capability:
- Think about which capability would give the most relevant information
- Use multiple capabilities if needed to provide a complete answer
- Be creative in combining data from different sources

To call a capability, use this format in your thinking:
CALL: server_id.capability_name({{"param1": "value1", "param2": "value2"}})

Example for finding the lowest processing day:
CALL: dayAnalyzer.findLowestProcessingDay({{}})

First analyze the question, then use the appropriate server and capability."""

def extract_tool_calls(text):
    """Extract tool calls from the LLM response"""
    import re
    calls = []
    pattern = r'CALL:\s*(\w+)\.(\w+)\(({.*?})\)'
    
    matches = re.findall(pattern, text, re.DOTALL)
    for match in matches:
        try:
            server = match[0]
            capability = match[1]
            params_json = match[2]
            params = json.loads(params_json)
            
            calls.append({
                "server": server,
                "capability": capability,
                "params": params
            })
        except Exception as e:
            logger.error(f"Error parsing tool call: {str(e)}")
    
    return calls

def execute_tool_calls(calls, schedule_data):
    """Execute a list of tool calls against the servers"""
    results = []
    print(f"Executing {len(calls)} tool calls")
    
    for call in calls:
        try:
            server_id = call["server"]
            capability = call["capability"]
            params = call["params"]
            
            print(f"Executing {server_id}.{capability}({params})")
            
            if server_id not in mcp_servers:
                error_msg = f"Server {server_id} not found"
                print(f"ERROR: {error_msg}")
                results.append({
                    "call": call,
                    "error": error_msg,
                    "success": False
                })
                continue
            
            server = mcp_servers[server_id]
            if capability not in server.capabilities:
                error_msg = f"Capability {capability} not found in {server_id}"
                print(f"ERROR: {error_msg}")
                results.append({
                    "call": call,
                    "error": error_msg,
                    "success": False
                })
                continue
            
            # Execute the capability
            print(f"Server and capability found, executing...")
            result = server.execute(capability, params, schedule_data)
            print(f"Execution result keys: {list(result.keys() if result else [])}")
            
            if "error" in result:
                print(f"ERROR returned from capability: {result['error']}")
                results.append({
                    "call": call,
                    "error": result["error"],
                    "success": False
                })
            else:
                print(f"SUCCESS: {server_id}.{capability} executed successfully")
                results.append({
                    "call": call,
                    "result": result,
                    "success": True
                })
        except Exception as e:
            print(f"EXCEPTION executing {call}: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                "call": call,
                "error": str(e),
                "success": False
            })
    
    return results

def format_tool_results(tool_results):
    """Format tool results for the second prompt"""
    formatted_results = []
    
    for tr in tool_results:
        result_text = f"TOOL RESULT: {tr['call']['server']}.{tr['call']['capability']}\n"
        result_text += f"Success: {tr['success']}\n"
        
        if tr['success']:
            result_text += f"Result: {json.dumps(tr['result'], indent=2)}"
        else:
            result_text += f"Error: {tr['error']}"
            
        formatted_results.append(result_text)
    
    return "\n\n".join(formatted_results)

@app.route('/chat', methods=['POST'])
def chat():
    """MCP-compliant chat endpoint"""
    global current_schedule_data
    try:
        # Add schedule data validation
        if not current_schedule_data:
            print("WARNING: No schedule data available")
        else:
            print(f"Schedule data keys: {list(current_schedule_data.keys())}")
        
        data = request.json
        messages = data.get('messages', [])
        
        # Get the user's last message
        if not messages or messages[-1]['role'] != 'user':
            return jsonify({"error": "No user message found"}), 400
            
        user_query = messages[-1]['content']
        
        # STEP 1: Planning phase (internal only, not shown to user)
        # This follows the JSON-RPC format from MCP schema
        planning_request = {
            "jsonrpc": "2.0",
            "id": f"plan-{datetime.now().timestamp()}",
            "method": "internal/planning",
            "params": {
                "query": user_query,
                "_meta": {
                    "source": "user_chat"
                }
            }
        }
        
        # Generate the MCP system prompt
        system_prompt = generate_mcp_prompt()
        
        # Create the planning messages
        planning_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question: {user_query}\n\nAnalyze this question and determine which MCP tools to use. Follow the MCP protocol strictly."}
        ]
        
        # Call OpenAI API for tool planning
        try:
            plan_response = client.chat.completions.create(
                model="gpt-4o",
                messages=planning_messages,
                temperature=0.5,
                max_tokens=1000
            )
            
            plan_text = plan_response.choices[0].message.content
            
            # Extract tool calls from the plan (internal use only)
            tool_calls = extract_tool_calls(plan_text)
            
            if not tool_calls:
                # No tool calls found, return a direct response
                response_messages = [
                    {"role": "system", "content": "You are a helpful assistant. Answer the user's question directly."},
                    {"role": "user", "content": user_query}
                ]
                
                direct_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=response_messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                return jsonify({
                    "response": direct_response.choices[0].message.content
                })
            
            # STEP 2: Tool execution (internal)
            # Format following MCP CallToolRequest
            tool_results = []
            for call in tool_calls:
                mcp_tool_request = {
                    "method": "tools/call",
                    "params": {
                        "name": f"{call['server']}.{call['capability']}",
                        "arguments": call['params']
                    }
                }
                
                # Execute the tool call
                if call['server'] in mcp_servers:
                    server = mcp_servers[call['server']]
                    if call['capability'] in server.capabilities:
                        result = server.execute(call['capability'], call['params'], current_schedule_data)
                        
                        # Format according to MCP CallToolResult
                        tool_result = {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }],
                            "isError": "error" in result
                        }
                        
                        tool_results.append({
                            "call": mcp_tool_request,
                            "result": tool_result
                        })
            
            # STEP 3: Response generation (shown to user)
            # Format tool results for consumption
            formatted_results = ""
            for tr in tool_results:
                if not tr["result"]["isError"]:
                    formatted_results += f"Tool {tr['call']['params']['name']} returned:\n"
                    try:
                        # Get the text content
                        content_text = tr["result"]["content"][0]["text"]
                        result_obj = json.loads(content_text)
                        if "result" in result_obj:
                            formatted_results += f"{result_obj['result']}\n\n"
                        else:
                            formatted_results += f"{content_text}\n\n"
                    except:
                        formatted_results += f"{tr['result']['content'][0]['text']}\n\n"
            
            # Generate final response WITHOUT showing the planning
            response_messages = [
                {"role": "system", "content": "You're a helpful assistant that explains refinery scheduling data. IMPORTANT: Respond DIRECTLY to the user's question using the provided data WITHOUT mentioning the tools used or any internal reasoning processes. Do not refer to any tools, analyzers, or the MCP protocol in your response. Present the information as if you analyzed the data directly."},
                {"role": "user", "content": f"Question: {user_query}\n\nData: {formatted_results}\n\nProvide a direct, natural-sounding answer."}
            ]
            
            final_response = client.chat.completions.create(
                model="gpt-4o",
                messages=response_messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return jsonify({
                "response": final_response.choices[0].message.content
            })
            
        except Exception as e:
            logger.error(f"Error in MCP chat flow: {str(e)}")
            return jsonify({"error": f"Error processing request: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/upload-schedule', methods=['POST'])
def upload_schedule():
    """Upload a schedule JSON file"""
    global current_schedule_data  # Add this line at the beginning
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
            
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
            
        if file and file.filename.endswith('.json'):
            # Parse JSON data
            schedule_data = json.loads(file.read())
            
            # Store in global variable
            current_schedule_data = schedule_data
            
            return jsonify({"message": "Schedule data uploaded successfully"})
        else:
            return jsonify({"error": "Invalid file format. Please upload a JSON file"}), 400
    
    except Exception as e:
        logger.error(f"Error uploading schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/set-schedule', methods=['POST'])
def set_schedule():
    """Set schedule data directly from JSON"""
    global current_schedule_data  # Add this line at the beginning
    try:
        schedule_data = request.json
        
        if not schedule_data:
            return jsonify({"error": "No schedule data provided"}), 400
        
        # Store in global variable
        current_schedule_data = schedule_data
        
        return jsonify({"message": "Schedule data set successfully"})
    
    except Exception as e:
        logger.error(f"Error setting schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/schedule/<filename>', methods=['GET'])
def get_schedule(filename):
    """Retrieve schedule data by filename"""
    global current_schedule_data  # Only declare once at beginning
    try:
        # Check if the filename is specified
        if not filename:
            return jsonify({"error": "Filename not specified"}), 400
        
        # If we're being asked for the latest schedule and we have data in memory, return it
        if filename == 'latest_schedule_output.json' and current_schedule_data:
            return jsonify(current_schedule_data)
            
        # Otherwise look for the file in the results directory
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'results')
        
        # Create the data directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        file_path = os.path.join(data_dir, secure_filename(filename))
        
        # Check if the file exists
        if not os.path.exists(file_path):
            # If not found and we have current data in memory, return that
            if current_schedule_data:
                return jsonify(current_schedule_data)
            return jsonify({"error": f"Schedule file {filename} not found"}), 404
        
        # Read the file
        with open(file_path, 'r') as f:
            schedule_data = json.load(f)
            
        # Update the current_schedule_data
        current_schedule_data = schedule_data
            
        return jsonify(schedule_data)
    except Exception as e:
        logger.error(f"Error retrieving schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/results/<filename>', methods=['GET'])
def get_results_file(filename):
    """Retrieve schedule data by filename from the results directory"""
    global current_schedule_data
    try:
        # Check if the filename is specified
        if not filename:
            return jsonify({"error": "Filename not specified"}), 400
        
        # If we're being asked for the latest schedule and we have data in memory, return it
        if filename == 'latest_schedule_output.json' and current_schedule_data:
            return jsonify(current_schedule_data)
            
        # Look for the file in the results directory
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'results')
        
        # Create the data directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        file_path = os.path.join(data_dir, secure_filename(filename))
        
        # Check if the file exists
        if not os.path.exists(file_path):
            # If not found and we have current data in memory, return that
            if current_schedule_data:
                return jsonify(current_schedule_data)
            return jsonify({"error": f"Schedule file {filename} not found"}), 404
        
        # Read the file
        with open(file_path, 'r') as f:
            schedule_data = json.load(f)
            
        # Update the current_schedule_data
        current_schedule_data = schedule_data
            
        return jsonify(schedule_data)
    except Exception as e:
        logger.error(f"Error retrieving schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """Simple endpoint to check if API is running"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "has_schedule_data": current_schedule_data is not None
    })

# Add this new endpoint for more flexible queries

@app.route('/smart-query', methods=['POST'])
def smart_query():
    """More flexible query endpoint that tries to match user questions to capabilities"""
    global current_schedule_data
    try:
        data = request.json
        query = data.get('query', '')
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
            
        if not current_schedule_data:
            return jsonify({"error": "No schedule data available"}), 400
        
        # Use OpenAI to decide which capability to call
        system_prompt = """You are a query router for a refinery scheduling system. 
Given a user query, determine the most appropriate API call from the following options:

1. dayAnalyzer.findLowestProcessingDay({}) - Find the day with lowest processing
2. dayAnalyzer.findHighestProcessingDay({}) - Find the day with highest processing
3. dayAnalyzer.compareDays({"day1": "1", "day2": "2"}) - Compare two specific days
4. dayAnalyzer.getAverageProcessingRates({}) - Get average processing rates by grade and overall
5. dayAnalyzer.analyzeProcessingTrends({}) - Analyze trends in processing over time
6. vesselTracker.getVesselSchedule({}) - Get all vessel schedules
7. vesselTracker.getVesselCargo({"vesselId": "1"}) - Get cargo for a specific vessel
8. vesselTracker.findVesselByDay({"day": "1"}) - Find vessels arriving on a specific day
9. tankManager.getTankCapacities({}) - Get all tank capacities
10. tankManager.getTankContents({"tankName": "Tank1", "day": "1"}) - Get contents of a specific tank
11. tankManager.checkTankUtilization({}) - Check utilization of tanks across schedule
12. gradeProcessor.getGradeVolumes({}) - Get total volumes for all grades
13. gradeProcessor.compareGrades({"grade1": "A", "grade2": "B"}) - Compare two grades
14. gradeProcessor.trackGradeByDay({"grade": "A"}) - Track processing of a specific grade by day

Return just the API call as JSON without any explanation."""

        try:
            router_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=150
            )
            
            router_text = router_response.choices[0].message.content
            router_decision = json.loads(router_text)
            
            # Extract server, capability and params
            for key, value in router_decision.items():
                if "." in key:
                    server_id, capability = key.split(".")
                    params = value
                    
                    if server_id not in mcp_servers:
                        return jsonify({"error": f"Server {server_id} not found"}), 400
                    
                    server = mcp_servers[server_id]
                    if capability not in server.capabilities:
                        return jsonify({"error": f"Capability {capability} not found in {server_id}"}), 400
                    
                    # Execute the capability
                    result = server.execute(capability, params, current_schedule_data)
                    
                    # Generate a natural language response
                    if "error" in result:
                        return jsonify({"error": result["error"]}), 400
                    
                    nlg_response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that explains refinery scheduling data. Use a conversational, helpful tone."},
                            {"role": "user", "content": f"Original query: {query}\nData result: {json.dumps(result, indent=2)}\n\nCreate a natural-sounding response that answers the query using this data."}
                        ],
                        temperature=0.7,
                        max_tokens=400
                    )
                    
                    return jsonify({
                        "response": nlg_response.choices[0].message.content,
                        "data": result,
                        "meta": {
                            "server": server_id,
                            "capability": capability,
                            "params": params
                        }
                    })
        
        except Exception as e:
            logger.error(f"Error in router: {str(e)}")
            # Fall back to the regular chat endpoint
            pass
        
        # If we get here, the router failed or couldn't decide
        # Create a proper internal call instead of directly calling chat()
        messages = [{"role": "user", "content": query}]
        system_prompt = generate_mcp_prompt()

        formatted_messages = [
            {"role": "system", "content": system_prompt}
        ]
        formatted_messages.extend(messages)

        # Call OpenAI API with these messages instead
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return jsonify({
                "response": response.choices[0].message.content
            })
        except Exception as e:
            logger.error(f"Error in fallback chat: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    except Exception as e:
        logger.error(f"Error in smart query: {str(e)}")
        return jsonify({"error": str(e)}), 500



# Print startup information
print(f"Starting Aegis API on port {int(os.environ.get('PORT', 5001))}")
print(f"API Key configured: {'Yes' if os.environ.get('OPENAI_API_KEY') else 'No'}")
print(f"Data directory: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'results')}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True)

# Add these new endpoints for MCP client interaction

@app.route('/mcp/capabilities', methods=['GET'])
def get_mcp_capabilities():
    """Get all MCP server capabilities"""
    capabilities = {}
    
    for server_id, server in mcp_servers.items():
        desc = server.get_description()
        capabilities[server_id] = {
            "name": desc["name"],
            "description": desc["description"],
            "capabilities": desc["capabilities"]
        }
    
    return jsonify(capabilities)

@app.route('/mcp/execute', methods=['POST'])
def execute_mcp_request():
    """Execute an MCP capability request"""
    global current_schedule_data
    try:
        data = request.json
        request_id = data.get('requestId')
        server_id = data.get('serverId')
        capability_id = data.get('capabilityId')
        params = data.get('params', {})
        
        if not request_id or not server_id or not capability_id:
            return jsonify({
                "status": "error",
                "message": "Missing required fields: requestId, serverId, or capabilityId"
            }), 400
        
        if not current_schedule_data:
            return jsonify({
                "status": "error",
                "message": "No schedule data available"
            }), 400
        
        if server_id not in mcp_servers:
            return jsonify({
                "status": "error",
                "message": f"Server {server_id} not found"
            }), 404
        
        server = mcp_servers[server_id]
        if capability_id not in server.capabilities:
            return jsonify({
                "status": "error",
                "message": f"Capability {capability_id} not found in server {server_id}"
            }), 404
        
        # Execute the capability
        result = server.execute(capability_id, params, current_schedule_data)
        
        return jsonify({
            "requestId": request_id,
            "status": "success" if "error" not in result else "error",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error executing MCP request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500