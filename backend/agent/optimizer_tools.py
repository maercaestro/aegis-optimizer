#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Agent tools that wrap around the optimizer components.
"""

import logging
import os
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from agent.base import AgentTool
from core.vessel_optimizer import VesselOptimizer
from core.lp_optimizer import LPOptimizer

logger = logging.getLogger(__name__)

class VesselOptimizationTool(AgentTool):
    """Tool for optimizing vessel scheduling and delivery dates."""
    
    @property
    def description(self) -> str:
        return "Optimizes vessel allocation and delivery dates to minimize freight costs while meeting target dates"
    
    def run(self, 
            loading_data_path: str,
            target_delivery_dates: Optional[Dict[str, int]] = None,
            prioritize_dates: bool = True,
            max_penalty: float = 1000000,
            output_format: str = "full") -> Dict[str, Any]:
        """
        Run vessel optimization.
        
        Args:
            loading_data_path: Path to the loading date ranges JSON file
            target_delivery_dates: Dict mapping grades to target arrival days (optional)
            prioritize_dates: If True, prioritize meeting target dates over vessel count
            max_penalty: Maximum penalty for missing target dates (higher = stricter)
            output_format: 'full' or 'scheduler' to format for scheduler
            
        Returns:
            Optimization results
        """
        try:
            # Initialize the vessel optimizer
            optimizer = VesselOptimizer(loading_data_path, target_delivery_dates)
            
            # Run the optimization
            optimization_result = optimizer.optimize(prioritize_dates, max_penalty)
            
            if optimization_result["status"] != "optimal":
                logger.warning(f"Vessel optimization did not find an optimal solution: {optimization_result['status']}")
                return optimization_result
            
            # Format for scheduler if requested
            if output_format == "scheduler":
                vessels = optimizer.format_vessels_for_scheduler(optimization_result)
                return {"status": "optimal", "vessels": vessels, "metadata": optimization_result}
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Error in vessel optimization tool: {str(e)}")
            return {"status": "error", "message": str(e)}


class LPOptimizationTool(AgentTool):
    """Tool for optimizing daily processing rates and blends using linear programming."""
    
    @property
    def description(self) -> str:
        return "Optimizes daily processing rates and blends to maximize throughput while respecting constraints"
    
    def run(self,
            schedule_file: str,
            min_threshold: float = 80.0,
            max_daily_change: float = 10.0,
            save_output: bool = True,
            output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Run LP optimization on a schedule.
        
        Args:
            schedule_file: Path to the schedule JSON file to optimize
            min_threshold: Minimum daily processing rate threshold
            max_daily_change: Maximum allowed change in processing rate between days
            save_output: Whether to save the optimized schedule to a file
            output_file: Path to save the optimized schedule (optional)
            
        Returns:
            Optimization results and path to the saved file if applicable
        """
        try:
            # Initialize the LP optimizer
            optimizer = LPOptimizer(schedule_file)
            
            # If we need to save the output, use the built-in method
            if save_output:
                output_path = optimizer.save_optimized_schedule(output_file)
                
                # Load the optimized schedule to return it
                with open(output_path, 'r') as f:
                    optimized_schedule = json.load(f)
                
                return {
                    "status": "optimal",
                    "schedule": optimized_schedule,
                    "output_file": output_path
                }
            else:
                # Just run the optimizer and return the schedule
                optimized_schedule = optimizer.optimize(min_threshold, max_daily_change)
                return {
                    "status": "optimal",
                    "schedule": optimized_schedule
                }
                
        except Exception as e:
            logger.error(f"Error in LP optimization tool: {str(e)}")
            return {"status": "error", "message": str(e)}


class FullOptimizationTool(AgentTool):
    """Tool that combines vessel optimization and LP optimization into a single workflow."""
    
    @property
    def description(self) -> str:
        return "Performs end-to-end optimization: optimizes vessel schedules and then refinery operations"
    
    def run(self,
            loading_data_path: str,
            input_data_path: str,
            target_delivery_dates: Optional[Dict[str, int]] = None,
            min_threshold: float = 80.0,
            max_daily_change: float = 10.0,
            save_output: bool = True) -> Dict[str, Any]:
        """
        Run full optimization pipeline.
        
        Args:
            loading_data_path: Path to the loading date ranges JSON file
            input_data_path: Path to the input data for scheduling
            target_delivery_dates: Dict mapping grades to target arrival days (optional)
            min_threshold: Minimum daily processing rate threshold for LP optimization
            max_daily_change: Maximum allowed change in processing rate between days for LP optimization
            save_output: Whether to save the optimized schedules to files
            
        Returns:
            Combined optimization results
        """
        try:
            # Step 1: Vessel optimization
            vessel_tool = VesselOptimizationTool()
            vessel_result = vessel_tool.run(
                loading_data_path=loading_data_path,
                target_delivery_dates=target_delivery_dates,
                output_format="scheduler"
            )
            
            if vessel_result["status"] != "optimal":
                return {
                    "status": "error",
                    "stage": "vessel_optimization",
                    "message": vessel_result.get("message", "Vessel optimization failed")
                }
            
            # Step 2: Generate schedule with optimized vessels
            from backend.data_loader import load_input_data
            from backend.core.scheduler import SimpleScheduler
            
            input_data = load_input_data(input_data_path)
            scheduler = SimpleScheduler(input_data)
            optimized_vessels = vessel_result["vessels"]
            schedule = scheduler.generate_schedule(optimized_vessels)
            
            # Save the initial schedule
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            initial_schedule_path = f"data/initial_schedule_{timestamp}.json"
            
            if save_output:
                with open(initial_schedule_path, 'w') as f:
                    json.dump(schedule, f, indent=2)
            
            # Step 3: LP optimization on the schedule
            lp_tool = LPOptimizationTool()
            lp_result = lp_tool.run(
                schedule_file=initial_schedule_path,
                min_threshold=min_threshold,
                max_daily_change=max_daily_change,
                save_output=save_output
            )
            
            # Combine results
            return {
                "status": "optimal",
                "vessel_optimization": vessel_result["metadata"],
                "initial_schedule_file": initial_schedule_path if save_output else None,
                "lp_optimization": lp_result
            }
                
        except Exception as e:
            logger.error(f"Error in full optimization tool: {str(e)}")
            return {"status": "error", "message": str(e)}