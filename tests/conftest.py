"""
pytest configuration and shared fixtures.
"""
import sys
import os

# Make databricks notebooks importable as Python modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../databricks/notebooks"))
