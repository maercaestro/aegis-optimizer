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
    Enhanced Vessel optimizer that can optimize for both vessel count and delivery dates.
    """
    
    def __init__(self, loading_data_path, target_delivery_dates=None):
        """
        Initialize the VesselOptimizer with loading date ranges and optional target dates.
        
        Args:
            loading_data_path (str): Path to the loading date ranges JSON file
            target_delivery_dates (dict, optional): Dict mapping grades to target arrival days
                                                   e.g. {"A": 5, "B": 12, "F": 20}
        """
        self.loading_data = self._load_loading_data(loading_data_path)
        self.loading_parcels = self.loading_data["loading_date_ranges"]
        self.vessel_constraints = self.loading_data["vessel_constraints"]
        self.travel_times = self.loading_data["travel_times"]
        self.destination = "Melaka"
        self.target_delivery_dates = target_delivery_dates or {}
        
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
    
    def optimize(self, prioritize_dates=True, max_penalty=1000000):
        """
        Optimize vessel allocation prioritizing target delivery dates.
        
        Args:
            prioritize_dates (bool): If True, prioritize meeting target dates over vessel count
            max_penalty (float): Maximum penalty for missing target dates (higher = stricter)
            
        Returns:
            dict: Optimized vessel allocation result
        """
        logger.info("Starting vessel optimization with target date priorities")
        
        # Generate all feasible combinations of parcels
        combinations = self._get_feasible_combinations()
        
        # Create the LP problem
        prob = pulp.LpProblem("Vessel_Optimization", pulp.LpMinimize)
        
        # Create binary variables for each combination
        use_combination = {}
        for i, combo in enumerate(combinations):
            use_combination[i] = pulp.LpVariable(f"use_combo_{i}", cat=pulp.LpBinary)
        
        # Create arrival day variables for each grade
        arrival_vars = {}
        for grade in self.target_delivery_dates.keys():
            arrival_vars[grade] = pulp.LpVariable(f"arrival_day_{grade}", 
                                                 lowBound=1, 
                                                 cat=pulp.LpInteger)
        
        # Create tardiness variables for each grade with a target date
        tardiness_vars = {}
        for grade, target_day in self.target_delivery_dates.items():
            tardiness_vars[grade] = pulp.LpVariable(f"tardiness_{grade}", 
                                                  lowBound=0, 
                                                  cat=pulp.LpInteger)
            
            # Tardiness = max(0, arrival_day - target_day)
            # Since we can't use max directly, we use these constraints:
            prob += tardiness_vars[grade] >= arrival_vars[grade] - target_day
            prob += tardiness_vars[grade] >= 0
        
        # Create vessel count variable
        vessel_count_var = pulp.LpVariable("vessel_count", lowBound=0, cat=pulp.LpInteger)
        prob += vessel_count_var == pulp.lpSum(use_combination[i] for i in range(len(combinations)))
        
        # Create over_limit variable for vessels beyond 5
        over_limit_var = pulp.LpVariable("over_limit", lowBound=0, cat=pulp.LpInteger)
        prob += over_limit_var >= vessel_count_var - 5
        prob += over_limit_var >= 0
        
        # Objective function: Minimize vessel count and tardiness penalties
        if prioritize_dates and self.target_delivery_dates:
            # Primary priority: meet target dates, secondary: minimize vessels
            prob += (max_penalty * pulp.lpSum(tardiness_vars.values()) + 
                   vessel_count_var + over_limit_var * 2)
        else:
            # Primary priority: minimize vessels, secondary: meet target dates if possible
            prob += (vessel_count_var + over_limit_var * 2 + 
                   pulp.lpSum(tardiness_vars.values()) / 100)
        
        # Constraint: Each parcel must be assigned to exactly one vessel
        for parcel in self.loading_parcels:
            prob += pulp.lpSum(use_combination[i] for i in range(len(combinations)) 
                               if parcel in combinations[i]) == 1, f"Assign_parcel_{parcel['id']}"
        
        # Constraint: Set arrival day for each grade based on vessel assignments
        for grade, target_day in self.target_delivery_dates.items():
            grade_parcels = [p for p in self.loading_parcels if p["grade"] == grade]
            
            if not grade_parcels:
                continue  # Skip if no parcels for this grade
            
            # For each grade with a target date, find its arrival day
            # This is a big-M constraint: if combo i contains this grade and is selected,
            # then the arrival day must be at least the calculated arrival day
            M = 100  # Big-M value (larger than any possible arrival day)
            
            for i, combo in enumerate(combinations):
                combo_parcels = [p for p in combo if p["grade"] == grade]
                if combo_parcels:
                    arrival_day = self._calculate_arrival_day(combo)
                    prob += arrival_vars[grade] <= arrival_day + M * (1 - use_combination[i])
                    prob += arrival_vars[grade] >= arrival_day - M * (1 - use_combination[i])
        
        # Solve the problem
        solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=120)
        prob.solve(solver)
        
        # Check if optimization was successful
        if pulp.LpStatus[prob.status] != 'Optimal':
            logger.warning(f"Optimization did not find an optimal solution. Status: {pulp.LpStatus[prob.status]}")
            return {"status": "failed", "message": f"Could not find optimal solution: {pulp.LpStatus[prob.status]}"}
        
        # Extract the results
        vessel_count = int(pulp.value(vessel_count_var))
        
        # Calculate cost with the new pricing structure
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
                
                # Create vessel object with target date info
                vessel = {
                    "cargo": combo,
                    "ldr": loading_range,
                    "loading_start": max_start,
                    "loading_end": min_end,
                    "arrival_day": arrival_day,
                    "meets_targets": self._check_meets_targets(combo, arrival_day)
                }
                vessels.append(vessel)
        
        # Sort vessels by arrival day
        vessels.sort(key=lambda v: v["arrival_day"])
        
        # Target date results
        target_date_results = {}
        for grade, target in self.target_delivery_dates.items():
            if grade in arrival_vars:
                arrival = int(pulp.value(arrival_vars[grade]))
                tardiness = int(pulp.value(tardiness_vars[grade]))
                target_date_results[grade] = {
                    "target_day": target,
                    "actual_arrival": arrival,
                    "tardiness": tardiness,
                    "status": "On time" if tardiness == 0 else f"Late by {tardiness} days"
                }
        
        # Create detailed result
        result = {
            "status": "optimal",
            "vessels": vessels,
            "vessel_count": vessel_count,
            "total_parcels": len(self.loading_parcels),
            "freight_cost": freight_cost,
            "target_date_results": target_date_results
        }
        
        return result
    
    def _check_meets_targets(self, combo, arrival_day):
        """Check if vessel arrival meets target dates for its cargo grades"""
        results = {}
        for parcel in combo:
            grade = parcel["grade"]
            if grade in self.target_delivery_dates:
                target = self.target_delivery_dates[grade]
                results[grade] = {
                    "target": target,
                    "actual": arrival_day,
                    "status": "On time" if arrival_day <= target else f"Late by {arrival_day - target} days"
                }
        return results
    
    def _calculate_freight_cost(self, vessel_count):
        """
        Calculate the freight cost based on the number of vessels.
        
        Args:
            vessel_count (int): Number of vessels
            
        Returns:
            float: Total freight cost
        """
        base_cost = self.vessel_constraints["freight_cost_usd"]
        free_vessels = 5  # First 5 vessels included in base cost
        
        if vessel_count <= free_vessels:
            return base_cost
        else:
            # $600,000 per vessel beyond 5
            additional_cost = 600000 * (vessel_count - free_vessels)
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