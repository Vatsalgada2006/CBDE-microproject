#!/usr/bin/env python3
"""
Test script to verify that the app can be imported without errors.
"""
try:
    from app import app
    print("SUCCESS: App imported successfully")
except Exception as e:
    print(f"ERROR: Failed to import app: {e}")
    import traceback
    traceback.print_exc()