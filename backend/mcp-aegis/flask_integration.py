"""
Integration between Flask API and MCP Server - 
Acts as API gateway for the frontend
"""
import os
import json
import asyncio
import functools
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import nest_asyncio
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Apply nest_asyncio to allow asyncio to work in Flask
nest_asyncio.apply()

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global storage for schedule data
schedule_data = None

# Helper to make async functions work in regular Flask routes
def async_to_sync(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# Add a simple index route for testing
@app.route('/')
def index():
    return jsonify({
        "status": "MCP API Gateway running",
        "endpoints": [
            "/mcp/capabilities",
            "/mcp/execute",
            "/mcp/chat",
            "/mcp/set-schedule"
        ],
        "schedule_data_loaded": schedule_data is not None
    })

@app.route('/mcp/capabilities', methods=['GET'])
def get_capabilities():
    """Get all MCP server capabilities"""
    try:
        capabilities = {
            "defaultServer": {
                "name": "Aegis Optimizer",
                "description": "MCP Server for Aegis Refinery Optimizer",
                "capabilities": [
                    "findLowestProcessingDay",
                    "findHighestProcessingDay", 
                    "compareDays",
                    "getAverageProcessingRates",
                    "analyzeProcessingTrends",
                    "getVesselSchedule",
                    "getVesselCargo",
                    "findVesselByDay",
                    "getTankCapacities",
                    "getTankContents",
                    "checkTankUtilization",
                    "getGradeVolumes",
                    "compareGrades",
                    "trackGradeByDay",
                    "getDataStatus"
                ]
            }
        }
        return jsonify(capabilities)
    except Exception as e:
        print(f"Error in get_capabilities: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Real processing functions for schedule data
class RefineryTools:
    @staticmethod
    def find_lowest_processing_day(data):
        """Find the day with lowest processing volume"""
        if not data or "daily_processing" not in data:
            return {"error": "No valid processing data"}
        
        daily_processing = data.get("daily_processing", {})
        if not daily_processing:
            return {"error": "No daily processing data available"}
        
        min_day = None
        min_volume = float('inf')
        
        for day, volume in daily_processing.items():
            if volume < min_volume:
                min_volume = volume
                min_day = day
        
        return {
            "day": min_day,
            "volume": min_volume,
            "unit": data.get("volume_unit", "units")
        }
    
    @staticmethod
    def find_highest_processing_day(data):
        """Find the day with highest processing volume"""
        if not data or "daily_processing" not in data:
            return {"error": "No valid processing data"}
        
        daily_processing = data.get("daily_processing", {})
        if not daily_processing:
            return {"error": "No daily processing data available"}
        
        max_day = None
        max_volume = float('-inf')
        
        for day, volume in daily_processing.items():
            if volume > max_volume:
                max_volume = volume
                max_day = day
        
        return {
            "day": max_day,
            "volume": max_volume,
            "unit": data.get("volume_unit", "units")
        }
    
    @staticmethod
    def compare_days(data, day1, day2):
        """Compare processing volumes between two days"""
        if not data or "daily_processing" not in data:
            return {"error": "No valid processing data"}
        
        daily_processing = data.get("daily_processing", {})
        if not daily_processing:
            return {"error": "No daily processing data available"}
        
        volume1 = daily_processing.get(day1)
        volume2 = daily_processing.get(day2)
        
        if volume1 is None:
            return {"error": f"No data for day {day1}"}
        
        if volume2 is None:
            return {"error": f"No data for day {day2}"}
        
        difference = volume1 - volume2
        percentage = (difference / volume2) * 100 if volume2 != 0 else float('inf')
        
        return {
            "day1": day1,
            "volume1": volume1,
            "day2": day2,
            "volume2": volume2,
            "difference": difference,
            "percentage_difference": percentage,
            "unit": data.get("volume_unit", "units")
        }
    
    @staticmethod
    def get_vessel_schedule(data):
        """Get schedule of all vessels"""
        if not data or "vessels" not in data:
            return {"error": "No valid vessel data"}
        
        vessels = data.get("vessels", [])
        if not vessels:
            return {"error": "No vessel data available"}
        
        return {
            "vessel_count": len(vessels),
            "vessels": vessels
        }
    
    @staticmethod
    def get_vessel_cargo(data, vessel_id):
        """Get cargo information for a specific vessel"""
        if not data or "vessels" not in data:
            return {"error": "No valid vessel data"}
        
        vessels = data.get("vessels", [])
        if not vessels:
            return {"error": "No vessel data available"}
        
        for vessel in vessels:
            if str(vessel.get("id")) == str(vessel_id):
                return {
                    "vessel_id": vessel_id,
                    "cargo": vessel.get("cargo", []),
                    "arrival_day": vessel.get("arrival_day"),
                    "departure_day": vessel.get("departure_day")
                }
        
        return {"error": f"No vessel found with ID {vessel_id}"}
    
    @staticmethod
    def get_tank_capacities(data):
        """Get capacities for all tanks"""
        if not data or "tanks" not in data:
            return {"error": "No valid tank data"}
        
        tanks = data.get("tanks", [])
        if not tanks:
            return {"error": "No tank data available"}
        
        tank_capacities = {}
        for tank in tanks:
            tank_capacities[tank.get("name")] = {
                "capacity": tank.get("capacity"),
                "unit": data.get("volume_unit", "units")
            }
        
        return {
            "tank_count": len(tanks),
            "capacities": tank_capacities
        }
    
    @staticmethod
    def get_grade_volumes(data):
        """Get total volumes for all crude grades"""
        if not data or "grades" not in data:
            return {"error": "No valid grade data"}
        
        grades = data.get("grades", [])
        if not grades:
            return {"error": "No grade data available"}
        
        grade_volumes = {}
        for grade in grades:
            grade_volumes[grade.get("name")] = {
                "total_volume": grade.get("total_volume"),
                "daily_processing": grade.get("daily_processing", {}),
                "unit": data.get("volume_unit", "units")
            }
        
        return {
            "grade_count": len(grades),
            "volumes": grade_volumes
        }
    
    @staticmethod
    def get_data_status(data):
        """Check status of loaded data"""
        if not data:
            return {"status": "No data loaded"}
        
        sections = []
        if "daily_processing" in data:
            sections.append("daily_processing")
        if "vessels" in data:
            sections.append("vessels")
        if "tanks" in data:
            sections.append("tanks")
        if "grades" in data:
            sections.append("grades")
        
        return {
            "status": "Data loaded",
            "available_sections": sections,
            "data_timestamp": data.get("timestamp", "unknown")
        }

# Map capabilities to functions
tool_map = {
    "findLowestProcessingDay": RefineryTools.find_lowest_processing_day,
    "findHighestProcessingDay": RefineryTools.find_highest_processing_day,
    "compareDays": RefineryTools.compare_days,
    "getVesselSchedule": RefineryTools.get_vessel_schedule,
    "getVesselCargo": RefineryTools.get_vessel_cargo,
    "getTankCapacities": RefineryTools.get_tank_capacities,
    "getGradeVolumes": RefineryTools.get_grade_volumes,
    "getDataStatus": RefineryTools.get_data_status
}

@app.route('/mcp/execute', methods=['POST'])
def execute_capability():
    """Execute a specific MCP capability with real data"""
    global schedule_data
    
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    request_id = data.get('requestId')
    capability_id = data.get('capabilityId')
    params = data.get('params', {})
    
    if not capability_id or not request_id:
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400
    
    if not schedule_data:
        return jsonify({
            "requestId": request_id,
            "status": "error",
            "error": "No schedule data loaded",
            "timestamp": datetime.now().isoformat()
        }), 400
    
    try:
        if capability_id not in tool_map:
            return jsonify({
                "requestId": request_id,
                "status": "error",
                "error": f"Unknown capability: {capability_id}",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        # Execute the tool function with real data
        tool_function = tool_map[capability_id]
        
        # Special handling for functions that need additional parameters
        if capability_id == "compareDays":
            result = tool_function(schedule_data, params.get("day1"), params.get("day2"))
        elif capability_id == "getVesselCargo":
            result = tool_function(schedule_data, params.get("vessel_id"))
        else:
            result = tool_function(schedule_data)
        
        return jsonify({
            "requestId": request_id,
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error executing {capability_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "requestId": request_id,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/mcp/chat', methods=['POST'])
def mcp_chat():
    """Chat endpoint that processes queries against real schedule data"""
    global schedule_data
    
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        query = data.get('query', '')
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        # Check if we have schedule data
        if not schedule_data:
            return jsonify({
                "response": "I don't have any schedule data loaded yet. Please upload schedule data first.",
                "debug": {"tool_calls": []}
            })
        
        # Process with OpenAI
        try:
            import openai
            
            # Initialize OpenAI client
            openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # Build list of available tools
            tools_description = []
            for tool_name, tool_function in tool_map.items():
                tools_description.append(f"- {tool_name}: {tool_function.__doc__}")
            
            # Create system prompt with tools info
            system_prompt = f"""You are an assistant that analyzes refinery schedule data.

You can call the following tools to analyze the schedule:

{chr(10).join(tools_description)}

When you need to use a tool:
1. Think about which tool is most appropriate for the question
2. Format your tool call exactly like this: TOOL[tool_name(param1="value1", param2="value2")]
3. Wait for the tool result before providing your final answer

Always base your answers on the data from the tools. If you can't answer with the available tools, say so."""

            # First pass - planning with OpenAI
            planning_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            planning_text = planning_response.choices[0].message.content
            
            # Extract tool calls with regex
            pattern = r'TOOL\[(\w+)\((.*?)\)\]'
            tool_calls = []
            matches = re.findall(pattern, planning_text)
            
            for match in matches:
                tool_name = match[0]
                params_text = match[1]
                
                # Parse parameters
                params = {}
                if params_text.strip():
                    param_pattern = r'(\w+)=(?:"([^"]*?)"|\'([^\']*?)\'|([^,\s]+))'
                    param_matches = re.findall(param_pattern, params_text)
                    for param_match in param_matches:
                        param_name = param_match[0]
                        param_value = next((g for g in param_match[1:] if g), None)
                        params[param_name] = param_value
                
                tool_calls.append({
                    "name": tool_name,
                    "params": params
                })
            
            # Execute tool calls
            tool_results = []
            for call in tool_calls:
                try:
                    tool_name = call["name"]
                    
                    if tool_name not in tool_map:
                        tool_results.append({
                            "name": tool_name,
                            "params": call["params"],
                            "error": f"Unknown tool: {tool_name}",
                            "success": False
                        })
                        continue
                    
                    # Get the tool function
                    tool_function = tool_map[tool_name]
                    
                    # Special handling for functions that need additional parameters
                    if tool_name == "compareDays":
                        result = tool_function(schedule_data, call["params"].get("day1"), call["params"].get("day2"))
                    elif tool_name == "getVesselCargo":
                        result = tool_function(schedule_data, call["params"].get("vessel_id"))
                    else:
                        result = tool_function(schedule_data)
                    
                    tool_results.append({
                        "name": tool_name,
                        "params": call["params"],
                        "result": result,
                        "success": True
                    })
                except Exception as e:
                    tool_results.append({
                        "name": call["name"],
                        "params": call["params"],
                        "error": str(e),
                        "success": False
                    })
            
            # Generate final response
            if not tool_results:
                # If no tools were called, return the planning response directly
                return jsonify({
                    "response": planning_text,
                    "debug": {"tool_calls": []}
                })
            
            # Format tool results for the final prompt
            tool_results_text = []
            for tr in tool_results:
                if tr["success"]:
                    result_str = json.dumps(tr["result"], indent=2)
                    tool_results_text.append(f"TOOL RESULT for {tr['name']}:\n{result_str}")
                else:
                    tool_results_text.append(f"TOOL ERROR for {tr['name']}:\n{tr['error']}")
            
            tool_results_combined = "\n\n".join(tool_results_text)
            
            # Second pass - synthesize results
            final_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that explains refinery scheduling data. Answer the user's question based on the tool results provided. Make your answer clear and concise. Do not mention the tools directly in your response."},
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": "I'll help answer that."},
                    {"role": "user", "content": f"Here are the results from the tools:\n\n{tool_results_combined}\n\nPlease provide a clear answer based on this data."}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return jsonify({
                "response": final_response.choices[0].message.content,
                "debug": {
                    "tool_calls": [f"{tc['name']}({json.dumps(tc['params'])})" for tc in tool_calls]
                }
            })
            
        except ImportError:
            # If OpenAI is not available, use a simpler approach
            response = "I don't have access to OpenAI for processing. Here's what I know about the schedule:\n\n"
            
            # Add some basic stats from the data
            if "vessel_count" in schedule_data:
                response += f"- There are {schedule_data['vessel_count']} vessels in the schedule.\n"
            
            if "daily_processing" in schedule_data:
                days = len(schedule_data["daily_processing"])
                response += f"- The schedule spans {days} days.\n"
                
                # Find highest and lowest processing days
                highest_tool = RefineryTools.find_highest_processing_day(schedule_data)
                lowest_tool = RefineryTools.find_lowest_processing_day(schedule_data)
                
                if "day" in highest_tool:
                    response += f"- The highest processing day is {highest_tool['day']} with {highest_tool['volume']} units.\n"
                
                if "day" in lowest_tool:
                    response += f"- The lowest processing day is {lowest_tool['day']} with {lowest_tool['volume']} units.\n"
            
            return jsonify({
                "response": response,
                "debug": {"tool_calls": []}
            })
            
    except Exception as e:
        print(f"Error in mcp_chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/mcp/set-schedule', methods=['POST'])
def set_schedule():
    """Set schedule data for MCP tools"""
    global schedule_data
    
    if not request.is_json:
        return jsonify({"error": "Expected JSON data"}), 400
    
    try:
        schedule_data = request.json
        if not schedule_data:
            return jsonify({"error": "No schedule data provided"}), 400
        
        # Add timestamp
        schedule_data["timestamp"] = datetime.now().isoformat()
        
        print(f"Loaded schedule data with {len(json.dumps(schedule_data))} characters")
        
        # Extra data validation and preprocessing could be done here
        return jsonify({
            "message": "Schedule data set successfully", 
            "data_size": len(json.dumps(schedule_data))
        })
    except Exception as e:
        print(f"Error in set_schedule: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Serve frontend assets if needed
@app.route('/assets/<path:path>')
def serve_assets(path):
    frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                              '..', '..', 'frontend', 'dist', 'assets')
    return send_from_directory(frontend_path, path)

# Add this function after your imports
def load_sample_schedule_data():
    """Load sample schedule data from files in the project directory"""
    global schedule_data
    
    # Check for data files in different possible locations
    possible_paths = [
        "sample_schedule.json",
        "data/sample_schedule.json",
        "data/refinery_schedule.json",
        "../data/sample_schedule.json",
        "../../data/refinery_schedule.json"
    ]
    
    # Search for any valid data file
    for rel_path in possible_paths:
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r') as f:
                    schedule_data = json.load(f)
                    print(f"✅ Loaded sample schedule data from {full_path}")
                    print(f"Data contains keys: {list(schedule_data.keys())}")
                    return True
            except Exception as e:
                print(f"❌ Error loading data from {full_path}: {e}")
    
    print("❌ No sample schedule data files found in project directory")
    return False

# Then modify the run_flask function to call this at startup
def run_flask():
    port = int(os.environ.get("MCP_FLASK_PORT", 5005))
    print(f"Starting MCP Gateway API on http://localhost:{port}")
    
    # Try to load sample data on startup
    if load_sample_schedule_data():
        print("Sample schedule data loaded successfully")
    else:
        print("No sample data found - waiting for data to be sent via API")
    
    app.run(host="0.0.0.0", port=port, debug=True)

if __name__ == "__main__":
    run_flask()