#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main entry point for the Aegis Refinery Optimizer.
"""

import json
import logging
from datetime import datetime

from data_loader import load_input_data
from scheduler import SimpleScheduler
from vessel_optimizer import VesselOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the optimization process."""
    
    logger.info("Starting Aegis Refinery Optimizer")
    
    # Load input data
    input_data = load_input_data("data/input.json")
    
    # Run vessel optimization
    logger.info("Running vessel optimization")
    vessel_optimizer = VesselOptimizer("data/loading_date_ranges.json")
    optimization_result = vessel_optimizer.optimize()
    
    if optimization_result["status"] == "optimal":
        logger.info(f"Vessel optimization successful: {optimization_result['vessel_count']} vessels, " 
                   f"${optimization_result['freight_cost']:,.2f} freight cost")
        
        # Format vessels for scheduler
        optimized_vessels = vessel_optimizer.format_vessels_for_scheduler(optimization_result)
    else:
        logger.warning("Vessel optimization failed, using default vessel allocation")
        optimized_vessels = None
    
    # Create a simple scheduler
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
    
    logger.info("Optimization completed")

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
    output_file = f"data/schedule_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Add vessel optimization results if available
    if vessel_optimization:
        schedule["vessel_optimization"] = {
            "vessel_count": vessel_optimization["vessel_count"],
            "freight_cost": vessel_optimization["freight_cost"]
        }
    
    with open(output_file, 'w') as f:
        json.dump(schedule, f, indent=2)
    logger.info(f"Schedule saved to {output_file}")

if __name__ == "__main__":
    main()