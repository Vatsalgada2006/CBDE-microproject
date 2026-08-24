import os
print("All environment variables containing FIREBASE or FLASK:")
for key, value in os.environ.items():
    if 'FIREBASE' in key or 'FLASK' in key:
        print(f"{key}: {value}")

print("\nSpecifically checking FIREBASE_STORAGE_BUCKET:")
print(f"FIREBASE_STORAGE_BUCKET in os.environ: {'FIREBASE_STORAGE_BUCKET' in os.environ}")
if 'FIREBASE_STORAGE_BUCKET' in os.environ:
    print(f"FIREBASE_STORAGE_BUCKET value: {repr(os.environ['FIREBASE_STORAGE_BUCKET'])}")
else:
    print("FIREBASE_STORAGE_BUCKET not found in os.environ")