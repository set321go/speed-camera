import logging
import sys
from config import app_constants
import subprocess
import importlib
from importlib import util


def init_logger(config):
    # Now that variables are imported from config.py Setup Logging
    log_level = logging.DEBUG if config.verbose else logging.CRITICAL
    log_format = '%(asctime)s %(levelname)-8s %(funcName)-10s %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    if config.loggingToFile:
        logging.basicConfig(level=log_level,
                            format=log_format,
                            datefmt=date_format,
                            filename=config.logFilePath,
                            filemode='w')
    else:
        logging.basicConfig(level=log_level,
                            format=log_format,
                            datefmt=date_format)


def import_cv2():
    opencv_spec = util.find_spec("cv2")
    if opencv_spec is not None:
        return importlib.import_module("cv2")
    else:
        logging.error("Could Not import cv2 library")
        if sys.version_info > (2, 9):
            logging.error("python3 failed to import cv2")
            logging.error("Try installing opencv for python3")
            logging.error("For RPI See https://github.com/pageauc/opencv3-setup")
        else:
            logging.error("python2 failed to import cv2")
            logging.error("Try RPI Install per command")
            logging.error("%s %s Exiting Due to Error", app_constants.progName, app_constants.progVer)
        sys.exit(1)


def import_picam(config):
    picam_spec = util.find_spec("picamera")

    if picam_spec is None:
        config.WEBCAM = True

    if not config.WEBCAM:
        # Check that pi camera module is installed and enabled
        camResult = subprocess.check_output("vcgencmd get_camera", shell=True)
        camResult = camResult.decode("utf-8")
        camResult = camResult.replace("\n", "")
        if (camResult.find("0")) >= 0:   # -1 is zero not found. Cam OK
            logging.error("Pi Camera Module Not Found %s", camResult)
            logging.error("if supported=0 Enable Camera per command sudo raspi-config")
            logging.error("if detected=0 Check Pi Camera Module is Installed Correctly")
            logging.error("%s %s Exiting Due to Error", app_constants.progName, app_constants.progVer)
            sys.exit(1)
        else:
            logging.info("Pi Camera Module is Enabled and Connected %s", camResult)
