#!/bin/bash

# Change to project directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Set Python path to include project directory
export PYTHONPATH=$(pwd):$PYTHONPATH

# Create data directories if they don't exist
mkdir -p data/uploads data/results

# Set API configuration (can be overridden with environment variables)
export API_HOST=${API_HOST:-0.0.0.0}
export API_PORT=${API_PORT:-5001}
export API_DEBUG=${API_DEBUG:-true}

echo "Starting API server on $API_HOST:$API_PORT (debug=$API_DEBUG)"

# Start the Flask API
python app.py