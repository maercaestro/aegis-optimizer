from mcp.server.fastmcp import FastMCP, Context
import json
import os
import sys

# Add the parent directory to path so we can import from the api package
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Import the MCPServers from existing Flask implementation
from api.app import (
    DayProcessingAnalyzer, 
    VesselTracker, 
    TankInventoryManager, 
    CrudeGradeProcessor
)

# Initialize our data store
schedule_data = None

# Create an MCP server
mcp = FastMCP(
    "Aegis Refinery Optimizer",
    description="Tools for analyzing and optimizing refinery schedules"
)

# Initialize our domain servers
day_analyzer = DayProcessingAnalyzer()
vessel_tracker = VesselTracker()
tank_manager = TankInventoryManager()
grade_processor = CrudeGradeProcessor()

# --- Day Analyzer Tools ---

@mcp.tool(name="findLowestProcessingDay")
def find_lowest_processing_day() -> dict:
    """Find the day with the lowest processing rate"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return day_analyzer.findLowestProcessingDay({}, schedule_data)

@mcp.tool(name="findHighestProcessingDay")
def find_highest_processing_day() -> dict:
    """Find the day with the highest processing rate"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return day_analyzer.findHighestProcessingDay({}, schedule_data)

@mcp.tool(name="compareDays")
def compare_days(day1: str, day2: str) -> dict:
    """Compare processing rates between two days"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return day_analyzer.compareDays({"day1": day1, "day2": day2}, schedule_data)

@mcp.tool(name="getAverageProcessingRates")
def get_average_processing_rates() -> dict:
    """Calculate average processing rates by grade and overall"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return day_analyzer.getAverageProcessingRates({}, schedule_data)

@mcp.tool(name="analyzeProcessingTrends")
def analyze_processing_trends() -> dict:
    """Analyze trends in processing rates over time"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return day_analyzer.analyzeProcessingTrends({}, schedule_data)

# --- Vessel Tracker Tools ---

@mcp.tool(name="getVesselSchedule")
def get_vessel_schedule() -> dict:
    """Get the schedule of all vessels"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return vessel_tracker.getVesselSchedule({}, schedule_data)

@mcp.tool(name="getVesselCargo")
def get_vessel_cargo(vessel_id: str) -> dict:
    """Get cargo details for a specific vessel"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return vessel_tracker.getVesselCargo({"vesselId": vessel_id}, schedule_data)

@mcp.tool(name="findVesselByDay")
def find_vessel_by_day(day: str) -> dict:
    """Find vessels arriving on a specific day"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return vessel_tracker.findVesselByDay({"day": day}, schedule_data)

# --- Tank Manager Tools ---

@mcp.tool(name="getTankCapacities")
def get_tank_capacities() -> dict:
    """Get capacities for all tanks"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return tank_manager.getTankCapacities({}, schedule_data)

@mcp.tool(name="getTankContents")
def get_tank_contents(tank_name: str, day: str) -> dict:
    """Get contents of a specific tank on a specific day"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return tank_manager.getTankContents({"tankName": tank_name, "day": day}, schedule_data)

@mcp.tool(name="checkTankUtilization")
def check_tank_utilization() -> dict:
    """Check utilization of tanks across the schedule"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return tank_manager.checkTankUtilization({}, schedule_data)

# --- Grade Processor Tools ---

@mcp.tool(name="getGradeVolumes")
def get_grade_volumes() -> dict:
    """Get total volumes for all grades"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return grade_processor.getGradeVolumes({}, schedule_data)

@mcp.tool(name="compareGrades")
def compare_grades(grade1: str, grade2: str) -> dict:
    """Compare processing volumes between two grades"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return grade_processor.compareGrades({"grade1": grade1, "grade2": grade2}, schedule_data)

@mcp.tool(name="trackGradeByDay")
def track_grade_by_day(grade: str) -> dict:
    """Track processing of a specific grade across days"""
    global schedule_data
    if not schedule_data:
        return {"error": "No schedule data available"}
    
    return grade_processor.trackGradeByDay({"grade": grade}, schedule_data)

# --- Data Management Tools ---

@mcp.tool(name="loadScheduleData")
def load_schedule_data(file_path: str) -> dict:
    """Load schedule data from a file"""
    global schedule_data
    try:
        with open(file_path, 'r') as f:
            schedule_data = json.load(f)
        return {"status": "success", "message": "Schedule data loaded successfully"}
    except Exception as e:
        return {"error": f"Failed to load schedule data: {str(e)}"}

@mcp.tool(name="getDataStatus")
def get_data_status() -> dict:
    """Check if schedule data is loaded"""
    global schedule_data
    return {
        "status": "available" if schedule_data else "not_available",
        "data_keys": list(schedule_data.keys()) if schedule_data else []
    }

# Main function to run the server
async def run_server():
    from mcp.server.stdio import stdio_server
    from mcp.types import InitializationOptions, NotificationOptions

    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="aegis-optimizer",
                server_version="0.1.0",
                capabilities=mcp.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_server())