#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Linear Programming Optimizer for the Aegis Refinery Optimizer.
This module uses linear programming to optimize refinery operations.
"""

import json
import logging
import os
from datetime import datetime
import pulp
from copy import deepcopy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LPOptimizer:
    """
    Linear Programming Optimizer for refinery operations.
    Optimizes daily processing rates and blends to maximize throughput
    while satisfying operational constraints.
    """
    
    def __init__(self, schedule_file):
        """
        Initialize the LP optimizer with a schedule file.
        
        Args:
            schedule_file (str): Path to the schedule output JSON file
        """
        self.schedule_file = schedule_file
        self.schedule = self._load_schedule()
        self.grades = self._get_available_grades()
        logger.info(f"Initialized LP Optimizer with {len(self.grades)} grades: {', '.join(self.grades)}")
        
    def _load_schedule(self):
        """Load the schedule from JSON file."""
        try:
            with open(self.schedule_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading schedule: {e}")
            raise
            
    def _get_available_grades(self):
        """Extract all available crude grades from the schedule."""
        grades = set()
        
        # Extract grades from any daily plan
        for day, day_plan in self.schedule["daily_plan"].items():
            for grade in day_plan["processing_rates"].keys():
                grades.add(grade)
                
        return sorted(list(grades))
    
    def _get_initial_inventory(self):
        """Get the initial inventory from the first day of the schedule."""
        first_day = min(int(day) for day in self.schedule["daily_plan"].keys())
        return self.schedule["daily_plan"][str(first_day)]["inventory_by_grade"]
    
    def _get_vessel_arrivals_by_day(self):
        """Organize vessel arrivals by day for easier processing."""
        arrivals_by_day = {}
        
        for vessel in self.schedule["vessel_arrivals"]:
            day = vessel["arrival_day"]
            
            if day not in arrivals_by_day:
                arrivals_by_day[day] = []
                
            for cargo in vessel["cargo"]:
                arrivals_by_day.setdefault(day, []).append({
                    "grade": cargo["grade"],
                    "volume": cargo["volume"]
                })
                
        return arrivals_by_day
        
    def _get_possible_recipes(self, day):
        """
        Get possible recipes for a given day based on historic blending patterns.
        
        Args:
            day (int): Day number
            
        Returns:
            list: List of recipe dictionaries
        """
        recipes = []
        
        # Add solo recipes for each grade
        for grade in self.grades:
            recipes.append({
                "primary_grade": grade,
                "secondary_grade": None,
                "ratio": [1.0, 0.0],
                "capacity_limit": 95.0  # Default max capacity
            })
        
        # Add standard blended recipes from existing data
        day_str = str(day)
        if day_str in self.schedule["daily_plan"]:
            blend_details = self.schedule["daily_plan"][day_str].get("blending_details", [])
            
            for blend in blend_details:
                primary_grade = blend.get("primary_grade")
                secondary_grade = blend.get("secondary_grade")
                
                if primary_grade and secondary_grade:
                    # Parse ratio from string like "0.60:0.40"
                    ratio_str = blend.get("ratio", "1.00:0.00")
                    ratio_parts = ratio_str.split(":")
                    ratio = [float(ratio_parts[0]), float(ratio_parts[1])]
                    
                    recipes.append({
                        "primary_grade": primary_grade,
                        "secondary_grade": secondary_grade,
                        "ratio": ratio,
                        "capacity_limit": blend.get("capacity_limit", 95.0)
                    })
        
        return recipes
    
    def create_optimization_model(self, min_threshold=80.0, max_daily_change=10.0):
        """
        Create a PuLP linear programming model with strict recipe constraints.
        
        Args:
            min_threshold (float): Minimum daily processing rate threshold
            max_daily_change (float): Maximum allowed change in processing rate between days
            
        Returns:
            tuple: (model, variables_dict) - The PuLP model and dictionary of variables
        """
        # Initialize model
        model = pulp.LpProblem("Refinery_Optimization", pulp.LpMaximize)
        
        # Get days in ascending order
        days = sorted([int(day) for day in self.schedule["daily_plan"].keys()])
        
        # Get all possible recipes for each day
        possible_recipes = {}
        for day in days:
            possible_recipes[day] = self._get_possible_recipes(day)
        
        # Create variables
        recipe_vars = {}  # recipe_vars[day][recipe_idx] - binary variable for recipe selection
        recipe_rate_vars = {}  # recipe_rate_vars[day][recipe_idx] - continuous variable for recipe rate
        processing_vars = {}  # processing_vars[day][grade] - derived from recipe selection
        total_processing_vars = {}  # total_processing_vars[day]
        inventory_vars = {}  # inventory_vars[day][grade]
        
        # Create recipe selection variables
        for day in days:
            recipe_vars[day] = {}
            recipe_rate_vars[day] = {}
            processing_vars[day] = {}
            inventory_vars[day] = {}
            
            # Total processing variable for the day
            total_processing_vars[day] = pulp.LpVariable(
                f"total_processing_day_{day}", 
                lowBound=0, 
                cat=pulp.LpContinuous
            )
            
            # Initialize processing vars for all grades
            for grade in self.grades:
                processing_vars[day][grade] = pulp.LpVariable(
                    f"process_{grade}_day_{day}", 
                    lowBound=0, 
                    cat=pulp.LpContinuous
                )
                
                # Inventory variable for each grade
                inventory_vars[day][grade] = pulp.LpVariable(
                    f"inventory_{grade}_day_{day}", 
                    lowBound=0, 
                    cat=pulp.LpContinuous
                )
        
            # Create recipe selection variables
            for i, recipe in enumerate(possible_recipes[day]):
                # Binary variable for recipe selection (1 if selected, 0 otherwise)
                recipe_vars[day][i] = pulp.LpVariable(
                    f"recipe_{i}_day_{day}", 
                    cat=pulp.LpBinary
                )
                
                # Continuous variable for recipe processing rate
                recipe_rate_vars[day][i] = pulp.LpVariable(
                    f"recipe_rate_{i}_day_{day}", 
                    lowBound=0,
                    upBound=recipe["capacity_limit"],
                    cat=pulp.LpContinuous
                )
    
        # Add constraints
    
        # 1. Only one recipe can be selected per day
        for day in days:
            model += pulp.lpSum(recipe_vars[day].values()) == 1, f"one_recipe_day_{day}"
    
        # 2. Recipe rate is zero if recipe not selected
        for day in days:
            for i, recipe in enumerate(possible_recipes[day]):
                # If recipe not selected (recipe_vars[day][i] = 0), then rate must be 0
                model += recipe_rate_vars[day][i] <= recipe["capacity_limit"] * recipe_vars[day][i]
    
        # 3. Processing rates are determined by recipe selection and recipe rates
        for day in days:
            for grade in self.grades:
                # Initialize a list to collect terms for this grade from all recipes
                grade_terms = []
                
                for i, recipe in enumerate(possible_recipes[day]):
                    # Check if this grade is used in this recipe
                    if recipe["primary_grade"] == grade:
                        # If this is a solo recipe (no secondary grade)
                        if recipe["secondary_grade"] is None:
                            # All the recipe rate goes to this grade
                            grade_terms.append(recipe_rate_vars[day][i])
                        else:
                            # Only primary proportion of rate goes to this grade
                            primary_ratio = recipe["ratio"][0]
                            grade_terms.append(primary_ratio * recipe_rate_vars[day][i])
                    
                    # Check if this grade is the secondary in this recipe
                    elif recipe["secondary_grade"] == grade:
                        secondary_ratio = recipe["ratio"][1]
                        grade_terms.append(secondary_ratio * recipe_rate_vars[day][i])
                
                # Processing rate for this grade equals sum of contributions from recipes
                if grade_terms:
                    model += processing_vars[day][grade] == pulp.lpSum(grade_terms)
                else:
                    model += processing_vars[day][grade] == 0
    
        # 4. Total processing rate for each day
        for day in days:
            model += total_processing_vars[day] == pulp.lpSum(processing_vars[day].values())
    
        # 5. Minimum processing threshold
        for day in days:
            model += total_processing_vars[day] >= min_threshold
    
        # 6. Maximum daily rate change
        for i in range(1, len(days)):
            day = days[i]
            prev_day = days[i-1]
            model += total_processing_vars[day] - total_processing_vars[prev_day] <= max_daily_change
            model += total_processing_vars[prev_day] - total_processing_vars[day] <= max_daily_change
    
        # 7. Inventory balance constraints
        # Get initial inventory and vessel arrivals
        initial_inventory = self._get_initial_inventory()
        vessel_arrivals = self._get_vessel_arrivals_by_day()
        
        # Set initial inventory for first day
        for grade in self.grades:
            init_amount = initial_inventory.get(grade, 0)
            # Add any vessel arrivals on first day
            if days[0] in vessel_arrivals:
                for cargo in vessel_arrivals[days[0]]:
                    if cargo["grade"] == grade:
                        init_amount += cargo["volume"]
        
            # Initial inventory minus processing equals end of day inventory
            model += inventory_vars[days[0]][grade] == init_amount - processing_vars[days[0]][grade]
    
        # For subsequent days
        for i in range(1, len(days)):
            day = days[i]
            prev_day = days[i-1]
            
            for grade in self.grades:
                # Start with previous day's inventory
                arrival_amount = 0
                
                # Add any vessel arrivals on this day
                if day in vessel_arrivals:
                    for cargo in vessel_arrivals[day]:
                        if cargo["grade"] == grade:
                            arrival_amount += cargo["volume"]
                
                # Inventory balance: previous day inventory - processing + arrivals
                model += (
                    inventory_vars[day][grade] == 
                    inventory_vars[prev_day][grade] - processing_vars[day][grade] + arrival_amount
                )
    
        # 8. Processing cannot exceed available inventory
        for day in days:
            for grade in self.grades:
                if day == days[0]:
                    available = initial_inventory.get(grade, 0)
                    # Add any vessel arrivals on first day
                    if days[0] in vessel_arrivals:
                        for cargo in vessel_arrivals[days[0]]:
                            if cargo["grade"] == grade:
                                available += cargo["volume"]
                else:
                    prev_day = days[days.index(day)-1]
                    available = inventory_vars[prev_day][grade]
                
                model += processing_vars[day][grade] <= available
    
        # Objective function: Maximize total throughput
        model += pulp.lpSum(total_processing_vars.values())
        
        variables = {
            "recipe": recipe_vars,
            "recipe_rate": recipe_rate_vars,
            "processing": processing_vars,
            "inventory": inventory_vars,
            "total_processing": total_processing_vars
        }
        
        return model, variables
    
    def optimize(self, min_threshold=80.0, max_daily_change=10.0):
        """
        Optimize the refinery operations using linear programming.
        
        Args:
            min_threshold (float): Minimum daily processing rate threshold
            max_daily_change (float): Maximum allowed change in processing rate between days
            
        Returns:
            dict: Optimized schedule
        """
        logger.info("Starting LP optimization...")
        
        # Create the model
        model, variables = self.create_optimization_model(min_threshold, max_daily_change)
        
        # Solve the model
        solver = pulp.getSolver('PULP_CBC_CMD', msg=True, timeLimit=120)
        model.solve(solver)
        
        if model.status != pulp.LpStatusOptimal:
            logger.warning(f"Optimization did not find an optimal solution. Status: {pulp.LpStatus[model.status]}")
            return self.schedule  # Return original schedule if optimization fails
        
        logger.info(f"Optimization successful. Objective value: {pulp.value(model.objective)}")
        
        # Create optimized schedule
        optimized_schedule = deepcopy(self.schedule)
        days = sorted([int(day) for day in optimized_schedule["daily_plan"].keys()])
        possible_recipes = {}
        
        # Get all possible recipes for each day
        for day in days:
            possible_recipes[day] = self._get_possible_recipes(day)
    
        # Update processing rates and inventory
        for day in days:
            day_str = str(day)
            
            # Clear existing processing rates and set all to 0
            for grade in self.grades:
                optimized_schedule["daily_plan"][day_str]["processing_rates"][grade] = 0
        
            # Find which recipe was selected for this day
            selected_recipe_idx = None
            for i in range(len(possible_recipes[day])):
                if pulp.value(variables["recipe"][day][i]) > 0.5:  # Binary variable is approximately 1
                    selected_recipe_idx = i
                    break
        
            if selected_recipe_idx is not None:
                recipe = possible_recipes[day][selected_recipe_idx]
                recipe_rate = pulp.value(variables["recipe_rate"][day][selected_recipe_idx])
                
                # Update processing rates based on the selected recipe
                primary_grade = recipe["primary_grade"]
                secondary_grade = recipe["secondary_grade"]
                
                if secondary_grade is None:  # Solo recipe
                    optimized_schedule["daily_plan"][day_str]["processing_rates"][primary_grade] = recipe_rate
                    
                    # Update blending details
                    optimized_schedule["daily_plan"][day_str]["blending_details"] = [{
                        "primary_grade": primary_grade,
                        "secondary_grade": None,
                        "primary_rate": recipe_rate,
                        "secondary_rate": 0,
                        "total_rate": recipe_rate,
                        "ratio": "1.00:0.00",
                        "capacity_used": recipe_rate,
                        "capacity_limit": recipe["capacity_limit"]
                    }]
                else:  # Blended recipe
                    ratio = recipe["ratio"]
                    primary_rate = ratio[0] * recipe_rate
                    secondary_rate = ratio[1] * recipe_rate
                    
                    optimized_schedule["daily_plan"][day_str]["processing_rates"][primary_grade] = primary_rate
                    optimized_schedule["daily_plan"][day_str]["processing_rates"][secondary_grade] = secondary_rate
                    
                    # Update blending details
                    optimized_schedule["daily_plan"][day_str]["blending_details"] = [{
                        "primary_grade": primary_grade,
                        "secondary_grade": secondary_grade,
                        "primary_rate": primary_rate,
                        "secondary_rate": secondary_rate,
                        "total_rate": recipe_rate,
                        "ratio": f"{ratio[0]:.2f}:{ratio[1]:.2f}",
                        "capacity_used": recipe_rate,
                        "capacity_limit": recipe["capacity_limit"]
                    }]
        
            # Update total inventory
            total_inventory = pulp.value(pulp.lpSum(variables["inventory"][day].values()))
            optimized_schedule["daily_plan"][day_str]["inventory"] = total_inventory
            
            # Update inventory by grade
            for grade in self.grades:
                inventory = pulp.value(variables["inventory"][day][grade])
                if inventory > 0.01:  # Only include non-zero inventory
                    optimized_schedule["daily_plan"][day_str]["inventory_by_grade"][grade] = inventory
                else:
                    optimized_schedule["daily_plan"][day_str]["inventory_by_grade"][grade] = 0
    
        return optimized_schedule
    
    def save_optimized_schedule(self, output_file=None):
        """
        Save the LP optimized schedule to a file.
        
        Args:
            output_file (str, optional): Output file path. If None, a default name is generated.
            
        Returns:
            str: Path to the saved file
        """
        optimized_schedule = self.optimize()
        
        # Generate timestamped output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if not output_file:
            # Generate output filename based on input filename
            output_file = f"data/schedule_output_{timestamp}_lp_optimized.json"
            
        # Fixed output file (always overwritten with latest)
        fixed_output_file = "data/latest_schedule_output_lp_optimized.json"
            
        # Add optimization metadata
        optimized_schedule["lp_optimization"] = {
            "optimized_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "objective_value": "maximize_throughput"
        }
        
        # Save to both files
        with open(output_file, 'w') as f:
            json.dump(optimized_schedule, f, indent=2)
            
        # Also save to fixed filename (will overwrite any existing file)
        with open(fixed_output_file, 'w') as f:
            json.dump(optimized_schedule, f, indent=2)
            
        logger.info(f"LP Optimized schedule saved to {output_file} and {fixed_output_file}")
        return output_file


def main():
    """Main function to run the optimizer."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Linear Programming Optimizer for Refinery Operations')
    parser.add_argument('schedule_file', help='Path to the schedule JSON file')
    parser.add_argument('--threshold', type=float, default=80.0, 
                        help='Minimum desired daily processing rate (default: 80.0)')
    parser.add_argument('--max-change', type=float, default=10.0,
                        help='Maximum allowed daily rate change (default: 10.0)')
    parser.add_argument('--output', help='Output file path (optional)')
    
    args = parser.parse_args()
    
    optimizer = LPOptimizer(args.schedule_file)
    optimizer.save_optimized_schedule(args.output)
    
    
if __name__ == "__main__":
    main()