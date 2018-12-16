import cv2
import logging
import importlib
import time
from config.app_constants import APP_NAME, VERSION

# Color data for OpenCV lines and text
cvWhite = (255, 255, 255)
cvBlack = (0, 0, 0)
cvBlue = (255, 0, 0)
cvGreen = (0, 255, 0)
cvRed = (0, 0, 255)


def speed_image_add_lines(config, image, color):
    cv2.line(image, (config.x_left, config.y_upper),
             (config.x_right, config.y_upper), color, 1)
    cv2.line(image, (config.x_left, config.y_lower),
             (config.x_right, config.y_lower), color, 1)
    cv2.line(image, (config.x_left, config.y_upper),
             (config.x_left, config.y_lower), color, 1)
    cv2.line(image, (config.x_right, config.y_upper),
             (config.x_right, config.y_lower), color, 1)
    return image


def connect_to_stream(config):
    if config.WEBCAM:
        logging.info("Initializing USB Web Camera ..")
        # Start video stream on a processor Thread for faster speed
        webcam_module = importlib.import_module("speedcam.camera.webcam_video_stream")
        vs = webcam_module.WebcamVideoStream(config).start()

        if vs.failed:
            logging.error("USB Web Cam Not Connecting to WEBCAM_SRC %i", config.WEBCAM_SRC)
            logging.error("Check Camera is Plugged In and Working on Specified SRC")
            logging.error("and Not Used(busy) by Another Process.")
            logging.error("%s %s Exiting Due to Error", APP_NAME, VERSION)
    else:
        logging.info("Initializing Pi Camera ....")
        picam_module = importlib.import_module("speedcam.camera.pi_video_stream")
        # Start a pi-camera video stream thread
        vs = picam_module.PiVideoStream(config).start()
        time.sleep(2.0)  # Allow PiCamera to initialize

    return vs
