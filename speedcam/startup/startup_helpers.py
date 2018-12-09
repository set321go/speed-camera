import logging
import sys
import os
from config import app_constants
import subprocess
import importlib
from importlib import util


def init_boot_logger():
    # Boot logger for logging before we have loaded configuration data
    logging.basicConfig(level=logging.DEBUG,
                        format='%(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')


def init_logger(config):
    if config.gui_window_on:
        logging.info("Press lower case q on OpenCV GUI Window to Quit program or ctrl-c in this terminal session to Quit")
    else:
        logging.info("Press ctrl-c in this terminal session to Quit")
    logging.info("Boot complete, starting application logger")
    logging.info("----------------------------------------------------------------------")
    # Remove the boot logger that was not configured
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Now that variables are imported from config.py Setup Logging
    log_level = logging.DEBUG if config.verbose else logging.ERROR
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


def create_dir(config):
    cwd = os.getcwd()
    html_path = "media/html"
    if not os.path.isdir(config.image_path):
        logging.info("Creating Image Storage Folder %s", config.image_path)
        os.makedirs(config.image_path)
    os.chdir(config.image_path)
    os.chdir(cwd)
    if config.imageRecentMax > 0:
        if not os.path.isdir(config.imageRecentDir):
            logging.info("Create Recent Folder %s", config.imageRecentDir)
            try:
                os.makedirs(config.imageRecentDir)
            except OSError as err:
                logging.error('Failed to Create Folder %s - %s', config.imageRecentDir, err)
    if not os.path.isdir(config.search_dest_path):
        logging.info("Creating Search Folder %s", config.search_dest_path)
        os.makedirs(config.search_dest_path)
    if not os.path.isdir(html_path):
        logging.info("Creating html Folder %s", html_path)
        os.makedirs(html_path)
    os.chdir(cwd)


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


def look_for_picam(config):
    picam_spec = util.find_spec("picamera")

    if picam_spec is None and not config.WEBCAM:
        logging.warning('Changing to webcam mode as no picamera module detected')
        config.WEBCAM = True

    if not config.WEBCAM:
        # Check that pi camera module is installed and enabled
        cam_result = subprocess.check_output("vcgencmd get_camera", shell=True)
        cam_result = cam_result.decode("utf-8")
        cam_result = cam_result.replace("\n", "")
        if (cam_result.find("0")) >= 0:   # -1 is zero not found. Cam OK
            logging.error("Pi Camera Module Not Found %s", cam_result)
            logging.error("if supported=0 Enable Camera per command sudo raspi-config")
            logging.error("if detected=0 Check Pi Camera Module is Installed Correctly")
            logging.error("%s %s Exiting Due to Error", app_constants.progName, app_constants.progVer)
            sys.exit(1)
        else:
            logging.info("Pi Camera Module is Enabled and Connected %s", cam_result)
