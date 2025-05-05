"""
Quick start for the Aegis MCP Server
"""
import os
import sys

def main():
    print("Welcome to Aegis MCP Server!")
    print("==========================")
    print("Available commands:")
    print("  1. Run the server directly: python server.py")
    print("  2. Run with MCP dev tools: mcp dev server.py")
    print("  3. Install for Claude Desktop: mcp install server.py --name \"Aegis Refinery Optimizer\"")
    print("  4. Integrate with Flask API: python flask_integration.py")
    print("\nClient Options:")
    print("  1. Command-line client: python client.py")
    print("  2. Web interface: python web_client.py")
    print("  3. Launch complete system: python launch.py")
    print("\nFrontend Integration:")
    print("  1. Make sure your frontend points to http://localhost:5005 for MCP API")
    print("  2. Use the MCPClient React component to connect to the MCP server")
    print("  3. Start both backend and frontend: python launch.py && cd ../../frontend && npm run dev")
    print("\nFor more information, see the documentation at:")
    print("https://github.com/modelcontextprotocol/python-sdk")

if __name__ == "__main__":
    main()
