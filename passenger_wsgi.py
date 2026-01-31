"""
cPanel Passenger WSGI entry point for FastAPI
This file is used by cPanel's Python App Manager to run the FastAPI application.
"""

import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Set environment variables
os.environ.setdefault('PYTHONPATH', current_dir)

# Change to the application directory
os.chdir(current_dir)

# Import the FastAPI app from main.py
try:
    from main import app
    
    # For Passenger/WSGI compatibility, expose as 'application'
    application = app
    
except Exception as e:
    # Error handling for debugging
    import traceback
    error_msg = f"Error loading application: {str(e)}\n{traceback.format_exc()}"
    print(error_msg, file=sys.stderr)
    
    # Create a simple error app
    from fastapi import FastAPI
    error_app = FastAPI()
    
    @error_app.get("/")
    def error():
        return {"error": "Application failed to load", "details": error_msg}
    
    application = error_app
