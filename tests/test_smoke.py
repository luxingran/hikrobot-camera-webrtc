from pathlib import Path
import sys


sys.path.insert(0, str(Path(r"D:\camera_service_native\build")))

import smoke_native

print(f"smoke_add={smoke_native.add(2, 3)}")
