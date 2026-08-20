# stream/camera_worker.py

from __future__ import annotations

import threading
import time

class CameraWorker:

    def __init__(
        self,
        name,
        camera,
        latest_frame
    ):

        self.name = name

        self.camera = camera

        self.latest_frame = latest_frame


        self.running = False

        self.thread = None



    def start(self):

        if self.running:
            return


        self.running = True


        self.thread = threading.Thread(

            target=self.run,

            daemon=True

        )

        self.thread.start()

    def stop(self):

        self.running = False

    def run(self):

        print(
            f"{self.name} worker start"
        )


        camera = self.camera


        camera.start()


        while self.running:

            try:

                frame = camera.grab_frame(
                    timeout_ms=3000
                )


                self.latest_frame.update(
                    frame
                )


            except Exception as e:


                print(
                    self.name,
                    "error:",
                    e
                )

                self.latest_frame.set_error(
                    str(e)
                )
                time.sleep(0.1)
        camera.stop()
        print(
            f"{self.name} worker stop"
        )