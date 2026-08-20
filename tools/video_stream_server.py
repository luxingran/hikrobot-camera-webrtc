from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import time
from typing import Any


class LatestFrame:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.jpeg: bytes | None = None
        self.error: str | None = None
        self.frame_num: int | None = None
        self.updated_at: float | None = None
        self.capture_ms: float = 0.0
        self.save_ms: float = 0.0

    def set_frame(self, jpeg: bytes, frame_num: int, capture_ms: float, save_ms: float) -> None:
        with self.lock:
            self.jpeg = jpeg
            self.error = None
            self.frame_num = frame_num
            self.updated_at = time.time()
            self.capture_ms = capture_ms
            self.save_ms = save_ms

    def set_error(self, error: str) -> None:
        with self.lock:
            self.error = error

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "jpeg": self.jpeg,
                "error": self.error,
                "frame_num": self.frame_num,
                "updated_at": self.updated_at,
                "capture_ms": self.capture_ms,
                "save_ms": self.save_ms,
            }


def import_native(module_dir: str):
    sys.path.insert(0, str(Path(module_dir).resolve()))
    import hikcamera_native

    return hikcamera_native


def choose_serial(native: Any, requested_serial: str | None) -> str:
    devices = native.HikrobotCamera.enum_devices()
    if not devices:
        raise RuntimeError("No camera devices found")

    if requested_serial:
        for device in devices:
            if device.serial == requested_serial:
                return requested_serial
        raise RuntimeError(f"Camera serial not found: {requested_serial}")

    for device in devices:
        if device.transport == "USB3Vision":
            return device.serial
    return devices[0].serial


def make_frame_for_save(native: Any, cam: Any, frame: dict[str, Any], convert_to: str | None) -> dict[str, Any]:
    if not convert_to:
        return frame
    converted = cam.convert_frame(frame, native.PIXEL_FORMATS[convert_to])
    return {
        "width": converted["width"],
        "height": converted["height"],
        "pixel_type": converted["pixel_type"],
        "frame_num": frame.get("frame_num", 0),
        "frame_len": converted["data_len"],
        "data": converted["data"],
    }


def capture_loop(args: argparse.Namespace, latest: LatestFrame) -> None:
    native = import_native(args.module_dir)
    serial = choose_serial(native, args.serial)
    temp_dir = Path(tempfile.gettempdir()) / "hikrobot_video_stream"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_jpg = temp_dir / "latest.jpg"

    while True:
        cam = native.HikrobotCamera(serial)
        try:
            cam.open()
            while True:
                t0 = time.perf_counter()
                frame = cam.capture_burst(1, args.timeout_ms)[0]
                t1 = time.perf_counter()
                save_frame = make_frame_for_save(native, cam, frame, args.convert_to)
                cam.save_frame(save_frame, str(temp_jpg), "jpg", args.quality)
                jpeg = temp_jpg.read_bytes()
                t2 = time.perf_counter()
                latest.set_frame(
                    jpeg,
                    int(frame.get("frame_num", 0)),
                    (t1 - t0) * 1000.0,
                    (t2 - t1) * 1000.0,
                )
                time.sleep(max(0.0, 1.0 / args.fps))
        except Exception as exc:
            latest.set_error(str(exc))
            time.sleep(args.reconnect_s)
        finally:
            try:
                if cam.is_open():
                    cam.close()
            except Exception:
                pass


def make_handler(latest: LatestFrame):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path in {"/", "/index.html"}:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Hikrobot Camera Stream</title>
  <style>
    body { margin: 0; background: #111; color: #eee; font-family: Arial, sans-serif; }
    header { padding: 12px 16px; background: #222; }
    img { display: block; max-width: 100vw; max-height: calc(100vh - 54px); margin: 0 auto; }
  </style>
</head>
<body>
  <header>Hikrobot Camera Stream <span id="status"></span></header>
  <img src="/stream.mjpg" />
</body>
</html>"""
                )
                return

            if self.path == "/status":
                snap = latest.snapshot()
                body = (
                    f"frame_num={snap['frame_num']} "
                    f"capture_ms={snap['capture_ms']:.2f} "
                    f"save_ms={snap['save_ms']:.2f} "
                    f"error={snap['error']}"
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path != "/stream.mjpg":
                self.send_error(404)
                return

            self.send_response(200)
            self.send_header("Age", "0")
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()

            last_sent_at = 0.0
            while True:
                snap = latest.snapshot()
                jpeg = snap["jpeg"]
                updated_at = snap["updated_at"] or 0.0
                if jpeg and updated_at != last_sent_at:
                    last_sent_at = updated_at
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                time.sleep(0.03)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Show Hikrobot camera as an MJPEG stream")
    parser.add_argument("--module-dir", default="D:/camera_service_native/build")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--serial", default=None)
    parser.add_argument("--fps", type=float, default=2.0)
    parser.add_argument("--quality", type=int, default=85)
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument("--convert-to", default="BGR8")
    parser.add_argument("--reconnect-s", type=float, default=1.0)
    args = parser.parse_args()

    latest = LatestFrame()
    worker = threading.Thread(target=capture_loop, args=(args, latest), daemon=True)
    worker.start()

    server = ThreadingHTTPServer((args.host, args.port), make_handler(latest))
    print(f"stream_url=http://{args.host}:{args.port}/")
    print(f"status_url=http://{args.host}:{args.port}/status")
    server.serve_forever()


if __name__ == "__main__":
    main()
