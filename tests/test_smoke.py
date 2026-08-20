from pathlib import Path
import sys


sys.path.insert(0, str(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build")))

import smoke_native

print(f"smoke_add={smoke_native.add(2, 3)}")
