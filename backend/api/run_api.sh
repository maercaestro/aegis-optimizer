#!/bin/bash

# Enable command echo to see what's being executed
set -x

# Show timestamp for each command
timestamp() {
  date +"%Y-%m-%d %H:%M:%S"
}

echo "$(timestamp) Starting setup process..."

# Change to project directory
cd "$(dirname "$0")"
echo "$(timestamp) Current directory: $(pwd)"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "$(timestamp) Activating virtual environment..."
    source venv/bin/activate
    echo "$(timestamp) Python interpreter: $(which python)"
    echo "$(timestamp) Python version: $(python --version)"
else
    echo "$(timestamp) No virtual environment found at ./venv"
    echo "$(timestamp) Using system Python: $(which python)"
    echo "$(timestamp) Python version: $(python --version)"
fi

# Set Python path to include project directory and parent directories
export PYTHONPATH=$(pwd):$(pwd)/..:$(pwd)/../..:$PYTHONPATH
echo "$(timestamp) PYTHONPATH set to: $PYTHONPATH"

# Add this line right after setting PYTHONPATH
export PYTHONPATH=$(pwd)/../core:$PYTHONPATH
echo "$(timestamp) Added core directory to PYTHONPATH: $(pwd)/../core"

# List relevant Python directories to verify they exist
echo "$(timestamp) Checking core directory..."
ls -la ../core/

# Create data directories if they don't exist
echo "$(timestamp) Creating data directories..."
mkdir -p data/uploads data/results
echo "$(timestamp) Data directories created or already exist"
# Try direct imports to see if there's a specific error
echo "$(timestamp) Testing direct imports..."
python -c "import sys; sys.path.insert(0, '$(pwd)/../core'); import lp_optimizer; print('Successfully imported lp_optimizer')"

# Set API configuration (can be overridden with environment variables)
export API_HOST=${API_HOST:-0.0.0.0}
export API_PORT=${API_PORT:-5001}
export API_DEBUG=${API_DEBUG:-true}
export FLASK_DEBUG=1
export FLASK_ENV=development # Enable full debug output

echo "$(timestamp) Configuration:"
echo "- API_HOST: $API_HOST"
echo "- API_PORT: $API_PORT"
echo "- API_DEBUG: $API_DEBUG"
echo "- FLASK_DEBUG: $FLASK_DEBUG"
echo "- FLASK_ENV: $FLASK_ENV"

echo "$(timestamp) Starting API server on $API_HOST:$API_PORT (debug=$API_DEBUG)"

# First check if the app.py file exists
if [ ! -f "app.py" ]; then
    echo "$(timestamp) ERROR: app.py file not found!"
    echo "Files in current directory:"
    ls -la
    exit 1
fi

# Check important Python modules
echo "$(timestamp) Checking Python imports..."
python -c "import sys; print('Python path:', sys.path)"
python -c "import sys, os; print('Core directory exists:', os.path.exists(os.path.join('..', 'core')))"
python -c "import importlib.util; print('lp_optimizer importable:', importlib.util.find_spec('lp_optimizer') is not None)"
python -c "import importlib.util; print('scheduler importable:', importlib.util.find_spec('scheduler') is not None)"

# Start the Flask API with verbose output
echo "$(timestamp) Starting Flask API..."
python -u app.py  # Use -u for unbuffered output