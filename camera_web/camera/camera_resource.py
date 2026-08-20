from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import threading


@dataclass
class CameraResource:

    # 业务名称
    name: str

    # 唯一编号
    serial: str

    # USB3Vision / GigE
    transport: str

    # GigE IP
    ip: str | None = None


    # MVS 相机对象
    device: Any | None = None


    # 状态
    opened: bool = False

    # stream width
    stream_width: int | None = None

    # stream height

    stream_height: int | None = None

    pixel_format: str | None = None

    # 相机锁
    lock: threading.Lock = field(
        default_factory=threading.Lock
    )

    def try_lock(self):

        return self.lock.acquire(
            blocking=False
        )


    def unlock(self):

        if self.lock.locked():
            self.lock.release()

    def acquire(self):
        return self.lock.acquire()


    def release(self):
        self.lock.release()


    def is_open(self):
        return self.opened