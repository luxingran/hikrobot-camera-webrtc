# stream/stream_manager.py

from __future__ import annotations

from .latest_frame import LatestFrame
from .camera_worker import CameraWorker



class StreamManager:


    def __init__(
        self,
        camera_manager
    ):

        self.camera_manager = camera_manager


        self.workers = {}

        self.frames = {}

    def add_camera(
        self,
        camera_name
    ):


        resource = self.camera_manager.get(
            camera_name
        )
        print( "resource.device",
                resource.device
                )


        if not resource.device:

            raise RuntimeError(
                f"{camera_name} not opened"
            )


        latest = LatestFrame()


        worker = CameraWorker(

            camera_name,

            resource.device,

            latest

        )


        self.frames[camera_name] = latest


        self.workers[camera_name] = worker



    def start_all(self):

        for worker in self.workers.values():

            worker.start()



    def get_frame(
        self,
        camera_name
    ):

        return self.frames[
            camera_name
        ].snapshot()



    def stop_all(self):

        for worker in self.workers.values():

            worker.stop()