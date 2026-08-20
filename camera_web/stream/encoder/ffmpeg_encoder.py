from __future__ import annotations

from pathlib import Path
import subprocess
import threading
import time

ROOT_DIR = Path(__file__).resolve().parents[2]

FFMPEG_PATH = (
    ROOT_DIR
    / "third_party"
    / "ffmpeg"
    / "bin"
    / "ffmpeg.exe"
)


class FFmpegEncoder:

    def __init__(
        self,
        width: int,
        height: int,
        fps: float = 15,
        output_mode: str = "null",
        rtsp_url: str | None = None,
        bitrate: str = "4M",
    ):
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps)

        self.output_mode = output_mode

        self.rtsp_url = rtsp_url

        self.bitrate = bitrate

        self.process: subprocess.Popen | None = None

        self.lock = threading.Lock()


    def start(self):

        if self.process is not None:
            return

        if not FFMPEG_PATH.exists():
            raise FileNotFoundError(
                f"FFmpeg not found: {FFMPEG_PATH}"
            )


        cmd = [
            str(FFMPEG_PATH),

            "-hide_banner",

            "-loglevel",
            "warning",

            # =================================================
            # 输入：Python BGR24
            # =================================================

            "-f",
            "rawvideo",

            "-pix_fmt",
            "bgr24",

            "-video_size",
            f"{self.width}x{self.height}",

            "-framerate",
            str(self.fps),

            "-i",
            "pipe:0",

            "-an",

            # =================================================
            # H264
            # =================================================

            "-c:v",
            "libx264",

            "-preset",
            "ultrafast",

            "-tune",
            "zerolatency",

            "-pix_fmt",
            "yuv420p",

            # 不要 B Frame
            # WebRTC 对 H264 B-frame 兼容性不好
            "-bf",
            "0",

            # GOP
            "-g",
            str(max(1, int(self.fps))),

            "-keyint_min",
            str(max(1, int(self.fps))),

            # 关闭 scene cut 自动改变关键帧
            "-sc_threshold",
            "0",

            # 控制码率
            "-b:v",
            self.bitrate,

            "-maxrate",
            self.bitrate,

            "-bufsize",
            self.bitrate,
        ]


        # =====================================================
        # 输出
        # =====================================================

        if self.output_mode == "null":

            cmd += [
                "-f",
                "null",
                "-"
            ]


        elif self.output_mode == "rtsp":

            if not self.rtsp_url:
                raise ValueError(
                    "rtsp_url is required "
                    "when output_mode='rtsp'"
                )

            cmd += [
                # FFmpeg RTSP muxer 支持 TCP
                "-rtsp_transport",
                "tcp",

                "-f",
                "rtsp",

                self.rtsp_url,
            ]


        else:

            raise ValueError(
                f"Unsupported output_mode: "
                f"{self.output_mode}"
            )


        print()
        print("FFmpeg command:")
        print(" ".join(cmd))
        print()


        self.process = subprocess.Popen(
            cmd,

            stdin=subprocess.PIPE,

            stdout=subprocess.DEVNULL,

            # 测试阶段直接显示 FFmpeg 错误
            stderr=None,

            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if hasattr(
                    subprocess,
                    "CREATE_NO_WINDOW"
                )
                else 0
            ),
        )


    def encode(
        self,
        frame_bytes: bytes
    ):

        process = self.process

        if process is None:
            raise RuntimeError(
                "FFmpeg encoder not started"
            )

        if process.stdin is None:
            raise RuntimeError(
                "FFmpeg stdin unavailable"
            )


        expected_size = (
            self.width
            * self.height
            * 3
        )


        if len(frame_bytes) != expected_size:

            raise ValueError(
                f"Invalid BGR frame size: "
                f"expected={expected_size}, "
                f"actual={len(frame_bytes)}"
            )


        # FFmpeg 是否已经挂了
        return_code = (
            process.poll()
        )

        if return_code is not None:

            raise RuntimeError(
                f"FFmpeg already exited, "
                f"code={return_code}"
            )


        try:

            with self.lock:

                process.stdin.write(
                    frame_bytes
                )

        except BrokenPipeError:

            return_code = (
                process.poll()
            )

            raise RuntimeError(
                f"FFmpeg pipe broken, "
                f"return_code={return_code}"
            )


    def stop(self):

        process = self.process

        if process is None:
            return


        try:

            if process.stdin:

                try:
                    process.stdin.close()
                except Exception:
                    pass


            try:

                process.wait(
                    timeout=5
                )

            except subprocess.TimeoutExpired:

                process.terminate()

                try:

                    process.wait(
                        timeout=3
                    )

                except subprocess.TimeoutExpired:

                    process.kill()

                    process.wait()


        finally:

            self.process = None


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
        print_interval_s: float = 5.0
    ):

        super().__init__(
            name=f"EncodeWorker-{camera_name}",
            daemon=True,
        )

        self.print_interval_s = print_interval_s
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
                        >= self.print_interval_s
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

