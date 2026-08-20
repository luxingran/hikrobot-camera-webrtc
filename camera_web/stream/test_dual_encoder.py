from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path


# ============================================================
# 路径
# ============================================================

# 当前文件：
# camera_web/stream/test_dual_encoder.py
#
# parents[0] = stream
# parents[1] = camera_web
CAMERA_WEB_ROOT = Path(__file__).resolve().parents[1]

if str(CAMERA_WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(CAMERA_WEB_ROOT))


# ============================================================
# 项目模块
# ============================================================

from camera.native_loader import import_native
from camera.camera_manager import CameraManager
from stream.encoder.ffmpeg_encoder import FFmpegEncoder


# ============================================================
# 测试参数
# ============================================================

CONFIG_PATH = CAMERA_WEB_ROOT / "config.json"

TEST_DURATION_S = 0

PRINT_INTERVAL_S = 2.0

USB_NAME = "usb_side"
GIGE_NAME = "gige_top"

USB_ENCODER_FPS = 20
GIGE_ENCODER_FPS = 15


# ============================================================
# 配置读取
# ============================================================

def load_config(path: Path) -> dict:

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# 获取 BGR8 pixel type
# ============================================================

def get_bgr8_pixel_type(native):

    formats = native.PIXEL_FORMATS

    # 不同版本封装可能名称不同
    candidates = [
        "BGR8Packed",
        "BGR8",
    ]

    for name in candidates:

        if name in formats:

            print(
                f"BGR output format: "
                f"{name} = {formats[name]}"
            )

            return formats[name]

    raise RuntimeError(
        "Cannot find BGR8 format in "
        "native.PIXEL_FORMATS. "
        f"Available formats: {formats}"
    )


# ============================================================
# 编码 Worker
# ============================================================

