#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Data loader module for the Aegis Refinery Optimizer.
"""

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def load_input_data(file_path):
    """
    Load input data from the specified JSON file.
    
    Args:
        file_path (str): Path to the input JSON file
        
    Returns:
        dict: Parsed and processed input data
    """
    logger.info(f"Loading input data from {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Process and validate the data
        processed_data = process_input_data(data)
        return processed_data
    
    except FileNotFoundError:
        logger.error(f"Input file not found: {file_path}")
        raise
    
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in input file: {file_path}")
        raise
    
    except Exception as e:
        logger.error(f"Error loading input data: {str(e)}")
        raise

def process_input_data(data):
    """
    Process and validate the input data.
    
    Args:
        data (dict): Raw input data
        
    Returns:
        dict: Processed input data
    """
    # Add processing date information
    data["processing_dates"] = {
        "start_date": datetime.strptime("2025-10-01", "%Y-%m-%d"),
        "end_date": datetime.strptime("2025-10-30", "%Y-%m-%d"),
        "days": 30
    }
    
    # Process LDR (Laydays and Ranges) for each feedstock delivery
    for feedstock in data["feedstock_delivery_program"]:
        processed_ldrs = []
        for ldr in feedstock["ldr"]:
            # Parse LDR like "1-3 Oct"
            parts = ldr.split()
            days = parts[0].split("-")
            start_day = int(days[0])
            end_day = int(days[1])
            
            # Convert to arrival days (1-indexed)
            processed_ldrs.append({
                "start_day": start_day,
                "end_day": end_day,
                "ldr_text": ldr
            })
        
        feedstock["processed_ldr"] = processed_ldrs
    
    # Convert margin data to a dictionary for easier access
    margin_dict = {item["grade"]: item["margin"] for item in data["margin_usd_per_bbl_oct"]}
    data["margin_dict"] = margin_dict
    
    # Convert crude pairings to a dictionary for easier access
    pairings_dict = {}
    for pairing in data["crude_pairings_blending"]:
        grade = pairing["grade"]
        paired_with = pairing["paired_with"]
        capacity = pairing["capacity_bpd"]
        
        if paired_with == "-":
            paired_with = None
            ratio = [1.0]
        else:
            # Parse ratio like "27:73"
            ratio_parts = pairing["pairing_ratio"].split(":")
            ratio = [float(r) / 100.0 for r in ratio_parts]
        
        pairings_dict[grade] = {
            "paired_with": paired_with,
            "capacity_bpd": capacity,
            "ratio": ratio
        }
    
    data["pairings_dict"] = pairings_dict
    
    # Process tank data
    tanks_dict = {item["tank_name"]: {"capacity": item["capacity"], "contents": []} for item in data["tanks"]}
    data["tanks_dict"] = tanks_dict
    
    # Process opening inventory and associate with tanks
    inventory_dict = {}
    for item in data["opening_inventory"]:
        grade = item["grade"]
        volume = item["volume"]
        tank_name = item["tank"]
        
        # Add grade to inventory dict
        if grade not in inventory_dict:
            inventory_dict[grade] = 0
        inventory_dict[grade] += volume
        
        # Update tank contents
        if tank_name:
            tanks_dict[tank_name]["contents"].append({
                "grade": grade,
                "volume": volume
            })
    
    data["inventory_dict"] = inventory_dict
    
    # Calculate total tank capacity
    total_tank_capacity = sum(tank["capacity"] for tank in data["tanks"])
    data["total_tank_capacity"] = total_tank_capacity
    
    return data