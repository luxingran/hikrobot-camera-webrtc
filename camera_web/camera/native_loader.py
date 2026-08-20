from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def import_native(module_dir: str) -> Any:

    path = Path(module_dir).resolve()

    if str(path) not in sys.path:
        sys.path.insert(
            0,
            str(path)
        )

    import hikcamera_native

    return hikcamera_native