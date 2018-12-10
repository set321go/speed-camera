import cv2
import time
from threading import Thread


class WebcamVideoStream:
    timeout = 12.0

    def __init__(self, config):
        """
        initialize the video camera stream and read the first frame
        from the stream
        """
        self.v_flip = config.WEBCAM_VFLIP
        self.h_flip = config.WEBCAM_HFLIP
        self.CAM_SRC = config.WEBCAM_SRC
        self.CAM_WIDTH = config.WEBCAM_WIDTH
        self.CAM_HEIGHT = config.WEBCAM_HEIGHT
        self.stream = cv2.VideoCapture(config.WEBCAM_SRC)
        self.stream.set(3, config.WEBCAM_WIDTH)
        self.stream.set(4, config.WEBCAM_HEIGHT)
        self.grabbed = None
        self.frame = None
        self.stopped = False
        self.failed = False

    def start(self):
        """ start the thread to read frames from the video stream """
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()

        wait_time = 0.0
        while not self.is_ready() and self.timeout > wait_time:
            wait_time += 0.5
            time.sleep(0.5)

        if self.timeout <= wait_time:
            self.failed = True
            self.stop()

        return self

    def is_ready(self):
        return self.stream.isOpened() and self.grabbed is not None and self.frame is not None

    def update(self):
        """ keep looping infinitely until the thread is stopped """
        while not self.stopped:
            # otherwise, read the next frame from the stream
            (self.grabbed, self.frame) = self.stream.read()
        self.stream.release()

    def read(self):
        """ return the frame most recently read """
        if self.h_flip and self.v_flip:
            return cv2.flip(self.frame, -1)
        elif self.h_flip:
            return cv2.flip(self.frame, 1)
        elif self.v_flip:
            return cv2.flip(self.frame, 0)
        else:
            return self.frame

    def stop(self):
        """ indicate that the thread should be stopped """
        self.stopped = True
