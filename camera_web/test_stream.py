import time
import json

from camera.native_loader import import_native
from camera.camera_manager import CameraManager


native = import_native(
    "D:/camera_service_native/build_py311"
)
def test_camera(camera_name, duration=30):
    camera = manager.get(camera_name)
    cam = camera.device
    print(f"\nTesting {camera_name}")
    cam.start()
    count = 0
    start_time = time.time()
    last_time = start_time
    try:
        while True:
            frame = cam.grab_frame(
                timeout_ms=3000
            )
            # raw = camera.grab_frame()

            # bgr = cam.convert_frame(
            #     frame,
            #     native.PIXEL_FORMATS["BGR8"]
            # )
            # # print(
            #     len("数据长度", bgr["data"])
            # )
            # cam.save_frame(
            #     bgr,
            #     "test.jpg",
            #     "jpg",
            #     90
            # )
            count += 1
            now = time.time()
            # 每秒打印一次
            if now - last_time >= 1:

                fps = count / (
                    now - start_time
                )

                print(
                    camera_name,
                    # "frames:",
                    # count,
                    "fps:",
                    round(fps,2),
                    "size:",
                    frame["width"],
                    frame["height"],
                    # "keys",
                    # frame.keys(),
                    # "pixel_type",
                    # frame["pixel_type"]
                )
                last_time = now
            if now - start_time > duration:
                break


    finally:

        cam.stop()


    print(
        camera_name,
        "finished"
    )





with open(
    "config.json",
    "r",
    encoding="utf8"
) as f:

    config=json.load(f)



manager = CameraManager(
    native,
    config
)


manager.open_all()


import threading


t1 = threading.Thread(
    target=test_camera,
    args=("usb_side",20)
)


t2 = threading.Thread(
    target=test_camera,
    args=("gige_top",20)
)


t1.start()
t2.start()


t1.join()
t2.join()