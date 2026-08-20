from pathlib import Path
import sys
import time
import statistics


TEST_THROUGHPUT = 100_000_000
# 先测试 100 MB/s。
#
# 如果现在确实是 37.5 MB/s 限制：
#
# 当前：
#   19.96 MB / 37.5 MB/s
#   ≈ 532 ms/frame
#
# 改 100 MB/s 后理论约：
#   19.96 MB / 100 MB/s
#   ≈ 200 ms/frame
#
# 先不要直接冲到最大值。


def line():
    print("=" * 80)


def get_int_safe(cam, name):
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
        print(
            f"{name}: NOT AVAILABLE -> {e}"
        )

        return None


def get_float_safe(cam, name):
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
        print(
            f"{name}: NOT AVAILABLE -> {e}"
        )

        return None


def get_enum_safe(cam, name):
    try:
        p = cam.get_enum(name)

        print(
            f"{name}: "
            f"value={p.value}, "
            f"supported={list(p.supported_values)}"
        )

        return p

    except Exception as e:
        print(
            f"{name}: NOT AVAILABLE -> {e}"
        )

        return None


def align_value(value, minimum, maximum, increment):
    value = max(minimum, min(value, maximum))

    if increment <= 0:
        return value

    return (
        minimum
        + ((value - minimum) // increment)
        * increment
    )


def benchmark_direct(
    cam,
    repeat=8,
    timeout_ms=3000,
):
    values = []

    print()
    line()
    print("DIRECT trigger() + get_frame()")
    line()

    #
    # 第一帧预热
    #
    cam.trigger()
    cam.get_frame(timeout_ms)

    for i in range(repeat):

        t0 = time.perf_counter()

        t_trigger0 = time.perf_counter()

        cam.trigger()

        t_trigger1 = time.perf_counter()

        t_get0 = time.perf_counter()

        frame = cam.get_frame(
            timeout_ms
        )

        t_get1 = time.perf_counter()

        trigger_ms = (
            t_trigger1 - t_trigger0
        ) * 1000.0

        get_ms = (
            t_get1 - t_get0
        ) * 1000.0

        total_ms = (
            t_get1 - t0
        ) * 1000.0

        values.append(total_ms)

        print(
            f"run={i + 1:02d} | "
            f"trigger={trigger_ms:8.2f} ms | "
            f"get_frame={get_ms:8.2f} ms | "
            f"total={total_ms:8.2f} ms"
        )

    avg = statistics.mean(values)
    median = statistics.median(values)

    print()

    print(
        f"AVG    = {avg:.2f} ms"
    )

    print(
        f"MEDIAN = {median:.2f} ms"
    )

    print(
        f"FPS    = {1000.0 / avg:.2f}"
    )

    return avg


def print_bandwidth_info(cam):

    line()
    print("CAMERA BANDWIDTH PARAMETERS")
    line()

    #
    # 最关键
    #
    throughput_limit = get_int_safe(
        cam,
        "DeviceLinkThroughputLimit",
    )

    get_int_safe(
        cam,
        "DeviceLinkCurrentThroughput",
    )

    #
    # 一帧实际 payload
    #
    payload = get_int_safe(
        cam,
        "PayloadSize",
    )

    #
    # 有些型号可能存在
    #
    get_int_safe(
        cam,
        "DeviceLinkSpeed",
    )

    print()

    acquisition_fps = get_float_safe(
        cam,
        "AcquisitionFrameRate",
    )

    resulting_fps = get_float_safe(
        cam,
        "ResultingFrameRate",
    )

    #
    # 尝试一些可能存在的节点
    #
    get_float_safe(
        cam,
        "DeviceLinkCurrentThroughput",
    )

    print()

    get_enum_safe(
        cam,
        "DeviceLinkThroughputLimitMode",
    )

    #
    # 根据实际值计算
    #
    if payload is not None:

        payload_bytes = int(
            payload.value
        )

        print()
        print(
            f"PayloadSize = "
            f"{payload_bytes:,} bytes "
            f"= {payload_bytes / 1024 / 1024:.2f} MiB"
        )

        if resulting_fps is not None:

            real_fps = float(
                resulting_fps.value
            )

            calculated_bw = (
                payload_bytes
                * real_fps
            )

            print(
                f"PayloadSize × ResultingFrameRate"
            )

            print(
                f"= {payload_bytes:,} "
                f"× {real_fps:.6f}"
            )

            print(
                f"= {calculated_bw:,.0f} bytes/s"
            )

            print(
                f"= {calculated_bw / 1_000_000:.2f} MB/s"
            )

            print(
                f"= {calculated_bw / 1024 / 1024:.2f} MiB/s"
            )

    return throughput_limit


def main():

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
    print("HIKROBOT USB BANDWIDTH DIAGNOSTIC")
    line()

    devices = (
        hikcamera_native
        .HikrobotCamera
        .enum_devices()
    )

    print(
        f"device_count={len(devices)}"
    )

    if not devices:

        raise RuntimeError(
            "No camera found"
        )

    dev = devices[0]

    print(
        f"serial={dev.serial}"
    )

    print(
        f"model={dev.model}"
    )

    print(
        f"transport={dev.transport}"
    )

    cam = (
        hikcamera_native
        .HikrobotCamera(
            dev.serial
        )
    )

    cam.open()

    original_limit = None

    try:

        # ====================================================
        # 1. 当前参数
        # ====================================================

        print()
        line()
        print("STEP 1: CURRENT STATUS")
        line()

        throughput_param = (
            print_bandwidth_info(
                cam
            )
        )

        if throughput_param is not None:

            original_limit = int(
                throughput_param.value
            )

            print()
            print(
                f">>> Current DeviceLinkThroughputLimit "
                f"= {original_limit:,} bytes/s"
            )

        # ====================================================
        # 2. 当前速度
        # ====================================================

        print()
        line()
        print("STEP 2: CURRENT CAPTURE SPEED")
        line()

        cam.configure_software_trigger()

        cam.start()

        before_ms = benchmark_direct(
            cam,
            repeat=6,
        )

        cam.stop()

        # ====================================================
        # 如果没有吞吐限制节点
        # ====================================================

        if throughput_param is None:

            print()
            line()
            print("DeviceLinkThroughputLimit NOT AVAILABLE")
            line()

            print(
                "无法通过该节点继续测试。"
            )

            print(
                "重点检查 USB 端口 / USB Hub / 数据线 / USB协商速度。"
            )

            return

        # ====================================================
        # 3. 修改吞吐限制
        # ====================================================

        line()
        print("STEP 3: CHANGE THROUGHPUT LIMIT")
        line()

        target = align_value(
            TEST_THROUGHPUT,
            int(throughput_param.min),
            int(throughput_param.max),
            int(throughput_param.increment),
        )

        print(
            f"Current limit : "
            f"{original_limit:,} bytes/s"
        )

        print(
            f"Target limit  : "
            f"{target:,} bytes/s"
        )

        if target == original_limit:

            print(
                "Target equals current value. "
                "Nothing to change."
            )

        else:

            print(
                "Setting DeviceLinkThroughputLimit..."
            )

            cam.set_int(
                "DeviceLinkThroughputLimit",
                target,
            )

            time.sleep(0.2)

        # ====================================================
        # 4. 修改后重新读取
        # ====================================================

        print()
        line()
        print("STEP 4: STATUS AFTER CHANGE")
        line()

        print_bandwidth_info(
            cam
        )

        # ====================================================
        # 5. 修改后的拍照速度
        # ====================================================

        print()
        line()
        print("STEP 5: CAPTURE AFTER CHANGE")
        line()

        cam.configure_software_trigger()

        cam.start()

        after_ms = benchmark_direct(
            cam,
            repeat=8,
        )

        cam.stop()

        # ====================================================
        # 6. Summary
        # ====================================================

        print()
        line()
        print("SUMMARY")
        line()

        print(
            f"BEFORE:"
        )

        print(
            f"  capture = {before_ms:.2f} ms"
        )

        print(
            f"  FPS     = {1000.0 / before_ms:.2f}"
        )

        print()

        print(
            f"AFTER:"
        )

        print(
            f"  capture = {after_ms:.2f} ms"
        )

        print(
            f"  FPS     = {1000.0 / after_ms:.2f}"
        )

        print()

        improvement = (
            before_ms / after_ms
            if after_ms > 0
            else 0
        )

        print(
            f"Speed improvement = "
            f"{improvement:.2f}x"
        )

    finally:

        #
        # 恢复原来的 throughput limit
        #
        try:

            if cam.is_grabbing():
                cam.stop()

        except Exception:
            pass

        if original_limit is not None:

            try:

                cam.set_int(
                    "DeviceLinkThroughputLimit",
                    original_limit,
                )

                print()
                print(
                    f"DeviceLinkThroughputLimit restored "
                    f"to {original_limit:,}"
                )

            except Exception as e:

                print(
                    f"WARNING: restore throughput failed: {e}"
                )

        try:

            if cam.is_open():
                cam.close()

        except Exception:
            pass


if __name__ == "__main__":
    main()