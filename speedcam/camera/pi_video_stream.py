import logging
import sys
import time
from threading import Thread
from config import app_constants
from picamera import PiCamera


class PiVideoStream:
    def __init__(self, config):
        """ initialize the camera and stream """
        try:
            self.camera = PiCamera()
        except:
            logging.error("PiCamera Already in Use by Another Process")
            logging.error("%s %s Exiting Due to Error", app_constants.progName, app_constants.progVer)
            sys.exit(1)
        self.camera.resolution = (config.CAMERA_WIDTH, config.CAMERA_HEIGHT)
        self.camera.rotation = config.CAMERA_ROTATION
        self.camera.framerate = config.CAMERA_FRAMERATE
        self.camera.hflip = config.CAMERA_HFLIP
        self.camera.vflip = config.CAMERA_VFLIP
        self.rawCapture = picamera.array.PiRGBArray(self.camera, size=self.camera.resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture,
                                                     format="bgr",
                                                     use_video_port=True)
        """
        initialize the frame and the variable used to indicate
        if the thread should be stopped
        """
        self.frame = None
        self.stopped = False
        self.frame_count = -1
        self.fps_time = time.time()

    def start(self):
        """ start the thread to read frames from the video stream """
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        """ keep looping infinitely until the thread is stopped """
        for f in self.stream:
            # grab the frame from the stream and clear the stream in
            # preparation for the next frame
            self.frame = f.array
            self.rawCapture.truncate(0)

            # if the thread indicator variable is set, stop the thread
            # and resource camera resources
            if self.stopped:
                self.stream.close()
                self.rawCapture.close()
                self.camera.close()
                return

    def read(self):
        """ return the frame most recently read """
        return self.frame

    def stop(self):
        """ indicate that the thread should be stopped """
        self.stopped = True

    def get_fps(self):
        """ Calculate and display frames per second processing """
        fps = -1
        if self.frame_count < 0:
            self.frame_count = 1
            self.fps_time = time.time()
        if self.frame_count >= 1000:
            duration = float(time.time() - self.fps_time)
            fps = float(self.frame_count / duration)
            self.frame_count = 0
            self.fps_time = time.time()
        else:
            self.frame_count += 1
        return fps
