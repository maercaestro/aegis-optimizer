#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main entry point for the Aegis Refinery Optimizer.
"""

import json
import logging
import argparse
import os
from datetime import datetime

from backend.data_loader import load_input_data
from backend.core.scheduler import SimpleScheduler
from backend.core.vessel_optimizer import VesselOptimizer
from backend.agent.base import OptimizerAgent
from backend.agent.optimizer_tools import (
    VesselOptimizationTool, 
    LPOptimizationTool,
    FullOptimizationTool
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_data_directories():
    """Ensure all required data directories exist."""
    # Get the project root directory (parent of backend)
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Define required data directories
    data_dirs = [
        os.path.join(project_dir, "data"),
        os.path.join(project_dir, "data", "uploads"),
        os.path.join(project_dir, "data", "results")
    ]
    
    # Create directories if they don't exist
    for directory in data_dirs:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")

def main():
    """Main function to run the optimization process."""
    # Ensure required directories exist
    ensure_data_directories()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Aegis Refinery Optimizer")
    parser.add_argument("--mode", choices=["standard", "vessel", "lp", "full"], default="standard",
                       help="Optimization mode to run")
    parser.add_argument("--input", default="data/input.json",
                       help="Path to the input data file")
    parser.add_argument("--loading", default="data/loading_date_ranges.json",
                       help="Path to the loading date ranges file")
    parser.add_argument("--schedule", 
                       help="Path to an existing schedule file (for LP optimization)")
    args = parser.parse_args()
    
    # Convert relative paths to absolute paths
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if not os.path.isabs(args.input):
        args.input = os.path.join(project_dir, args.input)
    
    if not os.path.isabs(args.loading):
        args.loading = os.path.join(project_dir, args.loading)
    
    if args.schedule and not os.path.isabs(args.schedule):
        args.schedule = os.path.join(project_dir, args.schedule)
    
    logger.info(f"Starting Aegis Refinery Optimizer in {args.mode} mode")
    
    if args.mode == "standard":
        # Traditional pipeline without agent tools
        run_standard_pipeline(args.input, args.loading)
    else:
        # Use agent tools for optimization
        run_agent_pipeline(args)
    
    logger.info("Optimization completed")

def run_standard_pipeline(input_file, loading_file):
    """Run the traditional optimization pipeline without agent tools."""
    # Check if input files exist
    for file_path, file_desc in [(input_file, "input data"), (loading_file, "loading data")]:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path} ({file_desc})")
            return
    
    # Load input data
    try:
        input_data = load_input_data(input_file)
        logger.info(f"Loaded input data from {input_file}")
    except Exception as e:
        logger.error(f"Failed to load input data: {str(e)}")
        return
    
    # Run vessel optimization
    logger.info("Running vessel optimization")
    try:
        vessel_optimizer = VesselOptimizer(loading_file)
        optimization_result = vessel_optimizer.optimize()
        
        if optimization_result["status"] == "optimal":
            logger.info(f"Vessel optimization successful: {optimization_result['vessel_count']} vessels, " 
                      f"${optimization_result['freight_cost']:,.2f} freight cost")
            
            # Format vessels for scheduler
            optimized_vessels = vessel_optimizer.format_vessels_for_scheduler(optimization_result)
        else:
            logger.warning(f"Vessel optimization failed: {optimization_result.get('message', 'Unknown error')}")
            optimized_vessels = None
            
    except Exception as e:
        logger.error(f"Error in vessel optimization: {str(e)}")
        optimized_vessels = None
    
    # Create a simple scheduler
    try:
        scheduler = SimpleScheduler(input_data)
        
        # Run the simple scheduler with optimized vessels if available
        if optimized_vessels:
            logger.info("Using optimized vessel allocation for scheduling")
            schedule = scheduler.generate_schedule(optimized_vessels)
        else:
            logger.info("Using default vessel allocation for scheduling")
            schedule = scheduler.generate_schedule()
        
        # Output the schedule
        print_schedule(schedule, optimization_result if optimized_vessels else None)
        
        # Save the schedule to a file
        save_schedule(schedule, optimization_result if optimized_vessels else None)
            
    except Exception as e:
        logger.error(f"Error in scheduling: {str(e)}")

def run_agent_pipeline(args):
    """Run optimization using the agent framework."""
    # Create agent and register tools
    agent = OptimizerAgent()
    agent.register_tool(VesselOptimizationTool())
    agent.register_tool(LPOptimizationTool())
    agent.register_tool(FullOptimizationTool())
    
    try:
        if args.mode == "vessel":
            # Check if loading file exists
            if not os.path.exists(args.loading):
                logger.error(f"Loading data file not found: {args.loading}")
                return
                
            # Run vessel optimization only
            logger.info("Running vessel optimization with agent")
            result = agent.run_tool(
                "VesselOptimizationTool",
                loading_data_path=args.loading,
                output_format="full"
            )
            
            if result["status"] == "optimal":
                logger.info(f"Vessel optimization successful: {result['vessel_count']} vessels, " 
                          f"${result['freight_cost']:,.2f} freight cost")
                
                # Format for scheduler
                vessel_optimizer = VesselOptimizer(args.loading)
                optimized_vessels = vessel_optimizer.format_vessels_for_scheduler(result)
                
                # Check if input file exists
                if not os.path.exists(args.input):
                    logger.error(f"Input data file not found: {args.input}")
                    return
                
                # Generate schedule with optimized vessels
                input_data = load_input_data(args.input)
                scheduler = SimpleScheduler(input_data)
                schedule = scheduler.generate_schedule(optimized_vessels)
                
                # Output and save the schedule
                print_schedule(schedule, result)
                save_schedule(schedule, result)
            else:
                logger.error(f"Vessel optimization failed: {result.get('message', 'Unknown error')}")
                
        elif args.mode == "lp":
            # Run LP optimization on an existing schedule
            if not args.schedule:
                logger.error("LP optimization requires a schedule file. Use --schedule to specify.")
                return
                
            if not os.path.exists(args.schedule):
                logger.error(f"Schedule file not found: {args.schedule}")
                return
                
            logger.info(f"Running LP optimization with agent on {args.schedule}")
            result = agent.run_tool(
                "LPOptimizationTool",
                schedule_file=args.schedule,
                save_output=True
            )
            
            if result["status"] == "optimal":
                logger.info(f"LP optimization successful. Output saved to {result['output_file']}")
                
                # Load and print the optimized schedule
                try:
                    with open(result["output_file"], 'r') as f:
                        optimized_schedule = json.load(f)
                        
                    print_schedule(optimized_schedule)
                except Exception as e:
                    logger.error(f"Error loading optimized schedule: {str(e)}")
            else:
                logger.error(f"LP optimization failed: {result.get('message', 'Unknown error')}")
                
        elif args.mode == "full":
            # Check if input files exist
            for file_path, file_desc in [(args.input, "input data"), (args.loading, "loading data")]:
                if not os.path.exists(file_path):
                    logger.error(f"File not found: {file_path} ({file_desc})")
                    return
                    
            # Run full optimization pipeline
            logger.info("Running full optimization pipeline with agent")
            result = agent.run_tool(
                "FullOptimizationTool",
                loading_data_path=args.loading,
                input_data_path=args.input,
                save_output=True
            )
            
            if result["status"] == "optimal":
                logger.info("Full optimization successful")
                logger.info(f"Vessel optimization: {result['vessel_optimization']['vessel_count']} vessels, "
                          f"${result['vessel_optimization']['freight_cost']:,.2f} freight cost")
                
                # Load and print the final optimized schedule
                try:
                    lp_result = result["lp_optimization"]
                    with open(lp_result["output_file"], 'r') as f:
                        final_schedule = json.load(f)
                        
                    print_schedule(final_schedule, result["vessel_optimization"])
                except Exception as e:
                    logger.error(f"Error loading optimized schedule: {str(e)}")
            else:
                logger.error(f"Full optimization failed: {result.get('message', 'Unknown error')}")
                logger.error(f"Stage: {result.get('stage', 'unknown')}")
    except Exception as e:
        logger.error(f"Error in agent pipeline: {str(e)}")

def print_schedule(schedule, vessel_optimization=None):
    """Print the schedule in a readable format."""
    print("\n=== REFINERY SCHEDULE ===")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Print vessel optimization results if available
    if vessel_optimization:
        print("\n=== VESSEL OPTIMIZATION RESULTS ===")
        print(f"Number of vessels: {vessel_optimization['vessel_count']}")
        print(f"Total freight cost: ${vessel_optimization['freight_cost']:,.2f}")
    
    print("\nDaily Processing Plan:")
    
    for day, day_plan in schedule["daily_plan"].items():
        print(f"\n--- Day {day} ---")
        
        # Print blending details
        print("Blending Operations:")
        for blend in day_plan.get("blending_details", []):
            if blend["secondary_grade"]:
                print(f"  Blend {blend['primary_grade']} ({blend['primary_rate']:.1f} kbpd) + "
                      f"{blend['secondary_grade']} ({blend['secondary_rate']:.1f} kbpd) = "
                      f"{blend['total_rate']:.1f} kbpd with ratio {blend['ratio']}")
            else:
                print(f"  Process {blend['primary_grade']} solo: {blend['primary_rate']:.1f} kbpd")
        
        # Print inventory
        print("Inventory:")
        for grade, volume in day_plan["inventory_by_grade"].items():
            print(f"  {grade}: {volume:.1f} kb")
        print(f"  Total: {day_plan['inventory']:.1f} kb")
        
        # Print tank status
        print("Tank Status:")
        for tank_name, tank_data in day_plan["tanks"].items():
            contents_str = ", ".join(f"{c['grade']}: {c['volume']:.1f} kb" for c in tank_data["contents"])
            contents_str = contents_str if contents_str else "Empty"
            current_volume = sum(content["volume"] for content in tank_data["contents"])
            print(f"  {tank_name} ({current_volume:.1f}/{tank_data['capacity']:.1f} kb): {contents_str}")

    print("\nVessel Arrivals:")
    for vessel in schedule["vessel_arrivals"]:
        print(f"\nVessel arriving on day {vessel['arrival_day']} (LDR: {vessel.get('ldr_text', 'N/A')})")
        for cargo in vessel["cargo"]:
            print(f"  {cargo['grade']}: {cargo['volume']} kb from {cargo['origin']}")
            
            # Print tank allocations if available
            if "tank_allocation" in cargo:
                print("  Allocated to:")
                for alloc in cargo["tank_allocation"]:
                    print(f"    {alloc['tank']}: {alloc['volume']:.1f} kb")
    
    # Print held vessels
    if "held_vessels" in schedule and schedule["held_vessels"]:
        print("\nDeferred Vessels (Insufficient Ullage):")
        for vessel in schedule["held_vessels"]:
            original_day = vessel.get("original_arrival_day", vessel["arrival_day"])
            days_held = vessel.get("days_held", "Unknown")
            print(f"\nVessel originally planned for day {original_day} (LDR: {vessel.get('ldr_text', 'N/A')})")
            print(f"  Held for: {days_held} days")
            print(f"  Reason: {vessel.get('held_reason', 'Unknown')}")
            print(f"  Earliest possible berth day: {vessel.get('earliest_possible_day', 'Unknown')}")
            
            for cargo in vessel["cargo"]:
                print(f"  {cargo['grade']}: {cargo['volume']} kb from {cargo['origin']}")
                
                # Print simulated allocation and overflow amount if available
                if "simulated_allocation" in cargo:
                    print("  Attempted allocation:")
                    
                    # Show valid allocations
                    for alloc in cargo.get("simulated_allocation", []):
                        print(f"    {alloc['tank']}: {alloc['volume']:.1f} kb")
                    
                    # Show overflow amount if present
                    if "overflow_amount" in cargo and cargo["overflow_amount"] > 0:
                        print(f"    Insufficient ullage: {cargo['overflow_amount']:.1f} kb")
                    elif cargo.get("overflow_amount", 0) == 0:
                        print("    Other cargoes in this vessel caused deferment")
                        
    # Print summary statistics
    print("\n=== SCHEDULE SUMMARY ===")
    total_vessels = len(schedule["vessel_arrivals"])
    deferred_vessels = len(schedule.get("held_vessels", []))
    print(f"Vessels successfully berthed: {total_vessels}")
    print(f"Vessels deferred due to tank constraints: {deferred_vessels}")
    
    # Calculate total crude processed
    total_processed = 0
    for day, day_plan in schedule["daily_plan"].items():
        day_total = sum(day_plan["processing_rates"].values())
        total_processed += day_total
    
    print(f"Total crude processed: {total_processed:.1f} kb")
    print(f"Average daily processing: {total_processed/len(schedule['daily_plan']):.1f} kbpd")
    
    # Print final inventory position
    final_day = max(schedule["daily_plan"].keys())
    final_inventory = schedule["daily_plan"][final_day]["inventory"]
    print(f"Final inventory: {final_inventory:.1f} kb")

def save_schedule(schedule, vessel_optimization=None):
    """Save the schedule to a JSON file."""
    # Create timestamp for the filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Get the project root directory
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Ensure data directory exists
    data_dir = os.path.join(project_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Timestamped output file with absolute path
    output_file = os.path.join(data_dir, f"schedule_output_{timestamp}.json")
    
    # Fixed output file with absolute path
    fixed_output_file = os.path.join(data_dir, "latest_schedule_output.json")
    
    # Add vessel optimization results if available
    if vessel_optimization:
        schedule["vessel_optimization"] = {
            "vessel_count": vessel_optimization["vessel_count"],
            "freight_cost": vessel_optimization["freight_cost"]
        }
    
    # Save to timestamped file
    with open(output_file, 'w') as f:
        json.dump(schedule, f, indent=2)
    
    # Also save to fixed filename (will overwrite any existing file)
    with open(fixed_output_file, 'w') as f:
        json.dump(schedule, f, indent=2)
    
    logger.info(f"Schedule saved to {output_file} and {fixed_output_file}")
    
    return output_file

if __name__ == "__main__":
    ensure_data_directories()
    main()