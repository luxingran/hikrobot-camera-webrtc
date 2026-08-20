from pathlib import Path
import sys


build_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build")
sys.path.insert(0, str(build_dir))

print("before import")
import hikcamera_native

print("after import")
print(hikcamera_native)
