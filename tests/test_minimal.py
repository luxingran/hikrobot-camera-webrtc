from pathlib import Path
import sys


def main():
    if len(sys.argv) > 1:
        sys.path.insert(0, str(Path(sys.argv[1]).resolve()))

    import hikcamera_native

    devices = hikcamera_native.HikrobotCamera.enum_devices()
    print(f"device_count={len(devices)}")
    for device in devices:
        print(
            f"device index={device.index} transport={device.transport} "
            f"model={device.model} serial={device.serial}"
        )

    if not devices:
        raise RuntimeError("No camera devices found")

    cam = hikcamera_native.HikrobotCamera(devices[0].serial)
    cam.open()
    print(f"opened=True serial={cam.serial()}")

    cam.start()
    print("started=True")

    frame = cam.get_frame(3000)
    print(
        "frame="
        f"width:{frame['width']},"
        f"height:{frame['height']},"
        f"pixel_type:0x{frame['pixel_type']:x},"
        f"frame_num:{frame['frame_num']},"
        f"frame_len:{frame['frame_len']},"
        f"data_len:{len(frame['data'])}"
    )

    cam.stop()
    print("stopped=True")

    cam.close()
    print("closed=True")


if __name__ == "__main__":
    main()
