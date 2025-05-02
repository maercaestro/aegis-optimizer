#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vessel optimizer module for the Aegis Refinery Optimizer.
Uses linear programming to optimize vessel allocation and arrival scheduling.
"""

import json
import logging
import math
import pulp
from datetime import datetime
from itertools import combinations

logger = logging.getLogger(__name__)

class VesselOptimizer:
    """
    Vessel optimizer class that handles the assignment of cargoes to vessels
    based on loading date ranges, vessel constraints, and travel times.
    Uses linear programming for optimization.
    """
    
    def __init__(self, loading_data_path):
        """
        Initialize the VesselOptimizer with loading date ranges data.
        
        Args:
            loading_data_path (str): Path to the loading date ranges JSON file
        """
        self.loading_data = self._load_loading_data(loading_data_path)
        self.loading_parcels = self.loading_data["loading_date_ranges"]
        self.vessel_constraints = self.loading_data["vessel_constraints"]
        self.travel_times = self.loading_data["travel_times"]
        self.destination = "Melaka"  # Destination is always Melaka
        
        # Preprocess parcels for optimization
        self._preprocess_parcels()
        
    def _load_loading_data(self, file_path):
        """
        Load loading date ranges data from JSON file.
        
        Args:
            file_path (str): Path to the loading date ranges JSON file
            
        Returns:
            dict: Loaded loading date ranges data
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Error loading loading date ranges data: {e}")
            raise
    
    def _parse_date_range(self, ldr):
        """
        Parse loading date range string into start and end dates.
        
        Args:
            ldr (str): Loading date range string (e.g., "1-3 Oct")
            
        Returns:
            tuple: (start_day, end_day) as integers
        """
        parts = ldr.split()
        days = parts[0].split("-")
        start_day = int(days[0])
        end_day = int(days[1])
        return start_day, end_day
    
    def _preprocess_parcels(self):
        """Preprocess parcels to include calculated fields needed for optimization."""
        for i, parcel in enumerate(self.loading_parcels):
            # Add unique parcel ID
            parcel["id"] = f"parcel_{i+1}"
            
            # Parse LDR
            start_day, end_day = self._parse_date_range(parcel["ldr"])
            parcel["start_day"] = start_day
            parcel["end_day"] = end_day
            
            # Calculate travel time to Melaka
            route = f"{parcel['origin']} to {self.destination}"
            travel_time = self.travel_times.get(route, 2)  # Default to 2 days if route not found
            parcel["travel_time"] = travel_time
            
            # Calculate earliest and latest arrival days
            parcel["earliest_arrival"] = start_day + math.ceil(travel_time)
            parcel["latest_arrival"] = end_day + math.ceil(travel_time)
        
        # Sort parcels by earliest arrival day
        self.loading_parcels.sort(key=lambda p: p["earliest_arrival"])
    
    def _get_feasible_combinations(self):
        """
        Generate all feasible cargo combinations for vessels.
        
        Returns:
            list: List of feasible cargo combinations
        """
        feasible_combinations = []
        
        # Add single-parcel options (always feasible)
        for parcel in self.loading_parcels:
            feasible_combinations.append([parcel])
        
        # Try combining 2 parcels
        for combo in combinations(self.loading_parcels, 2):
            if self._is_feasible_combination(list(combo)):
                feasible_combinations.append(list(combo))
        
        # Try combining 3 parcels
        for combo in combinations(self.loading_parcels, 3):
            if self._is_feasible_combination(list(combo)):
                feasible_combinations.append(list(combo))
        
        logger.info(f"Generated {len(feasible_combinations)} feasible cargo combinations")
        return feasible_combinations
    
    def _is_feasible_combination(self, parcels):
        """
        Check if a combination of parcels is feasible.
        
        Args:
            parcels (list): List of parcel dictionaries
            
        Returns:
            bool: True if the combination is feasible, False otherwise
        """
        # Check volume constraint
        total_volume = sum(parcel["volume_kb"] for parcel in parcels)
        
        # Get number of unique grades
        grades = set(parcel["grade"] for parcel in parcels)
        num_grades = len(grades)
        
        # Check volume limits based on number of grades
        if num_grades == 2:
            max_volume = self.vessel_constraints["max_volume_per_vessel"]["two_grades"]
            if total_volume > max_volume:
                return False
        elif num_grades == 3:
            max_volume = self.vessel_constraints["max_volume_per_vessel"]["three_grades"]
            if total_volume > max_volume:
                return False
        elif num_grades > 3:
            # More than 3 grades not allowed
            return False
        
        # Check if LDRs overlap
        start_days = [parcel["start_day"] for parcel in parcels]
        end_days = [parcel["end_day"] for parcel in parcels]
        
        max_start = max(start_days)
        min_end = min(end_days)
        
        if max_start > min_end:
            return False
        
        return True
    
    def _calculate_arrival_day(self, parcels):
        """
        Calculate the earliest possible arrival day for a combination of parcels.
        
        Args:
            parcels (list): List of parcel dictionaries
            
        Returns:
            int: Earliest possible arrival day at Melaka
        """
        # Find the latest loading start day among all parcels
        latest_start = max(parcel["start_day"] for parcel in parcels)
        
        # Find the maximum travel time from any origin
        max_travel_time = max(parcel["travel_time"] for parcel in parcels)
        
        # Calculate arrival day (loading day + travel time, rounded up)
        return latest_start + math.ceil(max_travel_time)
    
    def optimize(self):
        """
        Optimize vessel allocation using linear programming.
        
        Returns:
            dict: Optimized vessel allocation result
        """
        logger.info("Starting vessel optimization with linear programming")
        
        # Generate all feasible combinations of parcels
        combinations = self._get_feasible_combinations()
        
        # Create the LP problem
        prob = pulp.LpProblem("Vessel_Optimization", pulp.LpMinimize)
        
        # Create binary variables for each combination
        use_combination = {}
        for i, combo in enumerate(combinations):
            use_combination[i] = pulp.LpVariable(f"use_combo_{i}", cat=pulp.LpBinary)
        
        # Objective: Minimize the number of vessels
        prob += pulp.lpSum(use_combination[i] for i in range(len(combinations)))
        
        # Constraint: Each parcel must be assigned to exactly one vessel
        for parcel in self.loading_parcels:
            prob += pulp.lpSum(use_combination[i] for i in range(len(combinations)) 
                               if parcel in combinations[i]) == 1, f"Assign_parcel_{parcel['id']}"
        
        # Add constraint for maximum number of deliveries per month
        max_deliveries = self.vessel_constraints["max_delivery_per_month"]
        prob += pulp.lpSum(use_combination[i] for i in range(len(combinations))) <= max_deliveries, "Max_deliveries"
        
        # Solve the problem
        solver = pulp.PULP_CBC_CMD(msg=False)
        prob.solve(solver)
        
        # Check if optimization was successful
        if pulp.LpStatus[prob.status] != 'Optimal':
            logger.warning(f"Optimization did not find an optimal solution. Status: {pulp.LpStatus[prob.status]}")
            return {"status": "failed", "message": f"Could not find optimal solution: {pulp.LpStatus[prob.status]}"}
        
        # Extract the results
        vessel_count = int(sum(use_combination[i].value() for i in range(len(combinations))))
        
        # Calculate cost
        freight_cost = self._calculate_freight_cost(vessel_count)
        
        # Construct vessels from selected combinations
        vessels = []
        for i in range(len(combinations)):
            if use_combination[i].value() > 0.5:  # Selected combination
                combo = combinations[i]
                
                # Calculate loading day range for the vessel
                max_start = max(parcel["start_day"] for parcel in combo)
                min_end = min(parcel["end_day"] for parcel in combo)
                loading_range = f"{max_start}-{min_end} Oct"
                
                # Calculate arrival day at Melaka
                arrival_day = self._calculate_arrival_day(combo)
                
                # Create vessel object
                vessel = {
                    "cargo": combo,
                    "ldr": loading_range,
                    "loading_start": max_start,
                    "loading_end": min_end,
                    "arrival_day": arrival_day
                }
                vessels.append(vessel)
        
        # Sort vessels by arrival day
        vessels.sort(key=lambda v: v["arrival_day"])
        
        # Create detailed result
        result = {
            "status": "optimal",
            "vessels": vessels,
            "vessel_count": vessel_count,
            "total_parcels": len(self.loading_parcels),
            "freight_cost": freight_cost
        }
        
        logger.info(f"Vessel optimization complete: {vessel_count} vessels, cost ${freight_cost:,.2f}")
        return result
    
    def _calculate_freight_cost(self, vessel_count):
        """
        Calculate the freight cost based on the number of vessels.
        
        Args:
            vessel_count (int): Number of vessels
            
        Returns:
            float: Total freight cost
        """
        base_cost = self.vessel_constraints["freight_cost_usd"]
        free_vessels = 5  # Based on freight_note: no additional cost up to 5 deliveries
        
        if vessel_count <= free_vessels:
            return base_cost
        else:
            # Calculate additional cost beyond free vessels
            additional_cost = base_cost * (vessel_count - free_vessels) / free_vessels
            return base_cost + additional_cost
    
    def format_vessels_for_scheduler(self, optimized_result):
        """
        Format the optimized vessels for use with the scheduler.
        
        Args:
            optimized_result (dict): Result from optimize()
            
        Returns:
            list: List of vessels in the format expected by the scheduler
        """
        vessels = []
        
        for vessel in optimized_result["vessels"]:
            # Format cargo
            cargo = []
            for parcel in vessel["cargo"]:
                cargo.append({
                    "grade": parcel["grade"],
                    "volume": parcel["volume_kb"],
                    "origin": parcel["origin"]
                })
            
            # Create vessel object for scheduler
            scheduler_vessel = {
                "arrival_day": vessel["arrival_day"],
                "cargo": cargo,
                "ldr_text": vessel["ldr"]
            }
            vessels.append(scheduler_vessel)
        
        return vessels


if __name__ == "__main__":
    # Set up logging for standalone testing
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Test the optimizer
    optimizer = VesselOptimizer("data/loading_date_ranges.json")
    result = optimizer.optimize()
    
    print(f"\nOptimization Results:")
    print(f"Number of vessels: {result['vessel_count']}")
    print(f"Total freight cost: ${result['freight_cost']:,.2f}")
    
    print("\nDetailed vessel allocation:")
    for i, vessel in enumerate(result["vessels"]):
        print(f"\nVessel {i+1}:")
        print(f"  Loading window: {vessel['ldr']}")
        print(f"  Arrival day at Melaka: {vessel['arrival_day']}")
        print("  Cargo:")
        for parcel in vessel["cargo"]:
            print(f"    {parcel['grade']}: {parcel['volume_kb']} kb from {parcel['origin']}")