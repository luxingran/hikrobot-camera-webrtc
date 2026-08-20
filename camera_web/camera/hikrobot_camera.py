from __future__ import annotations

from typing import Any


class HikrobotCamera:

    def __init__(
        self,
        native: Any,
        serial: str,
        stream_width=None,
        stream_height=None,
        pixel_format=None
    ):
        self.native = native
        self.serial = serial

        self.stream_width = stream_width
        self.stream_height = stream_height
        self.pixel_format = pixel_format
        self.cam = native.HikrobotCamera(
            serial
        )

    def open(
        self,
        mode="stream"
    ):

        if not self.cam.is_open():

            self.cam.open()


        if mode == "stream":

            self.configure_stream_mode()


    def close(self):

        if self.cam.is_grabbing():

            self.stop()


        if self.cam.is_open():

            self.cam.close()


    def start(self):

        if not self.cam.is_grabbing():

            self.cam.start()


    def stop(self):

        if self.cam.is_grabbing():

            self.cam.stop()


    def grab_frame(
        self,
        timeout_ms=3000
    ):

        if not self.cam.is_grabbing():

            self.start()


        return self.cam.get_frame(
            timeout_ms
        )


    def capture_one(
        self,
        timeout_ms=3000
    ):

        return self.cam.capture_burst(
            1,
            timeout_ms
        )[0]
    def configure_stream_mode(self):

        # 关闭触发模式
        self.cam.set_enum(
            "TriggerMode",
            0
        )

        if self.pixel_format:

            try:
                self.cam.set_pixel_format(
                    self.native.PIXEL_FORMATS[
                        self.pixel_format
                    ]
                )

            except Exception as e:
                print(
                    f"pixel format set failed, keep default: {e}"
                )

        if self.stream_width and self.stream_height:

            print(
                f"stream roi {self.stream_width}x{self.stream_height}"
            )

            self.cam.set_roi(

                self.stream_width,
                self.stream_height,
                0,
                0,
            )

    def convert_frame(self,frame,pixel_format):

        converted = self.cam.convert_frame(
        frame,
        pixel_format
        )   

        converted["frame_num"] = frame.get(
        "frame_num",
        0
        )
        if "frame_len" not in converted:
            converted["frame_len"] = converted.get(
                "data_len",
                len(converted["data"])
            )
        return converted
    
    def save_frame(self,frame,path,image_format="jpg",quality=90):
        return self.cam.save_frame(
            frame,
            path,
            image_format,
            quality
        )

    def set_roi(self, width, height):

        self.cam.set_roi(

            width,
            height,
            0,
            0,

        )