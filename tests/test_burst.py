from pathlib import Path
import sys


def main():
    if len(sys.argv) > 1:
        sys.path.insert(0, str(Path(sys.argv[1]).resolve()))

    import hikcamera_native

    count = 6
    if len(sys.argv) > 2:
        count = int(sys.argv[2])

    devices = hikcamera_native.HikrobotCamera.enum_devices()
    print(f"device_count={len(devices)}")
    if not devices:
        raise RuntimeError("No camera devices found")

    device = devices[0]
    print(
        f"using index={device.index} transport={device.transport} "
        f"model={device.model} serial={device.serial}"
    )

    cam = hikcamera_native.HikrobotCamera(device.serial)
    cam.open()
    print(f"opened=True serial={cam.serial()}")

    frames = cam.capture_burst(count, 3000)
    print(f"burst_count={len(frames)}")

    previous_frame_num = None
    for index, frame in enumerate(frames):
        data_len = len(frame["data"])
        frame_num = frame["frame_num"]
        delta = None if previous_frame_num is None else frame_num - previous_frame_num
        previous_frame_num = frame_num
        print(
            f"frame[{index}]="
            f"width:{frame['width']},"
            f"height:{frame['height']},"
            f"pixel_type:0x{frame['pixel_type']:x},"
            f"frame_num:{frame_num},"
            f"delta:{delta},"
            f"frame_len:{frame['frame_len']},"
            f"data_len:{data_len}"
        )
        if frame["frame_len"] != data_len:
            raise RuntimeError(f"Frame {index} length mismatch")

    cam.stop()
    print("stopped=True")
    cam.close()
    print("closed=True")


if __name__ == "__main__":
    main()
