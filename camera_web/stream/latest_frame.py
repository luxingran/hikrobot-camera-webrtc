# stream/latest_frame.py

from __future__ import annotations

import threading
import time
from typing import Any


class LatestFrame:

    def __init__(self):

        self.lock = threading.Lock()

        self.frame: dict[str, Any] | None = None

        self.updated_at = 0.0

        self.frame_count = 0

        self.error: str | None = None


    def update(
        self,
        frame: dict[str, Any]
    ):

        with self.lock:

            self.frame = frame

            self.updated_at = time.time()

            self.frame_count += 1

            self.error = None



    def set_error(
        self,
        error:str
    ):

        with self.lock:

            self.error = error



    def snapshot(self):

        with self.lock:

            return {

                "frame": self.frame,

                "updated_at": self.updated_at,

                "frame_count": self.frame_count,

                "error": self.error

            }