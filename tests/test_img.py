from pathlib import Path
import sys
import time
import statistics


# ============================================================
# Basic utils
# ============================================================

def ms(seconds: float) -> float:
    return seconds * 1000.0


def line():
    print("=" * 80)


def frame_get(frame, name, default=None):
    """
    兼容两种 pybind 返回形式：

    1. dict
       frame["frame_num"]

    2. C++ Frame 对象
       frame.frame_num
    """
    if isinstance(frame, dict):
        return frame.get(name, default)

    return getattr(frame, name, default)


# ============================================================
# Parameter print helpers
# ============================================================

def print_float_param(cam, name: str):
    try:
        p = cam.get_float(name)

        print(
            f"{name}: "
            f"value={p.value:.2f}, "
            f"min={p.min:.2f}, "
            f"max={p.max:.2f}"
        )

    except Exception as e:
        print(
            f"{name}: read failed: {e}"
        )


def print_int_param(cam, name: str):
    try:
        p = cam.get_int(name)

        print(
            f"{name}: "
            f"value={p.value}, "
            f"min={p.min}, "
            f"max={p.max}, "
            f"inc={p.increment}"
        )

    except Exception as e:
        print(
            f"{name}: read failed: {e}"
        )


# ============================================================
# Single frame benchmark
# ============================================================

def benchmark_single(
    cam,
    repeat: int = 10,
    warmup: int = 2,
    timeout_ms: int = 3000,
):
    """
    纯 capture_burst(1) 性能测试。

    不做：
      - Bayer -> BGR
      - JPG
      - PNG
      - BMP
      - 算法

    测出来的就是相机采集链路耗时。
    """

    # --------------------------------------------------------
    # Warmup
    # --------------------------------------------------------

    for _ in range(warmup):

        frames = cam.capture_burst(
            1,
            timeout_ms,
        )

        if len(frames) != 1:
            raise RuntimeError(
                f"warmup expected 1 frame, got {len(frames)}"
            )

    # --------------------------------------------------------
    # Actual benchmark
    # --------------------------------------------------------

    values = []

    for i in range(repeat):

        t0 = time.perf_counter()

        frames = cam.capture_burst(
            1,
            timeout_ms,
        )

        t1 = time.perf_counter()

        if len(frames) != 1:
            raise RuntimeError(
                f"expected 1 frame, got {len(frames)}"
            )

        cost_ms = ms(t1 - t0)

        values.append(cost_ms)

        frame = frames[0]

        frame_num = frame_get(
            frame,
            "frame_num",
            -1,
        )

        width = frame_get(
            frame,
            "width",
            0,
        )

        height = frame_get(
            frame,
            "height",
            0,
        )

        frame_len = frame_get(
            frame,
            "frame_len",
            0,
        )

        exposure_us = frame_get(
            frame,
            "exposure_us",
            0.0,
        )

        gain = frame_get(
            frame,
            "gain",
            0.0,
        )

        pixel_type = frame_get(
            frame,
            "pixel_type",
            0,
        )

        average_brightness = frame_get(
            frame,
            "average_brightness",
            0,
        )

        print(
            f"  run={i + 1:02d} | "
            f"capture={cost_ms:8.2f} ms | "
            f"frame_num={frame_num} | "
            f"size={width}x{height} | "
            f"frame_len={frame_len / 1024 / 1024:6.2f} MB | "
            f"exposure={float(exposure_us):8.2f} us | "
            f"gain={float(gain):5.2f} | "
            f"brightness={average_brightness} | "
            f"pixel_type=0x{int(pixel_type):08X}"
        )

    return {
        "avg": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "values": values,
    }


# ============================================================
# Exposure benchmark
# ============================================================

