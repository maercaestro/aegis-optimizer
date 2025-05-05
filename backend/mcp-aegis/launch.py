#!/usr/bin/env python
"""
Launch script for the Aegis MCP Server and API Gateway
"""
import os
import subprocess
import time
import webbrowser
import signal
import sys

def main():
    print("Launching Aegis MCP System...")
    print("============================")
    
    # Start the API Gateway in a separate process
    api_process = subprocess.Popen(
        ["python", "flask_integration.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    print("Started API Gateway...")
    time.sleep(2)  # Give the server time to start
    
    # Check if the process is still running
    if api_process.poll() is not None:
        print("Error starting API Gateway:")
        stderr = api_process.stderr.read()
        print(stderr)
        return
    
    # Open the web UI in the default browser
    print("Opening web interface...")
    webbrowser.open("http://localhost:5005")
    
    print("\nAegis MCP System is running!")
    print("- API Gateway: http://localhost:5005")
    print("\nPress Ctrl+C to stop all services")
    
    try:
        # Keep the script running until Ctrl+C
        while True:
            line = api_process.stdout.readline()
            if line:
                print("API Gateway:", line.strip())
            
            # Check if the process has exited
            if api_process.poll() is not None:
                print("API Gateway stopped unexpectedly.")
                break
                
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down Aegis MCP System...")
    finally:
        # Ensure all processes are terminated
        if api_process and api_process.poll() is None:
            api_process.terminate()
            try:
                api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api_process.kill()

if __name__ == "__main__":
    main()