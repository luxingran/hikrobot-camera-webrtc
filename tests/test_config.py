from pathlib import Path
import sys


def describe_int(name, value):
    print(
        f"{name}=value:{value.value},min:{value.min},"
        f"max:{value.max},inc:{value.increment}"
    )


def describe_float(name, value):
    print(f"{name}=value:{value.value:.3f},min:{value.min:.3f},max:{value.max:.3f}")


def main():
    if len(sys.argv) > 1:
        sys.path.insert(0, str(Path(sys.argv[1]).resolve()))

    import hikcamera_native

    devices = hikcamera_native.HikrobotCamera.enum_devices()
    print(f"device_count={len(devices)}")
    if not devices:
        raise RuntimeError("No camera devices found")

    cam = hikcamera_native.HikrobotCamera(devices[0].serial)
    cam.open()
    print(f"opened=True serial={cam.serial()}")

    describe_float("ExposureTime.before", cam.get_float("ExposureTime"))
    describe_float("Gain.before", cam.get_float("Gain"))
    describe_int("Width.before", cam.get_int("Width"))
    describe_int("Height.before", cam.get_int("Height"))
    describe_int("OffsetX.before", cam.get_int("OffsetX"))
    describe_int("OffsetY.before", cam.get_int("OffsetY"))
    pixel_format = cam.get_enum("PixelFormat")
    print(
        f"PixelFormat.before=value:0x{pixel_format.value:x},"
        f"supported:{[hex(v) for v in pixel_format.supported_values[:12]]}"
    )
    print(f"KnownPixelFormats={hikcamera_native.PIXEL_FORMATS}")

    width = cam.get_int("Width")
    height = cam.get_int("Height")
    cam.set_roi(width.value, height.value, 0, 0)
    cam.set_exposure(cam.get_float("ExposureTime").value)
    cam.set_gain(cam.get_float("Gain").value)
    cam.set_pixel_format(pixel_format.value)
    print("set_same_parameters=True")

    frames = cam.capture_burst(2, 3000)
    print(f"burst_count={len(frames)}")
    for index, frame in enumerate(frames):
        print(
            f"frame[{index}]=width:{frame['width']},height:{frame['height']},"
            f"pixel_type:0x{frame['pixel_type']:x},frame_len:{frame['frame_len']},"
            f"data_len:{len(frame['data'])}"
        )

    cam.stop()
    cam.close()
    print("closed=True")


if __name__ == "__main__":
    main()
