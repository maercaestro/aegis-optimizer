#!/usr/bin/env python
"""
Script to start the Aegis MCP server with sample data
"""
import os
import json
import sys

# Add the parent directory to path so we can import from the api package
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Import server module
import server

# Sample data file path (you can modify this to point to your actual data)
DATA_FILE = os.path.join(parent_dir, 'api', 'data', 'results', 'latest_schedule_output.json')

def main():
    """Main function to initialize and display server information"""
    print("Aegis MCP Server")
    print("================")
    
    # Check for sample data
    if os.path.exists(DATA_FILE):
        print(f"Found schedule data at: {DATA_FILE}")
        try:
            with open(DATA_FILE, 'r') as f:
                server.schedule_data = json.load(f)
            print("Schedule data loaded successfully!")
        except Exception as e:
            print(f"Error loading schedule data: {e}")
    else:
        print(f"No schedule data found at: {DATA_FILE}")
        print("Tools will return errors until data is loaded.")
    
    # Print available tools
    print("\nAvailable MCP Tools:")
    for tool_name in server.mcp.tools:
        tool = server.mcp.tools[tool_name]
        print(f"- {tool_name}: {tool.description}")
    
    print("\nServer ready! Use `mcp dev server.py` to start the MCP server.")

if __name__ == "__main__":
    main()