class EncodeWorker(threading.Thread):

    def __init__(
        self,
        camera_name: str,
        camera,
        encoder: FFmpegEncoder,
        bgr_pixel_type,
    ):

        super().__init__(
            name=f"EncodeWorker-{camera_name}",
            daemon=True,
        )

        self.camera_name = camera_name

        self.camera = camera

        self.encoder = encoder

        self.bgr_pixel_type = (
            bgr_pixel_type
        )

        self.stop_event = (
            threading.Event()
        )

        self.frame_count = 0

        self.error_count = 0

        self.start_time = 0.0

        self.capture_total = 0.0

        self.convert_total = 0.0

        self.encode_total = 0.0


    def stop(self):

        self.stop_event.set()


    def run(self):

        print(f"[{self.camera_name}] "f"worker starting...")

        last_print_time = (time.perf_counter())

        last_print_count = 0

        self.start_time = (
            last_print_time
        )

        try:

            #
            # CameraManager 已经 open()
            #
            # Worker 这里只负责 StartGrabbing
            #
            self.camera.start()

            print(
                f"[{self.camera_name}] "
                f"camera grabbing started"
            )

            while (
                not self.stop_event.is_set()
            ):

                try:

                    # ======================================
                    # 1. grab
                    # ======================================

                    t0 = (
                        time.perf_counter()
                    )

                    frame = (
                        self.camera.grab_frame(
                            timeout_ms=3000
                        )
                    )

                    t1 = (
                        time.perf_counter()
                    )


                    # ======================================
                    # 2. Bayer -> BGR
                    # ======================================

                    bgr = (
                        self.camera.convert_frame(
                            frame,
                            self.bgr_pixel_type,
                        )
                    )

                    t2 = (
                        time.perf_counter()
                    )


                    # ======================================
                    # 检查转换结果
                    # ======================================

                    if bgr is None:

                        raise RuntimeError(
                            "convert_frame "
                            "returned None"
                        )


                    if "data" not in bgr:

                        raise RuntimeError(
                            "converted frame "
                            "has no data"
                        )


                    # ======================================
                    # 3. BGR -> FFmpeg
                    # ======================================

                    self.encoder.encode(
                        bgr["data"]
                    )

                    t3 = (
                        time.perf_counter()
                    )


                    # ======================================
                    # 统计
                    # ======================================

                    self.frame_count += 1

                    self.capture_total += (
                        t1 - t0
                    )

                    self.convert_total += (
                        t2 - t1
                    )

                    self.encode_total += (
                        t3 - t2
                    )


                    # ======================================
                    # 定期打印
                    # ======================================

                    now = (
                        time.perf_counter()
                    )

                    if (
                        now
                        - last_print_time
                        >= PRINT_INTERVAL_S
                    ):

                        interval_frames = (
                            self.frame_count
                            - last_print_count
                        )

                        interval_time = (
                            now
                            - last_print_time
                        )

                        fps = (
                            interval_frames
                            / interval_time
                        )


                        avg_capture_ms = (
                            self.capture_total
                            / self.frame_count
                            * 1000
                        )


                        avg_convert_ms = (
                            self.convert_total
                            / self.frame_count
                            * 1000
                        )


                        avg_encode_ms = (
                            self.encode_total
                            / self.frame_count
                            * 1000
                        )


                        print(
                            f"{self.camera_name:10s} "
                            f"fps: {fps:6.2f} | "
                            f"frames: "
                            f"{self.frame_count:6d} | "
                            f"grab: "
                            f"{avg_capture_ms:6.2f} ms | "
                            f"convert: "
                            f"{avg_convert_ms:6.2f} ms | "
                            f"encode: "
                            f"{avg_encode_ms:6.2f} ms | "
                            f"size: "
                            f"{bgr['width']}x"
                            f"{bgr['height']} | "
                            f"errors: "
                            f"{self.error_count}"
                        )


                        last_print_time = (
                            now
                        )

                        last_print_count = (
                            self.frame_count
                        )


                except Exception as e:

                    self.error_count += 1

                    print(
                        f"[{self.camera_name}] "
                        f"frame error: {e}"
                    )

                    time.sleep(0.1)


        except Exception as e:

            print(
                f"[{self.camera_name}] "
                f"worker fatal error: {e}"
            )


        finally:

            try:

                if self.camera.is_grabbing():

                    self.camera.stop()

            except Exception:

                # 如果 wrapper 没有
                # is_grabbing()，直接 stop
                try:
                    self.camera.stop()
                except Exception as e:

                    print(
                        f"[{self.camera_name}] "
                        f"camera stop error: {e}"
                    )


            print(
                f"[{self.camera_name}] "
                f"worker stopped"
            )


    def print_summary(self):

        elapsed = (
            time.perf_counter()
            - self.start_time
        )

        if elapsed <= 0:
            return

        fps = (
            self.frame_count
            / elapsed
        )

        if self.frame_count > 0:

            capture_ms = (
                self.capture_total
                / self.frame_count
                * 1000
            )

            convert_ms = (
                self.convert_total
                / self.frame_count
                * 1000
            )

            encode_ms = (
                self.encode_total
                / self.frame_count
                * 1000
            )

        else:

            capture_ms = 0

            convert_ms = 0

            encode_ms = 0


        print(
            f"\n[{self.camera_name}]"
        )

        print(
            f"frames        : "
            f"{self.frame_count}"
        )

        print(
            f"average fps   : "
            f"{fps:.2f}"
        )

        print(
            f"grab avg      : "
            f"{capture_ms:.2f} ms"
        )

        print(
            f"convert avg   : "
            f"{convert_ms:.2f} ms"
        )

        print(
            f"encode avg    : "
            f"{encode_ms:.2f} ms"
        )

        print(
            f"errors        : "
            f"{self.error_count}"
        )


