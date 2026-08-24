#!/usr/bin/env python3
print("Testing intelligence service...")
try:
    from services.intelligence_service import IntelligenceService
    service = IntelligenceService()
    print("SUCCESS: IntelligenceService imported and instantiated")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
