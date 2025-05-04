#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration settings for the Aegis Refinery Optimizer.
"""

import os
import logging

# Determine the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data directories
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

# Default file paths
DEFAULT_INPUT_FILE = os.path.join(DATA_DIR, "input.json")
DEFAULT_LOADING_FILE = os.path.join(DATA_DIR, "loading_date_ranges.json")
DEFAULT_OUTPUT_FILE = os.path.join(RESULTS_DIR, "latest_schedule_output.json")

# API settings
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", 5001))
API_DEBUG = os.environ.get("API_DEBUG", "True").lower() == "true"

# Optimizer settings
DEFAULT_LP_MIN_THRESHOLD = 80.0
DEFAULT_LP_MAX_DAILY_CHANGE = 10.0
DEFAULT_VESSEL_MAX_PENALTY = 1000000

# Create required directories
def ensure_directories():
    """Ensure all required directories exist."""
    for directory in [DATA_DIR, UPLOAD_DIR, RESULTS_DIR]:
        os.makedirs(directory, exist_ok=True)
        logging.debug(f"Ensured directory exists: {directory}")

# Call this at import time to ensure directories exist
ensure_directories()