def test_exposure(cam):

    line()
    print("TEST 1: EXPOSURE TIME -> PURE CAPTURE LATENCY")
    line()

    original_param = cam.get_float(
        "ExposureTime"
    )

    original_exposure = float(
        original_param.value
    )

    print(
        f"Original ExposureTime = "
        f"{original_exposure:.2f} us "
        f"({original_exposure / 1000.0:.2f} ms)"
    )

    print(
        f"Exposure range = "
        f"{original_param.min:.2f} ~ "
        f"{original_param.max:.2f} us"
    )

    #
    # 当前生产值 8000us 也包含在测试中
    #
    exposure_list = [
        20000.0,
        10000.0,
        8000.0,
        5000.0,
        2000.0,
    ]

    results = []

    try:

        for exposure_us in exposure_list:

            print()
            print("-" * 80)

            print(
                f"Set ExposureTime = "
                f"{exposure_us:.0f} us "
                f"({exposure_us / 1000.0:.2f} ms)"
            )

            # ------------------------------------------------
            # 设置曝光
            # ------------------------------------------------

            cam.set_exposure(
                exposure_us
            )

            #
            # 给相机节点一点时间生效
            #
            time.sleep(0.1)

            # ------------------------------------------------
            # 重新读取实际值
            # ------------------------------------------------

            actual_param = cam.get_float(
                "ExposureTime"
            )

            actual_exposure = float(
                actual_param.value
            )

            print(
                f"Actual ExposureTime = "
                f"{actual_exposure:.2f} us"
            )

            # ------------------------------------------------
            # Benchmark
            # ------------------------------------------------

            result = benchmark_single(
                cam,
                repeat=10,
                warmup=2,
                timeout_ms=3000,
            )

            results.append(
                (
                    actual_exposure,
                    result,
                )
            )

            print()

            print(
                f"RESULT | "
                f"Exposure={actual_exposure:8.2f} us | "
                f"AVG={result['avg']:8.2f} ms | "
                f"MEDIAN={result['median']:8.2f} ms | "
                f"MIN={result['min']:8.2f} ms | "
                f"MAX={result['max']:8.2f} ms"
            )

    finally:

        # ----------------------------------------------------
        # 恢复原生产曝光
        # ----------------------------------------------------

        print()
        print("-" * 80)

        try:

            cam.set_exposure(
                original_exposure
            )

            time.sleep(0.1)

            actual = cam.get_float(
                "ExposureTime"
            ).value

            print(
                f"Exposure restored: "
                f"{actual:.2f} us"
            )

        except Exception as e:

            print(
                f"WARNING: restore ExposureTime failed: {e}"
            )

    # ========================================================
    # Summary
    # ========================================================

    print()
    line()
    print("EXPOSURE SUMMARY")
    line()

    for exposure_us, result in results:

        exposure_ms = (
            exposure_us / 1000.0
        )

        #
        # 这里只是粗略计算：
        # capture总耗时 - 曝光时间
        #
        # 用于观察剩余固定开销。
        #
        non_exposure_ms = (
            result["avg"]
            - exposure_ms
        )

        effective_fps = (
            1000.0 / result["avg"]
            if result["avg"] > 0
            else 0.0
        )

        print(
            f"Exposure "
            f"{exposure_us:8.0f} us "
            f"({exposure_ms:6.2f} ms)"
            f" -> "
            f"capture_avg={result['avg']:8.2f} ms | "
            f"non_exposure≈{non_exposure_ms:8.2f} ms | "
            f"effective_fps={effective_fps:6.2f}"
        )


# ============================================================
# Burst benchmark
# ============================================================

def benchmark_burst(
    cam,
    count: int,
    repeat: int = 5,
    timeout_ms: int = 3000,
):
    """
    纯 capture_burst 测试。

    注意：
    这里完全不转换、不保存。
    """

    # --------------------------------------------------------
    # Warmup
    # --------------------------------------------------------

    warmup_frames = cam.capture_burst(
        1,
        timeout_ms,
    )

    if len(warmup_frames) != 1:
        raise RuntimeError(
            "burst warmup failed"
        )

    # --------------------------------------------------------
    # Benchmark
    # --------------------------------------------------------

    values = []

    for i in range(repeat):

        t0 = time.perf_counter()

        frames = cam.capture_burst(
            count,
            timeout_ms,
        )

        t1 = time.perf_counter()

        if len(frames) != count:
            raise RuntimeError(
                f"expected {count} frames, "
                f"got {len(frames)}"
            )

        total_ms = ms(
            t1 - t0
        )

        per_frame_ms = (
            total_ms / count
        )

        values.append(
            total_ms
        )

        frame_nums = [
            frame_get(
                frame,
                "frame_num",
                -1,
            )
            for frame in frames
        ]

        exposures = [
            float(
                frame_get(
                    frame,
                    "exposure_us",
                    0.0,
                )
            )
            for frame in frames
        ]

        print(
            f"  run={i + 1:02d} | "
            f"frames={count:2d} | "
            f"total={total_ms:8.2f} ms | "
            f"per_frame={per_frame_ms:8.2f} ms | "
            f"frame_nums={frame_nums} | "
            f"exposure={exposures}"
        )

    avg_total = (
        statistics.mean(values)
    )

    return {
        "avg": avg_total,
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "per_frame": avg_total / count,
    }


