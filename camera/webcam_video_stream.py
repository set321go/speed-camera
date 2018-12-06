import cv2
from threading import Thread


class WebcamVideoStream:
    def __init__(self, config):
        """
        initialize the video camera stream and read the first frame
        from the stream
        """
        self.CAM_SRC = config.WEBCAM_SRC
        self.CAM_WIDTH = config.WEBCAM_WIDTH
        self.CAM_HEIGHT = config.WEBCAM_HEIGHT
        self.stream = cv2.VideoCapture(config.WEBCAM_SRC)
        self.stream.set(3, config.WEBCAM_WIDTH)
        self.stream.set(4, config.WEBCAM_HEIGHT)
        (self.grabbed, self.frame) = self.stream.read()
        # initialize the variable used to indicate if the thread should
        # be stopped
        self.stopped = False

    def start(self):
        """ start the thread to read frames from the video stream """
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        """ keep looping infinitely until the thread is stopped """
        while True:
            # if the thread indicator variable is set, stop the thread
            if self.stopped:
                return
            # otherwise, read the next frame from the stream
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        """ return the frame most recently read """
        return self.frame

    def stop(self):
        """ indicate that the thread should be stopped """
        self.stopped = True
