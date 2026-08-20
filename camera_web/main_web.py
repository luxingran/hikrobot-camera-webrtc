from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


# ============================================================
# Project root
# ============================================================

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT_DIR)
    )


# ============================================================
# Imports
# ============================================================

from camera.native_loader import import_native
from camera.camera_manager import CameraManager

# from stream.encode_worker import EncodeWorker
from stream.encoder.ffmpeg_encoder import EncodeWorker
from stream.encoder.ffmpeg_encoder import (
    FFmpegEncoder, EncodeWorker
)

from web.server import create_web_server


# ============================================================
# Basic config
# ============================================================

CONFIG_PATH = (
    ROOT_DIR
    / "config.json"
)

PUBLIC_HOST = os.environ.get(
    "CAMERA_WEB_PUBLIC_HOST",
    "127.0.0.1",
)

WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

RTSP_HOST = "127.0.0.1"
RTSP_PORT = 8554

USB_NAME = "usb_side"
GIGE_NAME = "gige_top"

USB_ENCODER_FPS = 20
GIGE_ENCODER_FPS = 15

BITRATE = "4M"


# ============================================================
# MediaMTX
# ============================================================

MEDIAMTX_DIR = (
    ROOT_DIR
    / "third_party"
    / "mediamtx"
)

MEDIAMTX_EXE = (
    MEDIAMTX_DIR
    / "mediamtx.exe"
)

MEDIAMTX_CONFIG = (
    MEDIAMTX_DIR
    / "mediamtx.yml"
)


# ============================================================
# Config
# ============================================================

def load_config():

    with CONFIG_PATH.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# Native module
# ============================================================

def get_native_module_dir(
    config: dict
):

    #
    # 如果以后config里增加native.module_dir，
    # 自动使用
    #

    value = (
        config
        .get("native", {})
        .get("module_dir")
    )

    if value:
        return value


    return str(ROOT_DIR.parent / "build")


# ============================================================
# Wait for TCP port
# ============================================================

def wait_for_port(
    host: str,
    port: int,
    timeout: float = 10.0,
):

    start = time.monotonic()

    while (
        time.monotonic()
        - start
        < timeout
    ):

        try:

            with socket.create_connection(
                (host, port),
                timeout=1,
            ):
                return True

        except OSError:
            time.sleep(0.2)

    return False


# ============================================================
# MediaMTX
# ============================================================

def start_mediamtx():

    if not MEDIAMTX_EXE.exists():

        raise FileNotFoundError(
            f"MediaMTX not found: "
            f"{MEDIAMTX_EXE}"
        )


    if not MEDIAMTX_CONFIG.exists():

        raise FileNotFoundError(
            f"MediaMTX config not found: "
            f"{MEDIAMTX_CONFIG}"
        )


    print()
    print("=" * 70)
    print("Starting MediaMTX")
    print("=" * 70)


    process = subprocess.Popen(
        [
            str(MEDIAMTX_EXE),
            str(MEDIAMTX_CONFIG),
        ],

        cwd=str(
            MEDIAMTX_DIR
        ),

        #
        # 先保留MediaMTX日志
        # 方便现场排查
        #
        stdout=None,
        stderr=None,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )


    if not wait_for_port(
        RTSP_HOST,
        RTSP_PORT,
        timeout=10,
    ):

        process.terminate()

        raise RuntimeError(
            "MediaMTX RTSP port "
            "did not start"
        )


    print(
        f"MediaMTX ready: "
        f"rtsp://{RTSP_HOST}:{RTSP_PORT}"
    )

    return process


# ============================================================
# BGR PixelFormat
# ============================================================

def get_bgr8_pixel_type(native):

    formats = native.PIXEL_FORMATS

    for name in (
        "BGR8Packed",
        "BGR8",
    ):

        if name in formats:

            print(
                f"BGR format: "
                f"{name} = {formats[name]}"
            )

            return formats[name]


    raise RuntimeError(
        "BGR8 not found in "
        "native.PIXEL_FORMATS"
    )


# ============================================================
# Main
# ============================================================

