from __future__ import annotations

from typing import Any

from .camera_resource import CameraResource
from .hikrobot_camera import HikrobotCamera



class CameraManager:


    def __init__(
        self,
        native: Any,
        config: dict
    ):

        self.native = native

        self.cameras: dict[
            str,
            CameraResource
        ] = {}


        self.load_config(config)



    def load_config(
        self,
        config: dict
    ):

        for name, item in config["cameras"].items():

            resource = CameraResource(

                name=name,

                serial=item["serial"],

                transport=item["transport"],

                ip=item.get("ip"),

                stream_width = item.get("stream", {}).get("width"),

                stream_height = item.get("stream", {}).get("height"),

                pixel_format = item.get("pixel_format", "BayerGB8")
                
            )
            self.cameras[name] = resource



    def get(
        self,
        name: str
    ) -> CameraResource:


        if name not in self.cameras:
            raise KeyError(
                f"camera not found:{name}"
            )


        return self.cameras[name]



    def open(self, name:str):

        resource = self.get(name)


        # 已经打开
        if resource.opened:
            print(
                f"{name} already opened"
            )
            return resource.device
        # 防止重复打开
        if not resource.try_lock():
            raise RuntimeError(
                f"Camera {name} is busy"
            )
        try:
            print(
                f"Opening camera {name}"
            )
            camera = HikrobotCamera(
                self.native,
                resource.serial,
                stream_width=resource.stream_width,
                stream_height=resource.stream_height,
                pixel_format =resource.pixel_format
            )
            camera.open(mode="stream")
            resource.device = camera
            resource.opened = True
            return camera
        except RuntimeError as e:
            msg=str(e)
            if "0x80000203" in msg:
                raise RuntimeError(
                    f"""
                        Camera {name} ({resource.serial}) is occupied.

                        Please close:
                        1. MVS Viewer
                        2. Other camera_service process
                        3. Other Python process
                        """
                )
            raise
        finally:
            resource.unlock()


    def open_all(self):

        for name in self.cameras:

            print("==========")
            print("opening:", name)

            try:
                self.open(name)
                print("opened:", name)

            except Exception as e:
                print(
                    "failed:",
                    name,
                    e
                )
                raise



    def close_all(self):

        for cam in self.cameras.values():

            if cam.device:

                cam.device.close()

            cam.opened=False

    def status(self):

        result={}

        for name,camera in self.cameras.items():

            result[name]={

                "serial":camera.serial,

                "transport":camera.transport,

                "opened":camera.opened

            }


        return result