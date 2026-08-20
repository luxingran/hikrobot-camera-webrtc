from pathlib import Path
import os
import sys


conda = r"D:\Program\miniconda3"
os.environ["PATH"] = (
    conda
    + ";"
    + rf"{conda}\Library\bin"
    + ";"
    + os.environ.get("PATH", "")
)

sys.path.insert(0, str(Path(r"D:\camera_service_native\build")))

print("before import with conda path")
import hikcamera_native

print("after import with conda path")
print(hikcamera_native)
