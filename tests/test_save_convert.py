from pathlib import Path
import sys


def main():
    if len(sys.argv) > 1:
        sys.path.insert(0, str(Path(sys.argv[1]).resolve()))

    import hikcamera_native

    out_dir = Path(r"D:\camera_service_native\out")
    out_dir.mkdir(parents=True, exist_ok=True)

    devices = hikcamera_native.HikrobotCamera.enum_devices()
    print(f"device_count={len(devices)}")
    if not devices:
        raise RuntimeError("No camera devices found")

    cam = hikcamera_native.HikrobotCamera(devices[0].serial)
    cam.open()
    print(f"opened=True serial={cam.serial()}")

    frame = cam.capture_burst(1, 3000)[0]
    print(
        f"raw=width:{frame['width']},height:{frame['height']},"
        f"pixel_type:0x{frame['pixel_type']:x},frame_len:{frame['frame_len']},"
        f"data_len:{len(frame['data'])}"
    )

    bgr = cam.convert_frame(frame, hikcamera_native.PIXEL_FORMATS["BGR8"])
    print(
        f"bgr=width:{bgr['width']},height:{bgr['height']},"
        f"pixel_type:0x{bgr['pixel_type']:x},data_len:{bgr['data_len']},"
        f"bytes:{len(bgr['data'])}"
    )

    png_path = out_dir / "burst_frame_0.png"
    bmp_path = out_dir / "burst_frame_0.bmp"
    cam.save_frame(frame, str(png_path), "png", 3)
    cam.save_frame(frame, str(bmp_path), "bmp", 0)

    print(f"saved_png={png_path} exists={png_path.exists()} size={png_path.stat().st_size if png_path.exists() else 0}")
    print(f"saved_bmp={bmp_path} exists={bmp_path.exists()} size={bmp_path.stat().st_size if bmp_path.exists() else 0}")

    cam.stop()
    cam.close()
    print("closed=True")


if __name__ == "__main__":
    main()