def test_burst(cam):

    line()
    print("TEST 2: PURE CAPTURE_BURST PERFORMANCE")
    line()

    current_exposure = float(
        cam.get_float(
            "ExposureTime"
        ).value
    )

    print(
        f"Current ExposureTime = "
        f"{current_exposure:.2f} us "
        f"({current_exposure / 1000.0:.2f} ms)"
    )

    print(
        "No image conversion."
    )

    print(
        "No JPG/PNG/BMP saving."
    )

    print()

    results = {}

    for count in [
        1,
        6,
        8,
    ]:

        print()
        print("-" * 80)

        print(
            f"capture_burst("
            f"count={count}, "
            f"timeout_ms=3000)"
        )

        result = benchmark_burst(
            cam,
            count=count,
            repeat=5,
            timeout_ms=3000,
        )

        results[count] = result

        print()

        print(
            f"RESULT burst={count:2d} | "
            f"AVG={result['avg']:8.2f} ms | "
            f"MEDIAN={result['median']:8.2f} ms | "
            f"MIN={result['min']:8.2f} ms | "
            f"MAX={result['max']:8.2f} ms | "
            f"PER_FRAME={result['per_frame']:8.2f} ms"
        )

    # ========================================================
    # Summary
    # ========================================================

    print()
    line()
    print("BURST SUMMARY")
    line()

    for count, result in results.items():

        effective_fps = (
            1000.0 / result["per_frame"]
            if result["per_frame"] > 0
            else 0.0
        )

        print(
            f"{count:2d} frame(s) | "
            f"total_avg={result['avg']:8.2f} ms | "
            f"per_frame={result['per_frame']:8.2f} ms | "
            f"effective_fps={effective_fps:6.2f}"
        )

    # --------------------------------------------------------
    # 给出与线性估算的对比
    # --------------------------------------------------------

    if 1 in results:

        single = results[1]["avg"]

        print()
        print("Linear comparison:")

        for count in [
            6,
            8,
        ]:

            if count not in results:
                continue

            estimated = (
                single * count
            )

            actual = (
                results[count]["avg"]
            )

            diff = (
                actual - estimated
            )

            print(
                f"{count} frames | "
                f"single*{count}={estimated:.2f} ms | "
                f"actual={actual:.2f} ms | "
                f"difference={diff:+.2f} ms"
            )


# ============================================================
# Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Load native module
    # --------------------------------------------------------

    if len(sys.argv) > 1:

        native_path = Path(
            sys.argv[1]
        ).resolve()

        sys.path.insert(
            0,
            str(native_path),
        )

        print(
            f"native_module_path={native_path}"
        )

    import hikcamera_native

    line()
    print("HIKROBOT PURE CAPTURE PERFORMANCE BENCHMARK")
    line()

    # ========================================================
    # Enum devices
    # ========================================================

    devices = (
        hikcamera_native
        .HikrobotCamera
        .enum_devices()
    )

    print(
        f"device_count={len(devices)}"
    )

    for i, dev in enumerate(devices):

        print(
            f"device[{i}] "
            f"serial={dev.serial} "
            f"model={dev.model} "
            f"transport={dev.transport} "
            f"name={dev.user_defined_name} "
            f"ip={dev.ip}"
        )

    if not devices:

        raise RuntimeError(
            "No camera devices found"
        )

    # ========================================================
    # Use first camera
    # ========================================================

    selected = devices[0]

    print()
    print(
        f"Selected camera: "
        f"serial={selected.serial}, "
        f"model={selected.model}"
    )

    cam = (
        hikcamera_native
        .HikrobotCamera(
            selected.serial
        )
    )

    # ========================================================
    # Open
    # ========================================================

    print()
    print("Opening camera...")

    cam.open()

    print(
        f"is_open={cam.is_open()}"
    )

    try:

        # ====================================================
        # Current camera parameters
        # ====================================================

        print()
        line()
        print("CURRENT CAMERA PARAMETERS")
        line()

        print_float_param(
            cam,
            "ExposureTime",
        )

        print_float_param(
            cam,
            "Gain",
        )

        print_int_param(
            cam,
            "Width",
        )

        print_int_param(
            cam,
            "Height",
        )

        print_int_param(
            cam,
            "OffsetX",
        )

        print_int_param(
            cam,
            "OffsetY",
        )

        # ====================================================
        # TEST 1
        # ====================================================

        print()
        test_exposure(
            cam
        )

        # ====================================================
        # 恢复原曝光以后测试 burst
        # ====================================================

        print()
        test_burst(
            cam
        )

        # ====================================================
        # Finished
        # ====================================================

        print()
        line()
        print("ALL TESTS FINISHED")
        line()

    finally:

        # ====================================================
        # Cleanup
        # ====================================================

        print()
        print("Closing camera...")

        try:

            if cam.is_grabbing():

                cam.stop()

                print(
                    "camera stopped"
                )

        except Exception as e:

            print(
                f"cam.stop warning: {e}"
            )

        try:

            if cam.is_open():

                cam.close()

                print(
                    "camera closed"
                )

        except Exception as e:

            print(
                f"cam.close warning: {e}"
            )


if __name__ == "__main__":
    main()