#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Daily Rate Optimizer for the Aegis Refinery Optimizer.
This script optimizes daily processing rates to maintain a minimum rate threshold.
"""

import json
import argparse
import logging
import os
from datetime import datetime
from copy import deepcopy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DailyRateOptimizer:
    """
    Class to optimize daily processing rates by redistributing volume 
    from previous days to maintain a minimum threshold.
    """
    
    def __init__(self, schedule_file, min_threshold=85.0):
        """
        Initialize the optimizer with a schedule file.
        
        Args:
            schedule_file (str): Path to the schedule output JSON file
            min_threshold (float): Minimum desired daily processing rate
        """
        self.schedule_file = schedule_file
        self.min_threshold = min_threshold
        self.schedule = self._load_schedule()
        
    def _load_schedule(self):
        """Load the schedule from JSON file."""
        try:
            with open(self.schedule_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading schedule: {e}")
            raise
            
    def _get_total_daily_rate(self, day):
        """
        Calculate the total processing rate for a given day.
        
        Args:
            day (str): Day number as string
            
        Returns:
            float: Total processing rate
        """
        if day not in self.schedule["daily_plan"]:
            return 0.0
            
        rates = self.schedule["daily_plan"][day]["processing_rates"]
        return sum(rates.values())
        
    def _can_borrow_from_previous_day(self, day, prev_day):
        """
        Check if volume can be borrowed from the previous day.
        
        Args:
            day (str): Current day number as string
            prev_day (str): Previous day number as string
            
        Returns:
            bool: True if borrowing is possible
        """
        if prev_day not in self.schedule["daily_plan"]:
            return False
            
        # Check if previous day has enough volume to borrow
        prev_day_rate = self._get_total_daily_rate(prev_day)
        current_day_rate = self._get_total_daily_rate(day)
        
        # Only borrow if previous day has more than threshold + 10
        return prev_day_rate > self.min_threshold + 10 and current_day_rate < self.min_threshold
        
    def _find_grade_to_borrow(self, day, prev_day):
        """
        Find the best crude grade to borrow from previous day.
        
        Args:
            day (str): Current day number as string
            prev_day (str): Previous day number as string
            
        Returns:
            tuple: (grade, volume_to_borrow)
        """
        prev_day_rates = self.schedule["daily_plan"][prev_day]["processing_rates"]
        day_rates = self.schedule["daily_plan"][day]["processing_rates"]
        
        prev_day_inventory = self.schedule["daily_plan"][prev_day]["inventory_by_grade"]
        
        # Find grades processed on the previous day that have significant volume
        potential_grades = []
        
        for grade, rate in prev_day_rates.items():
            # Skip grades with minimal processing
            if rate < 5.0:
                continue
                
            # Check if this grade was also processed on the current day
            # This makes transfer easier as the blending recipe already exists
            current_rate = day_rates.get(grade, 0)
            inventory = prev_day_inventory.get(grade, 0)
            
            if current_rate > 0:
                priority = 2  # Higher priority if already processed
            else:
                priority = 1
                
            potential_grades.append((grade, rate, priority, inventory))
        
        # Sort by priority (higher first) and then by rate (higher first)
        potential_grades.sort(key=lambda x: (x[2], x[1]), reverse=True)
        
        if not potential_grades:
            return None, 0
            
        # Select best grade to borrow
        selected_grade = potential_grades[0][0]
        
        # Calculate how much volume to borrow
        current_day_rate = self._get_total_daily_rate(day)
        shortfall = self.min_threshold - current_day_rate
        
        # Don't take more than 30% from previous day's processing of this grade
        max_borrow = potential_grades[0][1] * 0.3
        
        # Borrow enough to reach the minimum threshold, but not more than max allowed
        volume_to_borrow = min(shortfall, max_borrow)
        
        return selected_grade, volume_to_borrow
        
    def _adjust_blending_details(self, day, grade, added_volume):
        """
        Adjust the blending details for a day when adding volume.
        
        Args:
            day (str): Day number as string
            grade (str): Crude grade
            added_volume (float): Volume added to processing
            
        Returns:
            list: Updated blending details
        """
        blending_details = deepcopy(self.schedule["daily_plan"][day]["blending_details"])
        
        # Check if there's an existing blend for this grade
        found = False
        for blend in blending_details:
            if blend.get("primary_grade") == grade:
                # Update the existing blend
                blend["primary_rate"] += added_volume
                blend["total_rate"] += added_volume
                blend["capacity_used"] += added_volume
                found = True
                break
            elif blend.get("secondary_grade") == grade:
                # Update the existing blend where this grade is secondary
                blend["secondary_rate"] += added_volume
                blend["total_rate"] += added_volume
                blend["capacity_used"] += added_volume
                found = True
                break
                
        # If no existing blend found, add a new solo blend
        if not found:
            new_blend = {
                "primary_grade": grade,
                "secondary_grade": None,
                "primary_rate": added_volume,
                "secondary_rate": 0,
                "total_rate": added_volume,
                "ratio": "1.00:0.00",
                "capacity_used": added_volume,
                "capacity_limit": 95.0  # Default limit
            }
            blending_details.append(new_blend)
            
        return blending_details
        
    def optimize(self):
        """
        Optimize the daily processing rates to ensure minimum threshold is met.
        
        Returns:
            dict: Optimized schedule
        """
        # Make a deep copy to avoid modifying the original
        optimized_schedule = deepcopy(self.schedule)
        
        # Get all days in ascending order
        days = sorted([int(day) for day in optimized_schedule["daily_plan"].keys()])
        
        changes_made = 0
        
        # Process days from day 2 onwards (since we need a previous day)
        for i in range(1, len(days)):
            current_day = str(days[i])
            prev_day = str(days[i-1])
            
            current_rate = self._get_total_daily_rate(current_day)
            logger.info(f"Day {current_day}: Current total rate = {current_rate:.2f}")
            
            # Check if rate is below threshold
            if current_rate < self.min_threshold:
                # Check if we can borrow from previous day
                if self._can_borrow_from_previous_day(current_day, prev_day):
                    grade, volume = self._find_grade_to_borrow(current_day, prev_day)
                    
                    if grade and volume > 0:
                        logger.info(f"Borrowing {volume:.2f} of {grade} from day {prev_day} to day {current_day}")
                        
                        # Adjust processing rates for current day
                        optimized_schedule["daily_plan"][current_day]["processing_rates"][grade] = \
                            optimized_schedule["daily_plan"][current_day]["processing_rates"].get(grade, 0) + volume
                            
                        # Adjust processing rates for previous day
                        optimized_schedule["daily_plan"][prev_day]["processing_rates"][grade] -= volume
                        
                        # Update blending details
                        optimized_schedule["daily_plan"][current_day]["blending_details"] = \
                            self._adjust_blending_details(current_day, grade, volume)
                            
                        # Update total inventory for both days
                        # (note: detailed inventory adjustments would require more complex logic)
                        new_prev_total = sum(optimized_schedule["daily_plan"][prev_day]["processing_rates"].values())
                        new_current_total = sum(optimized_schedule["daily_plan"][current_day]["processing_rates"].values())
                        
                        optimized_schedule["daily_plan"][prev_day]["inventory"] += volume
                        optimized_schedule["daily_plan"][current_day]["inventory"] -= volume
                        
                        logger.info(f"Day {prev_day}: Adjusted rate = {new_prev_total:.2f}")
                        logger.info(f"Day {current_day}: Adjusted rate = {new_current_total:.2f}")
                        
                        changes_made += 1
                    else:
                        logger.warning(f"Couldn't find suitable grade to borrow for day {current_day}")
                else:
                    logger.warning(f"Cannot borrow from day {prev_day} for day {current_day}")
                    
        logger.info(f"Optimization complete. Made {changes_made} adjustments")
        return optimized_schedule
        
    def save_optimized_schedule(self, output_file=None):
        """
        Save the optimized schedule to a file.
        
        Args:
            output_file (str, optional): Output file path. If None, a default name is generated.
            
        Returns:
            str: Path to the saved file
        """
        optimized_schedule = self.optimize()
        
        if not output_file:
            # Generate output filename based on input filename
            basename = os.path.basename(self.schedule_file)
            name_parts = os.path.splitext(basename)
            output_file = f"{name_parts[0]}_optimized{name_parts[1]}"
            output_file = os.path.join(os.path.dirname(self.schedule_file), output_file)
            
        # Fixed output file (always overwritten with latest)
        fixed_output_file = "data/latest_schedule_output_optimized.json"
            
        # Add optimization metadata
        optimized_schedule["rate_optimization"] = {
            "min_threshold": self.min_threshold,
            "optimized_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(optimized_schedule, f, indent=2)
        
        # Also save to fixed filename (will overwrite any existing file)
        with open(fixed_output_file, 'w') as f:
            json.dump(optimized_schedule, f, indent=2)
            
        logger.info(f"Optimized schedule saved to {output_file} and {fixed_output_file}")
        return output_file


def main():
    """Main function to run the optimizer."""
    parser = argparse.ArgumentParser(description='Optimize daily processing rates in a schedule.')
    parser.add_argument('schedule_file', help='Path to the schedule JSON file')
    parser.add_argument('--threshold', type=float, default=85.0, 
                        help='Minimum desired daily processing rate (default: 85.0)')
    parser.add_argument('--output', help='Output file path (optional)')
    
    args = parser.parse_args()
    
    optimizer = DailyRateOptimizer(args.schedule_file, args.threshold)
    optimizer.save_optimized_schedule(args.output)
    
    
if __name__ == "__main__":
    main()