#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Base agent framework for the Aegis Refinery Optimizer.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AgentTool(ABC):
    """Base class for all agent tools."""
    
    @property
    def name(self) -> str:
        """Get the name of the tool."""
        return self.__class__.__name__
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get a description of what the tool does."""
        pass
    
    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with the provided parameters."""
        pass

class OptimizerAgent:
    """
    Agent that can use various optimization tools for refinery scheduling.
    """
    
    def __init__(self):
        """Initialize the optimizer agent."""
        self.tools: Dict[str, AgentTool] = {}
        
    def register_tool(self, tool: AgentTool) -> None:
        """
        Register a tool with the agent.
        
        Args:
            tool: The tool to register
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def list_tools(self) -> List[Dict[str, str]]:
        """
        List all available tools.
        
        Returns:
            List of dictionaries containing tool names and descriptions
        """
        return [{"name": name, "description": tool.description} 
                for name, tool in self.tools.items()]
    
    def run_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Run a specific tool with the provided parameters.
        
        Args:
            tool_name: Name of the tool to run
            **kwargs: Parameters to pass to the tool
            
        Returns:
            Results from the tool execution
            
        Raises:
            KeyError: If the tool does not exist
        """
        if tool_name not in self.tools:
            raise KeyError(f"Tool '{tool_name}' not registered")
        
        logger.info(f"Running tool: {tool_name}")
        return self.tools[tool_name].run(**kwargs)