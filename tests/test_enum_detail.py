from pathlib import Path
import sys


def main() -> None:
    if len(sys.argv) > 1:
        sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent))

    import hikcamera_native

    devices = hikcamera_native.HikrobotCamera.enum_devices()
    print(f"device_count={len(devices)}")
    for device in devices:
        print(
            f"index={device.index} "
            f"transport={device.transport} "
            f"model={device.model} "
            f"serial={device.serial} "
            f"user_defined_name={device.user_defined_name} "
            f"ip={device.ip}"
        )


if __name__ == "__main__":
    main()