def main():

    mediamtx_process = None

    manager = None

    encoders = []

    workers = []

    web_server = None

    web_thread = None


    try:

        print()
        print("=" * 70)
        print("Camera Web Service")
        print("=" * 70)


        # ====================================================
        # 1. Config
        # ====================================================

        config = load_config()


        # ====================================================
        # 2. MediaMTX
        # ====================================================

        mediamtx_process = (
            start_mediamtx()
        )


        # ====================================================
        # 3. Native
        # ====================================================

        module_dir = (
            get_native_module_dir(
                config
            )
        )

        print(
            f"native module: "
            f"{module_dir}"
        )

        native = (
            import_native(
                module_dir
            )
        )


        # ====================================================
        # 4. CameraManager
        # ====================================================

        #
        # 这一行请和你当前已经成功运行的
        # test_dual_encoder.py 保持完全一致
        #

        manager = CameraManager(
            native,
            config,
        )


        print()
        print("Opening cameras...")

        manager.open_all()


        # ====================================================
        # 5. BGR
        # ====================================================

        bgr_pixel_type = (
            get_bgr8_pixel_type(
                native
            )
        )


        # ====================================================
        # 6. Camera resources
        # ====================================================

        usb_resource = manager.get(
            USB_NAME
        )

        gige_resource = manager.get(
            GIGE_NAME
        )


        usb_camera = (
            usb_resource.device
        )

        gige_camera = (
            gige_resource.device
        )


        # ====================================================
        # 7. Read actual stream dimensions
        # ====================================================

        usb_width = (
            usb_resource.stream_width
            or 1920
        )

        usb_height = (
            usb_resource.stream_height
            or 1080
        )

        gige_width = (
            gige_resource.stream_width
            or 1920
        )

        gige_height = (
            gige_resource.stream_height
            or 1080
        )


        # ====================================================
        # 8. Encoders
        # ====================================================

        usb_encoder = FFmpegEncoder(
            width=usb_width,
            height=usb_height,
            fps=USB_ENCODER_FPS,

            output_mode="rtsp",

            rtsp_url=(
                f"rtsp://"
                f"{RTSP_HOST}:"
                f"{RTSP_PORT}/"
                f"{USB_NAME}"
            ),

            bitrate=BITRATE,
        )


        gige_encoder = FFmpegEncoder(
            width=gige_width,
            height=gige_height,
            fps=GIGE_ENCODER_FPS,

            output_mode="rtsp",

            rtsp_url=(
                f"rtsp://"
                f"{RTSP_HOST}:"
                f"{RTSP_PORT}/"
                f"{GIGE_NAME}"
            ),

            bitrate=BITRATE,
        )


        encoders = [
            usb_encoder,
            gige_encoder,
        ]


        print()
        print("Starting FFmpeg encoders...")

        for encoder in encoders:
            encoder.start()


        # ====================================================
        # 9. Workers
        # ====================================================

        usb_worker = EncodeWorker(
            camera_name=USB_NAME,
            camera=usb_camera,
            encoder=usb_encoder,
            bgr_pixel_type=(
                bgr_pixel_type
            ),
        )


        gige_worker = EncodeWorker(
            camera_name=GIGE_NAME,
            camera=gige_camera,
            encoder=gige_encoder,
            bgr_pixel_type=(
                bgr_pixel_type
            ),
        )


        workers = [
            usb_worker,
            gige_worker,
        ]


        print()
        print("Starting camera workers...")

        for worker in workers:
            worker.start()


        # ====================================================
        # 10. Web Server
        # ====================================================

        web_server = (
            create_web_server(
                WEB_HOST,
                WEB_PORT,
            )
        )


        web_thread = threading.Thread(
            target=(
                web_server
                .serve_forever
            ),

            name="WebServer",

            daemon=True,
        )

        web_thread.start()


        # ====================================================
        # Ready
        # ====================================================

        print()
        print("=" * 70)
        print("SERVICE READY")
        print("=" * 70)

        print(
            f"Web:"
        )

        print(
            f"http://"
            f"{PUBLIC_HOST}:"
            f"{WEB_PORT}"
        )

        print()

        print(
            f"USB WebRTC:"
        )

        print(
            f"http://"
            f"{PUBLIC_HOST}:8889/"
            f"{USB_NAME}"
        )

        print()

        print(
            f"GigE WebRTC:"
        )

        print(
            f"http://"
            f"{PUBLIC_HOST}:8889/"
            f"{GIGE_NAME}"
        )

        print()

        print(
            "Press Ctrl+C to stop"
        )

        print("=" * 70)


        # ====================================================
        # Main loop
        # ====================================================

        while True:

            time.sleep(1)


            #
            # 如果MediaMTX意外退出，
            # 整个服务也退出
            #

            if (
                mediamtx_process.poll()
                is not None
            ):

                raise RuntimeError(
                    "MediaMTX exited "
                    f"unexpectedly, "
                    f"code="
                    f"{mediamtx_process.returncode}"
                )


    except KeyboardInterrupt:

        print()
        print("Ctrl+C received")


    except Exception as e:

        print()
        print(
            f"FATAL ERROR: {e}"
        )


    finally:

        print()
        print("=" * 70)
        print("Stopping service...")
        print("=" * 70)


        # ====================================================
        # 1. Worker
        # ====================================================

        for worker in workers:

            try:
                worker.stop()
            except Exception:
                pass


        for worker in workers:

            try:
                worker.join(
                    timeout=5
                )
            except Exception:
                pass


        # ====================================================
        # 2. FFmpeg
        # ====================================================

        for encoder in encoders:

            try:
                encoder.stop()
            except Exception as e:

                print(
                    "encoder stop error:",
                    e
                )


        # ====================================================
        # 3. Cameras
        # ====================================================

        if manager is not None:

            try:
                manager.close_all()
            except Exception as e:

                print(
                    "camera close error:",
                    e
                )


        # ====================================================
        # 4. Web
        # ====================================================

        if web_server is not None:

            try:
                web_server.shutdown()
                web_server.server_close()
            except Exception:
                pass


        if web_thread is not None:

            try:
                web_thread.join(
                    timeout=3
                )
            except Exception:
                pass


        # ====================================================
        # 5. MediaMTX
        # ====================================================

        if mediamtx_process is not None:

            if (
                mediamtx_process.poll()
                is None
            ):

                print(
                    "Stopping MediaMTX..."
                )

                try:
                    mediamtx_process.terminate()

                    mediamtx_process.wait(
                        timeout=5
                    )

                except subprocess.TimeoutExpired:

                    mediamtx_process.kill()

                    mediamtx_process.wait()


        print()
        print("=" * 70)
        print("Service stopped")
        print("=" * 70)


if __name__ == "__main__":

    main()
