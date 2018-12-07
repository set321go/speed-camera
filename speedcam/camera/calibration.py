import cv2
import logging
import os
from speedcam.camera import utils


def take_calibration_image(config, speed, filename, cal_image):
    """
    Create a calibration image for determining value of IMG_VIEW_FT variable
    Create calibration hash marks
    """
    # If there is bad contrast with background you can change the hash
    # colors to give more contrast.  You need to change values below
    # per values cvRed, cvBlue, cvWhite, cvBlack, cvGreen

    hash_color = utils.cvRed
    motion_win_color = utils.cvBlue

    for i in range(10, config.get_image_width() - 9, 10):
        cv2.line(cal_image, (i, config.y_upper - 5), (i, config.y_upper + 30), hash_color, 1)
    # This is motion window
    cal_image = utils.speed_image_add_lines(config, cal_image, motion_win_color)
    if config.SPEED_MPH:
        speed_units = 'mph'
    else:
        speed_units = 'kph'

    if not config.verbose or not logging.getLogger().isEnabledFor(logging.INFO):
        logging.error("You are in calibration mode but your log settings prevent you from seeing calibration info")
        logging.error("Enable verbose=True or turn your logger to INFO to see calibration information")

    logging.info("")
    logging.info("----------------------------- Create Calibration Image -----------------------------")
    logging.info("")
    logging.info("  Instructions for using %s image for camera calibration", filename)
    logging.info("")
    logging.info("  1 - Use Known Similar Size Reference Objects in Images, Like similar vehicles at the Required Distance.")
    logging.info("  2 - Record cal_obj_px Value Using Red y_upper Hash Marks at every 10 px  Current Setting is %i px", config.cal_obj_px)
    logging.info("  3 - Record cal_obj_mm of object. This is Actual length in mm of object above Current Setting is %i mm",
                 config.cal_obj_mm)
    logging.info("      If Recorded Speed %.1f %s is Too Low, Increasing cal_obj_mm to Adjust or Visa-Versa", speed, speed_units)
    if config.pluginEnable:
        logging.info("  4 - Edit %s File and Change Values for Above Variables.",
                     os.path.join(config.base_dir, "plugins", config.pluginName + '.ini'))
    else:
        logging.info("  4 - Edit %s File and Change Values for the Above Variables.", 'config.ini')
    logging.info("  5 - Do a Speed Test to Confirm/Tune Settings.  You May Need to Repeat.")
    logging.info("  6 - When Calibration is Finished, Set config.py Variable   calibrate = False")
    logging.info("      Then Restart speed-cam.py and monitor activity.")
    logging.info("")
    logging.info("  WARNING: It is Advised to Use 320x240 Stream for Best Performance.")
    logging.info("           Higher Resolutions Need More OpenCV Processing")
    logging.info("")
    logging.info("  Calibration Image Saved To %s%s  ", config.base_dir, filename)
    logging.info("  View Calibration Image in Web Browser (Ensure webserver.py is started)")
    logging.info("")
    logging.info("---------------------- Press ctrl-c to Quit Calibration Mode -----------------------")
    logging.info("")
    return cal_image
