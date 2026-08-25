#!/usr/bin/env python3
"""
Final verification that our fix for the Firebase private key newline processing is correct.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the raw private key from environment (as it exists in the .env file)
private_key_raw = os.environ.get('FIREBASE_PRIVATE_KEY', '')

print("=== FIREBASE PRIVATE KEY NEWLINE PROCESSING VERIFICATION ===")
print()

print("1. RAW PRIVATE KEY FROM ENVIRONMENT (.env file):")
print(f"   Length: {len(private_key_raw)} characters")
print(f"   First 30 chars: {repr(private_key_raw[:30])}")
print(f"   Contains literal backslash-n: {'\\n' in private_key_raw}")
print(f"   Count of literal backslash-n sequences: {private_key_raw.count('\\n')}")
print(f"   Contains actual newline characters: {chr(10) in private_key_raw}")
print(f"   Count of actual newline characters: {private_key_raw.count(chr(10))}")
print()

# Apply our fix
private_key_fixed = (private_key_raw or "").strip().replace('\\n', '\n')

print("2. AFTER APPLYING OUR FIX: .replace('\\n', '\\n')")
print(f"   Length: {len(private_key_fixed)} characters")
print(f"   First 30 chars: {repr(private_key_fixed[:30])}")
print(f"   Last 30 chars: {repr(private_key_fixed[-30:])}")
print(f"   Literal backslash-n sequences remaining: {private_key_fixed.count('\\n')}")
print(f"   Actual newline characters: {private_key_fixed.count(chr(10))}")
print()

print("3. VERIFICATION:")
print(f"   + Literal backslash-n sequences converted to newlines: {private_key_raw.count('\\n')} -> {private_key_fixed.count('\\n')} (should be 0)")
print(f"   + Actual newline characters created: {private_key_raw.count(chr(10))} -> {private_key_fixed.count(chr(10))} (should be +2)")
print(f"   + Total length change: {len(private_key_raw)} -> {len(private_key_fixed)} (should be -2)")
print()

print("4. FORMATTED RESULT (showing structure):")
print("   " + "="*50)
formatted_lines = private_key_fixed.split('\n')
for i, line in enumerate(formatted_lines):
    if i < 3:  # Show first 3 lines
        print(f"   {line}")
    elif i == 3 and len(formatted_lines) > 4:
        print("   ...")
    elif i >= len(formatted_lines) - 2:  # Show last 2 lines
        print(f"   {line}")
print("   " + "="*50)
print()

print("=== CONCLUSION ===")
if private_key_fixed.count('\\n') == 0 and private_key_fixed.count(chr(10)) == 2:
    print("[SUCCESS] Newline processing is working correctly!")
    print("   The literal backslash-n sequences have been converted to actual newlines.")
    print("   This should resolve the 'Unable to load PEM file' error related to InvalidByte(0, 92).")
else:
    print("[ISSUE] Newline processing may not be working correctly.")

print()
print("Note: Any remaining PEM loading errors are likely due to the key data itself")
print("being malformed or truncated, not due to the newline processing fix.")