from camera.native_loader import import_native
from camera.camera_manager import CameraManager

import json
from stream.stream_manager import StreamManager
import time
def main():

    native = import_native(
        "D:/camera_service_native/build_py311"
    )
    print(
    dir(native.HikrobotCamera)
    )   
    devices = native.HikrobotCamera.enum_devices()

    for d in devices:
        print(
            d.serial,
            d.transport
        )

    with open(
        "config.json",
        "r",
        encoding="utf-8"
    ) as f:

        config=json.load(f)


    manager = CameraManager(
        native,
        config
    )


    manager.open_all()

    usb = manager.get("usb_side")
    gige = manager.get("gige_top")


    usb.device.start()
    gige.device.start()

    # count = 0
    # while True:

    #     frame1 = usb.device.grab_frame()
    #     print("usb OK get grame")
    #     frame2 = gige.device.grab_frame()
    #     print("gige OK get grame")
    #     count +=1
    #     if count == 100:
    #         break
    stream = StreamManager(
        manager
    )

    stream.add_camera(
        "usb_side"
    )


    stream.add_camera(
        "gige_top"
    )


    stream.start_all()



    while True:


        usb = stream.get_frame(
            "usb_side"
        )


        gige = stream.get_frame(
            "gige_top"
        )


        print(
            "USB:",
            usb["frame_count"],
            "GIGE:",
            gige["frame_count"]
        )


        time.sleep(1)

if __name__=="__main__":
    main()