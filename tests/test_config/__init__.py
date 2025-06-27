"""Configuration system tests"""
import sys
import os

# Add the project root to sys.path to avoid import errors
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)