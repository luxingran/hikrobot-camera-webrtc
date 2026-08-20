from pathlib import Path
import sys


build_dir = Path(r"D:\camera_service_native\build")
sys.path.insert(0, str(build_dir))

print("before import")
import hikcamera_native

print("after import")
print(hikcamera_native)
