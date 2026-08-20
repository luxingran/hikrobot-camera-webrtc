class FrameConverter:


    def __init__(
        self,
        native,
        camera
    ):

        self.native = native
        self.camera = camera



    def to_bgr(
        self,
        frame
    ):

        return self.camera.convert_frame(
            frame,
            self.native.PIXEL_FORMATS["BGR8"]
        )