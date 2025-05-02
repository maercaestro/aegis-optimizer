#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility functions for the Aegis Refinery Optimizer.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def parse_ldr_date(ldr_text, year=2025, month=10):
    """
    Parse LDR date text into datetime objects.
    
    Args:
        ldr_text (str): LDR text like "1-3 Oct"
        year (int): Year
        month (int): Month number
        
    Returns:
        tuple: (start_date, end_date)
    """
    parts = ldr_text.split()
    days = parts[0].split("-")
    start_day = int(days[0])
    end_day = int(days[1])
    
    start_date = datetime(year, month, start_day)
    end_date = datetime(year, month, end_day)
    
    return start_date, end_date

def calculate_processing_rates(inventory, pairings, plant_capacity, margins):
    """
    Calculate processing rates for each crude grade based on inventory and constraints.
    
    In the simple scheduler, this will prioritize based on margins.
    In the rate optimizer, this will be optimized for maximum margin.
    
    Args:
        inventory (dict): Current inventory by grade
        pairings (dict): Crude pairings and blending ratios
        plant_capacity (float): Overall plant capacity
        margins (dict): Margin by crude grade
        
    Returns:
        tuple: (processing_rates, blending_details)
            - processing_rates: Dictionary with processing rate by grade
            - blending_details: List of blending operations
    """
    # Create a copy of inventory to work with
    inventory_copy = dict(inventory)
    
    # Initialize processing rates and blending details
    processing_rates = {grade: 0 for grade in inventory_copy}
    blending_details = []
    
    # Convert capacity from bpd to kbpd (thousands of barrels per day)
    plant_capacity_kbpd = plant_capacity / 1000
    
    # Sort grades by margin
    sorted_grades = sorted(
        [g for g in inventory_copy if inventory_copy[g] > 0],
        key=lambda g: margins.get(g, 0),
        reverse=True  # Highest margin first
    )
    
    # Find all possible pairings based on current inventory
    possible_pairings = []
    for grade in sorted_grades:
        pairing_info = pairings.get(grade, {})
        paired_with = pairing_info.get("paired_with")
        
        if paired_with and paired_with in inventory_copy and inventory_copy[paired_with] > 0:
            # Calculate effective margin for the pairing
            ratio = pairing_info.get("ratio", [0.5, 0.5])
            
            # Get margins - default to 0 if not found
            primary_margin = margins.get(grade, 0)
            secondary_margin = margins.get(paired_with, 0)
            
            # Calculate weighted margin
            weighted_margin = (primary_margin * ratio[0] + secondary_margin * ratio[1])
            
            # Convert capacity_bpd to kbpd
            capacity_kbpd = pairing_info.get("capacity_bpd", plant_capacity) / 1000
            
            possible_pairings.append({
                "primary_grade": grade,
                "secondary_grade": paired_with,
                "ratio": ratio,
                "capacity_kbpd": capacity_kbpd,
                "weighted_margin": weighted_margin
            })
    
    # Sort pairings by weighted margin
    sorted_pairings = sorted(
        possible_pairings,
        key=lambda p: p["weighted_margin"],
        reverse=True  # Highest margin first
    )
    
    # Initialize remaining capacity
    remaining_capacity = plant_capacity_kbpd
    
    # Flag to track if we've processed a recipe already
    recipe_processed = False
    
    # First try to process a paired blend (highest margin first)
    if sorted_pairings and not recipe_processed:
        # Take only the highest margin pairing
        pairing = sorted_pairings[0]
        primary_grade = pairing["primary_grade"]
        secondary_grade = pairing["secondary_grade"]
        ratio = pairing["ratio"]
        
        # Important: Respect the capacity_kbpd constraint
        max_capacity = min(pairing["capacity_kbpd"], remaining_capacity)
        
        # Check inventories
        if inventory_copy[primary_grade] > 0 and inventory_copy[secondary_grade] > 0:
            # Calculate how much we can process based on both inventories
            # Inventory is already in kb (thousand barrels)
            max_primary = min(inventory_copy[primary_grade], max_capacity * ratio[0])
            max_secondary = min(inventory_copy[secondary_grade], max_capacity * ratio[1])
            
            # Find limiting factor
            if max_primary / ratio[0] < max_secondary / ratio[1]:
                # Primary crude is limiting
                process_primary = max_primary
                process_secondary = process_primary * ratio[1] / ratio[0]
            else:
                # Secondary crude is limiting
                process_secondary = max_secondary
                process_primary = process_secondary * ratio[0] / ratio[1]
            
            # Ensure we don't exceed capacity
            total_process = process_primary + process_secondary
            if total_process > max_capacity:
                scale_factor = max_capacity / total_process
                process_primary *= scale_factor
                process_secondary *= scale_factor
                total_process = max_capacity
            
            if total_process > 0:
                # Update processing rates
                processing_rates[primary_grade] += process_primary
                processing_rates[secondary_grade] += process_secondary
                
                # Update inventory
                inventory_copy[primary_grade] -= process_primary
                inventory_copy[secondary_grade] -= process_secondary
                
                # Update remaining capacity
                remaining_capacity -= total_process
                
                # Record blending details
                blending_details.append({
                    "primary_grade": primary_grade,
                    "secondary_grade": secondary_grade,
                    "primary_rate": process_primary,
                    "secondary_rate": process_secondary,
                    "total_rate": total_process,
                    "ratio": f"{ratio[0]:.2f}:{ratio[1]:.2f}",
                    "capacity_used": total_process,
                    "capacity_limit": pairing["capacity_kbpd"]
                })
                
                recipe_processed = True
    
    # If no paired recipe was processed and we still have capacity, use solo grades
    if not recipe_processed and sorted_grades and remaining_capacity > 0:
        # Take the highest margin grade available
        grade = sorted_grades[0]
        
        # Get pairing info
        pairing_info = pairings.get(grade, {})
        
        # Convert capacity_bpd to kbpd
        capacity_kbpd = pairing_info.get("capacity_bpd", plant_capacity) / 1000
        
        # Important: Respect the capacity_kbpd constraint
        max_capacity = min(capacity_kbpd, remaining_capacity)
        
        # Process only what's available in inventory, up to max capacity
        process_rate = min(inventory_copy[grade], max_capacity)
        
        if process_rate > 0:
            # Update processing rate
            processing_rates[grade] += process_rate
            
            # Update inventory
            inventory_copy[grade] -= process_rate
            
            # Update remaining capacity
            remaining_capacity -= process_rate
            
            # Record blending details for solo processing
            blending_details.append({
                "primary_grade": grade,
                "secondary_grade": None,
                "primary_rate": process_rate,
                "secondary_rate": 0,
                "total_rate": process_rate,
                "ratio": "1.00:0.00",
                "capacity_used": process_rate,
                "capacity_limit": capacity_kbpd
            })
            
            recipe_processed = True
    
    return processing_rates, blending_details