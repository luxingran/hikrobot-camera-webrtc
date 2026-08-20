from pathlib import Path
import os
import sys


conda = os.environ.get("CONDA_PREFIX", r"C:\path\to\miniconda3")
os.environ["PATH"] = (
    conda
    + ";"
    + rf"{conda}\Library\bin"
    + ";"
    + os.environ.get("PATH", "")
)

sys.path.insert(0, str(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build")))

print("before import with conda path")
import hikcamera_native

print("after import with conda path")
print(hikcamera_native)
