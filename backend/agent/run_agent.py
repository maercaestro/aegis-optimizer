#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to run the optimizer agent with various tools.
"""

import logging
import json
from datetime import datetime

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

def main():
    """Main function to demonstrate the agent tools."""
    logger.info("Initializing Optimizer Agent")
    
    # Create agent and register tools
    agent = OptimizerAgent()
    agent.register_tool(VesselOptimizationTool())
    agent.register_tool(LPOptimizationTool())
    agent.register_tool(FullOptimizationTool())
    
    # List available tools
    print("\nAvailable tools:")
    for tool in agent.list_tools():
        print(f"- {tool['name']}: {tool['description']}")
    
    # Example: Run vessel optimization
    print("\nRunning vessel optimization...")
    vessel_result = agent.run_tool(
        "VesselOptimizationTool",
        loading_data_path="data/loading_date_ranges.json",
        target_delivery_dates={"A": 7, "B": 15, "F": 23},
        output_format="scheduler"
    )
    
    # Print vessel optimization result summary
    if vessel_result["status"] == "optimal":
        vessel_count = vessel_result["metadata"]["vessel_count"]
        freight_cost = vessel_result["metadata"]["freight_cost"]
        print(f"Vessel optimization successful: {vessel_count} vessels, ${freight_cost:,.2f} freight cost")
        
        # Print vessel arrival schedule
        print("\nOptimized vessel arrivals:")
        for i, vessel in enumerate(vessel_result["vessels"]):
            cargo_str = ", ".join([f"{c['grade']}: {c['volume']} kb" for c in vessel["cargo"]])
            print(f"Vessel {i+1}: Day {vessel['arrival_day']} - Cargo: {cargo_str}")
    else:
        print(f"Vessel optimization failed: {vessel_result.get('message', 'Unknown error')}")
    
    # Example: Run full optimization pipeline
    print("\nRunning full optimization pipeline...")
    full_result = agent.run_tool(
        "FullOptimizationTool",
        loading_data_path="data/loading_date_ranges.json",
        input_data_path="data/input.json",
        target_delivery_dates={"A": 7, "B": 15, "F": 23},
        save_output=True
    )
    
    # Print full optimization result summary
    if full_result["status"] == "optimal":
        vessel_opt = full_result["vessel_optimization"]
        lp_opt = full_result["lp_optimization"]
        print(f"Full optimization successful!")
        print(f"Vessel optimization: {vessel_opt['vessel_count']} vessels, ${vessel_opt['freight_cost']:,.2f} freight cost")
        print(f"Initial schedule saved to: {full_result['initial_schedule_file']}")
        print(f"LP optimized schedule saved to: {lp_opt['output_file']}")
    else:
        print(f"Full optimization failed: {full_result.get('message', 'Unknown error')}")

if __name__ == "__main__":
    main()