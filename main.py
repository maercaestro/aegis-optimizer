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
    
    # Create a simple scheduler
    scheduler = SimpleScheduler(input_data)
    
    # Run the simple scheduler
    schedule = scheduler.generate_schedule()
    
    # Output the schedule
    print_schedule(schedule)
    
    # Save the schedule to a file
    save_schedule(schedule)
    
    logger.info("Optimization completed")

def print_schedule(schedule):
    """Print the schedule in a readable format."""
    print("\n=== REFINERY SCHEDULE ===")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
        print("\nHeld Vessels (Insufficient Ullage):")
        for vessel in schedule["held_vessels"]:
            original_day = vessel.get("original_arrival_day", vessel["arrival_day"])
            days_held = vessel.get("days_held", "Unknown")
            print(f"\nVessel originally planned for day {original_day} (LDR: {vessel.get('ldr_text', 'N/A')})")
            print(f"  Held for: {days_held} days")
            print(f"  Reason: {vessel.get('held_reason', 'Unknown')}")
            print(f"  Earliest possible berth day: {vessel.get('earliest_possible_day', 'Unknown')}")
            
            for cargo in vessel["cargo"]:
                print(f"  {cargo['grade']}: {cargo['volume']} kb from {cargo['origin']}")
                
                # Print simulated allocation if available
                if "simulated_allocation" in cargo:
                    print("  Attempted allocation:")
                    overflow_volume = 0
                    for alloc in cargo["simulated_allocation"]:
                        if alloc["tank"] == "OVERFLOW":
                            overflow_volume = alloc["volume"]
                        else:
                            print(f"    {alloc['tank']}: {alloc['volume']:.1f} kb")
                    
                    if overflow_volume > 0:
                        print(f"    OVERFLOW: {overflow_volume:.1f} kb (insufficient ullage)")

def save_schedule(schedule):
    """Save the schedule to a JSON file."""
    output_file = f"data/schedule_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(schedule, f, indent=2)
    logger.info(f"Schedule saved to {output_file}")

if __name__ == "__main__":
    main()