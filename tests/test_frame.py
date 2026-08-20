from pathlib import Path
import sys
import time


def line():
    print("=" * 80)


def read_float(cam, name):
    try:
        p = cam.get_float(name)
        print(
            f"{name}: "
            f"value={p.value}, "
            f"min={p.min}, "
            f"max={p.max}"
        )
        return p
    except Exception as e:
        print(f"{name}: NOT AVAILABLE -> {e}")
        return None


def read_int(cam, name):
    try:
        p = cam.get_int(name)
        print(
            f"{name}: "
            f"value={p.value}, "
            f"min={p.min}, "
            f"max={p.max}, "
            f"inc={p.increment}"
        )
        return p
    except Exception as e:
        print(f"{name}: NOT AVAILABLE -> {e}")
        return None


def benchmark_direct(cam, repeat=10):
    """
    不调用 capture_burst。
    直接测试：

        trigger()
        get_frame()

    用来排除 capture_burst() 自己是否有 sleep。
    """

    line()
    print("DIRECT trigger() + get_frame() TEST")
    line()

    values = []

    for i in range(repeat):

        t0 = time.perf_counter()

        # 软件触发
        t_trigger0 = time.perf_counter()
        cam.trigger()
        t_trigger1 = time.perf_counter()

        # 等待图像
        t_get0 = time.perf_counter()
        frame = cam.get_frame(3000)
        t_get1 = time.perf_counter()

        total_ms = (t_get1 - t0) * 1000.0
        trigger_ms = (t_trigger1 - t_trigger0) * 1000.0
        get_ms = (t_get1 - t_get0) * 1000.0

        values.append(total_ms)

        print(
            f"run={i + 1:02d} | "
            f"trigger={trigger_ms:8.2f} ms | "
            f"get_frame={get_ms:8.2f} ms | "
            f"total={total_ms:8.2f} ms"
        )

    avg = sum(values) / len(values)

    print()
    print(
        f"DIRECT AVG = {avg:.2f} ms "
        f"({1000.0 / avg:.2f} FPS)"
    )

    return avg


def benchmark_burst(cam, repeat=5):
    """
    对比 capture_burst(1)
    """

    line()
    print("capture_burst(1) TEST")
    line()

    values = []

    for i in range(repeat):

        t0 = time.perf_counter()

        frames = cam.capture_burst(
            1,
            3000,
        )

        t1 = time.perf_counter()

        elapsed = (t1 - t0) * 1000.0

        values.append(elapsed)

        print(
            f"run={i + 1:02d} | "
            f"capture_burst={elapsed:8.2f} ms | "
            f"frames={len(frames)}"
        )

    avg = sum(values) / len(values)

    print()
    print(
        f"BURST AVG = {avg:.2f} ms "
        f"({1000.0 / avg:.2f} FPS)"
    )

    return avg


def main():

    if len(sys.argv) > 1:
        sys.path.insert(
            0,
            str(Path(sys.argv[1]).resolve())
        )

    import hikcamera_native

    line()
    print("HIKROBOT FRAME RATE LIMIT DIAGNOSTIC")
    line()

    devices = (
        hikcamera_native
        .HikrobotCamera
        .enum_devices()
    )

    print(f"device_count={len(devices)}")

    if not devices:
        raise RuntimeError("No camera found")

    dev = devices[0]

    print(
        f"serial={dev.serial} "
        f"model={dev.model} "
        f"transport={dev.transport}"
    )

    cam = hikcamera_native.HikrobotCamera(
        dev.serial
    )

    cam.open()

    try:

        # ====================================================
        # 当前参数
        # ====================================================

        line()
        print("CURRENT PARAMETERS")
        line()

        read_float(
            cam,
            "ExposureTime"
        )

        read_float(
            cam,
            "Gain"
        )

        read_float(
            cam,
            "AcquisitionFrameRate"
        )

        #
        # 不同型号可能叫不同名字，所以一起试
        #
        read_float(
            cam,
            "ResultingFrameRate"
        )

        read_float(
            cam,
            "ResultingFrameRateAbs"
        )

        read_float(
            cam,
            "AcquisitionResultingFrameRate"
        )

        read_float(
            cam,
            "AcquisitionResultingFrameRateAbs"
        )

        print()

        read_int(
            cam,
            "Width"
        )

        read_int(
            cam,
            "Height"
        )

        # ====================================================
        # 确保进入软件触发模式
        # ====================================================

        line()
        print("CONFIG SOFTWARE TRIGGER")
        line()

        cam.configure_software_trigger()

        print("configure_software_trigger() OK")

        #
        # 如果 capture_burst 内部会自己 start，
        # start 已经开始也没关系；
        # 防止目前只是 open 状态。
        #
        try:
            cam.start()
            print("start() OK")
        except Exception as e:
            print(f"start(): {e}")

        # ====================================================
        # 关键测试1：
        #
        # 完全绕开 capture_burst
        # ====================================================

        direct_avg = benchmark_direct(
            cam,
            repeat=10,
        )

        # ====================================================
        # 关键测试2：
        #
        # capture_burst(1)
        # ====================================================

        burst_avg = benchmark_burst(
            cam,
            repeat=5,
        )

        # ====================================================
        # 最终诊断
        # ====================================================

        print()
        line()
        print("DIAGNOSIS")
        line()

        print(
            f"direct trigger+get_frame = "
            f"{direct_avg:.2f} ms"
        )

        print(
            f"capture_burst(1)         = "
            f"{burst_avg:.2f} ms"
        )

        diff = burst_avg - direct_avg

        print(
            f"difference               = "
            f"{diff:+.2f} ms"
        )

        print()

        if diff > 300:

            print(
                "LIKELY: capture_burst() 内部存在额外等待 / sleep。"
            )

        elif direct_avg > 400:

            print(
                "LIKELY: 相机自身帧率/触发周期被限制在约 2 FPS。"
            )

        else:

            print(
                "Direct capture is significantly faster; "
                "continue checking burst implementation."
            )

    finally:

        try:
            if cam.is_grabbing():
                cam.stop()
        except Exception:
            pass

        try:
            if cam.is_open():
                cam.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()