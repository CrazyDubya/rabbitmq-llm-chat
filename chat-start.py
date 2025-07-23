#!/usr/bin/env python3
"""
Legacy entry point for RabbitMQ LLM Chat Platform.
Redirects to the new main.py entry point for backward compatibility.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == '__main__':
    print("Note: chat-start.py is deprecated. Please use 'python main.py' instead.")
    print("Running main application...\n")
    
    # Set default arguments for backward compatibility
    if len(sys.argv) == 1:
        sys.argv.extend(['run', '--debug'])
    
    main()