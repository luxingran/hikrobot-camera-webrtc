from pathlib import Path
import sys
import time


def ms(seconds: float) -> float:
    return seconds * 1000.0


def main() -> None:
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
    try:
        t0 = time.perf_counter()
        frame = cam.capture_burst(1, 3000)[0]
        t1 = time.perf_counter()

        cam.convert_frame(frame, hikcamera_native.PIXEL_FORMATS["BGR8"])
        t2 = time.perf_counter()

        png_path = out_dir / "bench_frame.png"
        bmp_path = out_dir / "bench_frame.bmp"

        cam.save_frame(frame, str(png_path), "png", 3)
        t3 = time.perf_counter()

        cam.save_frame(frame, str(bmp_path), "bmp", 0)
        t4 = time.perf_counter()

        print(f"capture_ms={ms(t1 - t0):.2f}")
        print(f"convert_bgr_ms={ms(t2 - t1):.2f}")
        print(f"save_png_ms={ms(t3 - t2):.2f} size={png_path.stat().st_size}")
        print(f"save_bmp_ms={ms(t4 - t3):.2f} size={bmp_path.stat().st_size}")
        print(f"total_capture_convert_png_ms={ms(t3 - t0):.2f}")
        print(f"total_capture_convert_png_bmp_ms={ms(t4 - t0):.2f}")
    finally:
        cam.stop()
        cam.close()


if __name__ == "__main__":
    main()