# ============================================================
# 主程序
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "Dual Camera H264 Encoding Test"
    )

    print(
        "=" * 70
    )


    # ========================================================
    # 1. 配置
    # ========================================================

    print(
        f"\nconfig: "
        f"{CONFIG_PATH}"
    )

    config = (
        load_config(
            CONFIG_PATH
        )
    )


    # ========================================================
    # 2. 加载 native
    # ========================================================

    MODULE_DIR = r"D:/camera_service_native/build_py311"

    print(
        f"native module dir: {MODULE_DIR}"
    )

    native = import_native(
        MODULE_DIR
)


    # ========================================================
    # 3. CameraManager
    # ========================================================

    manager = (
        CameraManager(
            native,
            config,
        )
    )


    workers = []

    encoders = []


    try:

        # ====================================================
        # 4. 打开所有相机
        # ====================================================

        print(
            "\nopening cameras..."
        )

        manager.open_all()


        # ====================================================
        # 5. 获取 BGR8
        # ====================================================

        bgr_pixel_type = (
            get_bgr8_pixel_type(
                native
            )
        )


        # ====================================================
        # 6. 获取相机
        # ====================================================

        usb_resource = (
            manager.get(
                USB_NAME
            )
        )

        gige_resource = (
            manager.get(
                GIGE_NAME
            )
        )


        usb_camera = (
            usb_resource.device
        )

        gige_camera = (
            gige_resource.device
        )


        if usb_camera is None:

            raise RuntimeError(
                f"{USB_NAME} "
                f"device is None"
            )


        if gige_camera is None:

            raise RuntimeError(
                f"{GIGE_NAME} "
                f"device is None"
            )


        # ====================================================
        # 7. Encoder
        # ====================================================

        usb_encoder = FFmpegEncoder(
            width=1920,
            height=1080,
            fps=20,

            output_mode="rtsp",

            rtsp_url=(
                "rtsp://127.0.0.1:8554/"
                "usb_side"
            ),

            bitrate="4M",
        )


        gige_encoder = FFmpegEncoder(
            width=1920,
            height=1080,
            fps=15,

            output_mode="rtsp",

            rtsp_url=(
                "rtsp://127.0.0.1:8554/"
                "gige_top"
            ),

            bitrate="4M",
        )


        encoders = [
            usb_encoder,
            gige_encoder,
        ]


        print(
            "\nstarting ffmpeg..."
        )


        usb_encoder.start()

        gige_encoder.start()


        # ====================================================
        # 8. Worker
        # ====================================================

        usb_worker = (
            EncodeWorker(
                camera_name=USB_NAME,
                camera=usb_camera,
                encoder=usb_encoder,
                bgr_pixel_type=(
                    bgr_pixel_type
                ),
            )
        )


        gige_worker = (
            EncodeWorker(
                camera_name=GIGE_NAME,
                camera=gige_camera,
                encoder=gige_encoder,
                bgr_pixel_type=(
                    bgr_pixel_type
                ),
            )
        )


        workers = [
            usb_worker,
            gige_worker,
        ]


        print(
            "\nstarting workers..."
        )


        for worker in workers:

            worker.start()


        # ====================================================
        # 9. 测试
        # ====================================================

        print()

        print(
            "=" * 70
        )

        print(
            f"test running for "
            f"{TEST_DURATION_S} seconds"
        )

        print(
            "Ctrl+C can stop early"
        )

        print(
            "=" * 70
        )

        print()


        start = (
            time.perf_counter()
        )


        while True:

            time.sleep(
                0.2
            )

            elapsed = (
                time.perf_counter()
                - start
            )


            if (
                TEST_DURATION_S > 0
                and elapsed
                >= TEST_DURATION_S
            ):

                print(
                    "\ntest duration reached"
                )

                break


    except KeyboardInterrupt:

        print(
            "\nCtrl+C received"
        )


    finally:

        # ====================================================
        # 停止顺序非常重要
        #
        # Worker
        #   ↓
        # Camera grabbing
        #   ↓
        # FFmpeg
        #   ↓
        # Camera close
        # ====================================================

        print(
            "\nstopping workers..."
        )


        for worker in workers:

            worker.stop()


        for worker in workers:

            worker.join(
                timeout=5
            )


        print(
            "stopping ffmpeg..."
        )


        for encoder in encoders:

            try:

                encoder.stop()

            except Exception as e:

                print(
                    "encoder stop error:",
                    e
                )


        print(
            "closing cameras..."
        )


        try:

            manager.close_all()

        except Exception as e:

            print(
                "manager close error:",
                e
            )


        # ====================================================
        # 最终统计
        # ====================================================

        print()

        print(
            "=" * 70
        )

        print(
            "FINAL RESULT"
        )

        print(
            "=" * 70
        )


        for worker in workers:

            worker.print_summary()


        print()

        print(
            "=" * 70
        )

        print(
            "test finished"
        )

        print(
            "=" * 70
        )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    main()