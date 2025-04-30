#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple scheduler module for the Aegis Refinery Optimizer.
"""

import logging
from datetime import datetime, timedelta
from utils import parse_ldr_date, calculate_processing_rates

logger = logging.getLogger(__name__)

class SimpleScheduler:
    """
    Simple scheduler class that generates a refinery schedule based on
    input data and constraints without optimization.
    """
    
    def __init__(self, input_data):
        """
        Initialize the SimpleScheduler with input data.
        
        Args:
            input_data (dict): Processed input data from data_loader
        """
        self.input_data = input_data
        self.plant_capacity = input_data["plant_details"]["capacity_bpd"]
        self.base_capacity = input_data["plant_details"]["base_crude_capacity_bpd"]
        self.crude_grades = input_data["crude_grades"]
        self.crude_pairings = input_data["pairings_dict"]
        self.opening_inventory = input_data["inventory_dict"]
        self.tanks = input_data["tanks_dict"]
        self.max_inventory = input_data["maximum_inventory"]["volume"]
        self.feedstock_program = input_data["feedstock_delivery_program"]
        self.margins = input_data["margin_dict"]
        self.time_of_travel = {item["route"]: item["days"] for item in input_data["time_of_travel_days"]}
        self.num_days = input_data["processing_dates"]["days"]
        
    def generate_schedule(self):
        """
        Generate a refinery schedule based on input data and constraints.
        
        Returns:
            dict: Schedule containing daily plan and vessel arrivals
        """
        logger.info("Generating simple schedule")
        
        # Initialize the schedule
        schedule = {
            "daily_plan": {},
            "vessel_arrivals": [],
            "held_vessels": []  # Track vessels that are held due to insufficient ullage
        }
        
        # Initialize inventory with opening inventory
        inventory = dict(self.opening_inventory)
        current_tanks = {name: dict(data) for name, data in self.tanks.items()}
        
        # Plan vessel arrivals based on LDRs
        planned_vessel_arrivals = self._plan_vessel_arrivals()
        
        # Keep track of held vessels that need to be checked on future days
        pending_vessels = []
        
        # Generate daily plan
        for day in range(1, self.num_days + 1):
            # Check if any vessels are planned to arrive on this day
            day_arrivals = [v for v in planned_vessel_arrivals if v["arrival_day"] == day]
            
            # Add any pending vessels that were held from previous days
            for vessel in pending_vessels:
                if vessel not in day_arrivals:  # Avoid duplicates
                    day_arrivals.append(vessel)
            
            # Reset pending vessels for this day
            pending_vessels = []
            actual_arrivals = []
            
            # Process each planned arrival and check if there's enough tank ullage
            for vessel in day_arrivals:
                can_berth = True
                vessel_allocations = []
                
                # Try to allocate each cargo to tanks and check if there's enough space
                for cargo in vessel["cargo"]:
                    grade = cargo["grade"]
                    volume = cargo["volume"]
                    
                    # Simulate allocation to check if there's enough ullage
                    allocation_results = self._simulate_tank_allocation(current_tanks, grade, volume)
                    
                    # If there's any overflow, the vessel can't berth
                    if any(alloc["tank"] == "OVERFLOW" for alloc in allocation_results):
                        can_berth = False
                        # Save allocation simulation for reporting
                        cargo["simulated_allocation"] = allocation_results
                    else:
                        vessel_allocations.append((cargo, allocation_results))
                
                # If all cargo can be accommodated, proceed with the vessel arrival
                if can_berth:
                    # Actually perform the allocations
                    for cargo, allocations in vessel_allocations:
                        grade = cargo["grade"]
                        volume = cargo["volume"]
                        
                        # Allocate cargo to tanks
                        allocation_results = self._allocate_to_tanks(current_tanks, grade, volume)
                        
                        # Update inventory
                        if grade not in inventory:
                            inventory[grade] = 0
                        inventory[grade] = inventory.get(grade, 0) + volume
                        
                        # Update vessel info with tank allocations
                        cargo["tank_allocation"] = allocation_results
                    
                    # Add to actual arrivals
                    vessel["actual_arrival_day"] = day
                    actual_arrivals.append(vessel)
                else:
                    # Check if this is a new hold or continued hold
                    if "original_arrival_day" not in vessel:
                        vessel["original_arrival_day"] = vessel["arrival_day"]
                        vessel["days_held"] = day - vessel["original_arrival_day"]
                    else:
                        vessel["days_held"] = day - vessel["original_arrival_day"]
                    
                    # Update vessel arrival day to check on the next day
                    vessel["arrival_day"] = day + 1
                    
                    # If we're within the simulation horizon, add to pending vessels for the next day
                    if vessel["arrival_day"] <= self.num_days:
                        pending_vessels.append(vessel)
                    else:
                        # If we've reached the end of the simulation horizon and the vessel is still held
                        vessel["held_reason"] = "Insufficient ullage until end of simulation horizon"
                        vessel["earliest_possible_day"] = "Beyond simulation horizon"
                        schedule["held_vessels"].append(vessel)
            
            # Update the schedule with the vessels that actually arrived
            schedule["vessel_arrivals"].extend(actual_arrivals)
            
            # Calculate processing rates based on inventory, blending rules, and constraints
            processing_rates, blending_details = calculate_processing_rates(
                inventory=inventory,
                pairings=self.crude_pairings,
                plant_capacity=self.plant_capacity,
                margins=self.margins
            )
            
            # Update inventory and tanks based on processing
            for grade, rate in processing_rates.items():
                # Update the overall inventory
                inventory[grade] = max(0, inventory[grade] - rate)
                
                # Update the tanks
                self._remove_from_tanks(current_tanks, grade, rate)
            
            # Check inventory total to ensure it doesn't exceed capacity
            total_inventory = sum(inventory.values())
            if total_inventory > self.max_inventory:
                logger.warning(f"Day {day}: Total inventory {total_inventory} exceeds maximum capacity {self.max_inventory}")
            
            # Store the daily plan
            schedule["daily_plan"][day] = {
                "processing_rates": processing_rates,
                "blending_details": blending_details,
                "inventory": sum(inventory.values()),
                "inventory_by_grade": dict(inventory),
                "tanks": {name: {"capacity": data["capacity"], 
                                 "contents": [dict(c) for c in data["contents"]]} 
                          for name, data in current_tanks.items()}
            }
        
        # Add any vessels still pending at the end of the simulation to the held_vessels list
        for vessel in pending_vessels:
            vessel["held_reason"] = "Insufficient ullage until end of simulation horizon"
            vessel["earliest_possible_day"] = "Beyond simulation horizon"
            schedule["held_vessels"].append(vessel)
        
        return schedule
    
    def _plan_vessel_arrivals(self):
        """
        Plan vessel arrivals based on LDRs in the feedstock program.
        
        Returns:
            list: List of vessel arrivals with cargoes
        """
        # Extract all parcels from the feedstock program
        parcels = []
        for feedstock in self.feedstock_program:
            grade = feedstock["grade"]
            for i, (ldr, size) in enumerate(zip(feedstock["processed_ldr"], feedstock["parcel_sizes_kb"])):
                parcels.append({
                    "grade": grade,
                    "volume": size,
                    "ldr": ldr,
                    "origin": next(g["origin"] for g in self.crude_grades if g["grade"] == grade)
                })
        
        # Sort parcels by earliest LDR start date
        parcels.sort(key=lambda p: p["ldr"]["start_day"])
        
        # Simple vessel assignment - each parcel gets its own vessel for now
        # In the vessel optimizer, these will be combined based on constraints
        vessels = []
        for parcel in parcels:
            # Pick the middle of the LDR range as the arrival date
            arrival_day = (parcel["ldr"]["start_day"] + parcel["ldr"]["end_day"]) // 2
            
            vessels.append({
                "arrival_day": arrival_day,
                "cargo": [
                    {
                        "grade": parcel["grade"],
                        "volume": parcel["volume"],
                        "origin": parcel["origin"]
                    }
                ],
                "ldr_text": parcel["ldr"]["ldr_text"]
            })
        
        return vessels
    
    def _allocate_to_tanks(self, tanks, grade, volume):
        """
        Allocate crude to tanks based on available space.
        
        Args:
            tanks (dict): Current tank state
            grade (str): Crude grade to allocate
            volume (float): Volume to allocate in kb
            
        Returns:
            list: List of allocations with tank name and volume
        """
        remaining_volume = volume
        allocations = []
        
        # First, try to allocate to tanks that already contain this grade
        for tank_name, tank in tanks.items():
            if remaining_volume <= 0:
                break
                
            # Check if tank already contains this grade
            has_grade = any(content["grade"] == grade for content in tank["contents"])
            
            if has_grade:
                # Calculate available space
                current_volume = sum(content["volume"] for content in tank["contents"])
                available_space = tank["capacity"] - current_volume
                
                if available_space > 0:
                    # Allocate as much as possible
                    allocated = min(remaining_volume, available_space)
                    
                    # Update tank contents
                    grade_in_tank = False
                    for content in tank["contents"]:
                        if content["grade"] == grade:
                            content["volume"] += allocated
                            grade_in_tank = True
                            break
                    
                    if not grade_in_tank:
                        tank["contents"].append({"grade": grade, "volume": allocated})
                    
                    # Record allocation
                    allocations.append({
                        "tank": tank_name,
                        "volume": allocated
                    })
                    
                    remaining_volume -= allocated
        
        # If there's still volume to allocate, try empty tanks
        if remaining_volume > 0:
            for tank_name, tank in tanks.items():
                if remaining_volume <= 0:
                    break
                    
                # Check if tank is empty
                is_empty = len(tank["contents"]) == 0
                
                if is_empty:
                    # Allocate as much as possible
                    allocated = min(remaining_volume, tank["capacity"])
                    
                    # Update tank contents
                    tank["contents"].append({"grade": grade, "volume": allocated})
                    
                    # Record allocation
                    allocations.append({
                        "tank": tank_name,
                        "volume": allocated
                    })
                    
                    remaining_volume -= allocated
        
        # If there's still volume to allocate, use any available space
        if remaining_volume > 0:
            for tank_name, tank in tanks.items():
                if remaining_volume <= 0:
                    break
                    
                # Calculate available space
                current_volume = sum(content["volume"] for content in tank["contents"])
                available_space = tank["capacity"] - current_volume
                
                if available_space > 0:
                    # Check if tank can accept this grade (already has it or is empty)
                    has_grade = any(content["grade"] == grade for content in tank["contents"])
                    is_empty = len(tank["contents"]) == 0
                    
                    if has_grade or is_empty:
                        # Allocate as much as possible
                        allocated = min(remaining_volume, available_space)
                        
                        # Update tank contents
                        grade_in_tank = False
                        for content in tank["contents"]:
                            if content["grade"] == grade:
                                content["volume"] += allocated
                                grade_in_tank = True
                                break
                        
                        if not grade_in_tank:
                            tank["contents"].append({"grade": grade, "volume": allocated})
                        
                        # Record allocation
                        allocations.append({
                            "tank": tank_name,
                            "volume": allocated
                        })
                        
                        remaining_volume -= allocated
        
        # Check if we couldn't allocate all the volume
        if remaining_volume > 0:
            logger.warning(f"Could not allocate {remaining_volume} kb of {grade} due to tank capacity constraints")
            allocations.append({
                "tank": "OVERFLOW",
                "volume": remaining_volume
            })
        
        return allocations
    
    def _remove_from_tanks(self, tanks, grade, volume):
        """
        Remove crude from tanks based on processing.
        
        Args:
            tanks (dict): Current tank state
            grade (str): Crude grade to remove
            volume (float): Volume to remove in kb
        """
        remaining_volume = volume
        
        # Sort tank contents by grade
        for tank_name, tank in tanks.items():
            if remaining_volume <= 0:
                break
                
            # Find contents with this grade
            for i, content in enumerate(tank["contents"]):
                if content["grade"] == grade:
                    # Remove as much as possible
                    removed = min(remaining_volume, content["volume"])
                    content["volume"] -= removed
                    
                    # If volume is now zero, remove the content entry
                    if content["volume"] <= 0:
                        tank["contents"].pop(i)
                    
                    remaining_volume -= removed
                    
                    # Break if we've removed enough
                    if remaining_volume <= 0:
                        break
        
        # Check if we couldn't remove all the volume
        if remaining_volume > 0:
            logger.warning(f"Could not remove {remaining_volume} kb of {grade} from tanks")
    
    def _simulate_tank_allocation(self, tanks, grade, volume):
        """
        Simulate allocation of crude to tanks to check if there's enough space
        without actually modifying the tank contents.
        
        Args:
            tanks (dict): Current tank state
            grade (str): Crude grade to allocate
            volume (float): Volume to allocate in kb
            
        Returns:
            list: List of allocations with tank name and volume
        """
        # Create a deep copy of tanks to avoid modifying the original
        tanks_copy = {}
        for tank_name, tank_data in tanks.items():
            tanks_copy[tank_name] = {
                "capacity": tank_data["capacity"],
                "contents": [dict(content) for content in tank_data["contents"]]
            }
        
        remaining_volume = volume
        allocations = []
        
        # First, try to allocate to tanks that already contain this grade
        for tank_name, tank in tanks_copy.items():
            if remaining_volume <= 0:
                break
                
            # Check if tank already contains this grade
            has_grade = any(content["grade"] == grade for content in tank["contents"])
            
            if has_grade:
                # Calculate available space
                current_volume = sum(content["volume"] for content in tank["contents"])
                available_space = tank["capacity"] - current_volume
                
                if available_space > 0:
                    # Allocate as much as possible
                    allocated = min(remaining_volume, available_space)
                    
                    # Record allocation
                    allocations.append({
                        "tank": tank_name,
                        "volume": allocated
                    })
                    
                    remaining_volume -= allocated
        
        # If there's still volume to allocate, try empty tanks
        if remaining_volume > 0:
            for tank_name, tank in tanks_copy.items():
                if remaining_volume <= 0:
                    break
                    
                # Check if tank is empty
                is_empty = len(tank["contents"]) == 0
                
                if is_empty:
                    # Allocate as much as possible
                    allocated = min(remaining_volume, tank["capacity"])
                    
                    # Record allocation
                    allocations.append({
                        "tank": tank_name,
                        "volume": allocated
                    })
                    
                    remaining_volume -= allocated
        
        # If there's still volume to allocate, use any available space
        if remaining_volume > 0:
            for tank_name, tank in tanks_copy.items():
                if remaining_volume <= 0:
                    break
                    
                # Calculate available space
                current_volume = sum(content["volume"] for content in tank["contents"])
                available_space = tank["capacity"] - current_volume
                
                if available_space > 0:
                    # Check if tank can accept this grade (already has it or is empty)
                    has_grade = any(content["grade"] == grade for content in tank["contents"])
                    is_empty = len(tank["contents"]) == 0
                    
                    if has_grade or is_empty:
                        # Allocate as much as possible
                        allocated = min(remaining_volume, available_space)
                        
                        # Record allocation
                        allocations.append({
                            "tank": tank_name,
                            "volume": allocated
                        })
                        
                        remaining_volume -= allocated
        
        # Check if we couldn't allocate all the volume
        if remaining_volume > 0:
            # Mark as overflow - this means there's not enough ullage
            allocations.append({
                "tank": "OVERFLOW",
                "volume": remaining_volume
            })
        
        return allocations