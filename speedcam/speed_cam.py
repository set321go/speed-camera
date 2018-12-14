#!/usr/bin/python
"""
speed-cam.py written by Claude Pageau pageauc@gmail.com
Windows, Unix, Raspberry (Pi) - python opencv2 Speed tracking
using picamera module or Web Cam
GitHub Repo here https://github.com/pageauc/rpi-speed-camera/tree/master/

This is a python openCV object speed tracking demonstration program.
It will detect speed in the field of view and use openCV to calculate the
largest contour and return its x,y coordinate.  The image is tracked for
a specified pixel length and the final speed is calculated.
Note: Variables for this program are stored in config.py

Some of this code is based on a YouTube tutorial by
Kyle Hounslow using C here https://www.youtube.com/watch?v=X6rPdRZzgjg

Thanks to Adrian Rosebrock jrosebr1 at http://www.pyimagesearch.com
for the PiVideoStream Class code available on github at
https://github.com/jrosebr1/imutils/blob/master/imutils/video/pivideostream.py

Here is my YouTube video demonstrating a previous speed tracking demo
program using a Raspberry Pi B2 https://youtu.be/09JS7twPBsQ
and a fun speed lapse video https://youtu.be/-xdB_x_CbC8
Installation
Requires a Raspberry Pi with a RPI camera module or Web Cam installed and working
or Windows, Unix Distro computer with a USB Web Cam.  See github wiki for
more detail https://github.com/pageauc/speed-camera/wiki

Install from a logged in SSH session per commands below.
Code should run on a non RPI platform using a Web Cam

curl -L https://raw.github.com/pageauc/rpi-speed-camera/master/speed-install.sh | bash
or
wget https://raw.github.com/pageauc/rpi-speed-camera/master/speed-install.sh
chmod +x speed-install.sh
./speed-install.sh
./speed-cam.py

"""
import time
import datetime
import sys
import logging
import importlib
import cv2
from speedcam.tracking.capture import Capture, CameraException
from speedcam.tracking.motion import MotionTrack
from config.app_constants import HORZ_LINE, APP_NAME, VERSION
from config import Config
from speedcam.startup import startup_helpers
from speedcam.storage import SqlLiteStorageService, CSVStorageService, ImgFileUtils, StorageUtils


def update_gui(config, image):
    # track = (x, y, w, h)
    if config.gui_window_on and image is not None:
        cv2.imshow('Movement (q Quits)', image)
        if config.show_thresh_on:
            cv2.imshow('Threshold', config.thresholdimage)
        # Broken as it only ever shows first frame image_crop
        # if config.show_crop_on:
        #     cv2.imshow('Crop Area', image_crop)
        # Close Window if q pressed
        if cv2.waitKey(25) & 0xFF == ord('q'):
            sys.exit()


# ------------------------------------------------------------------------------
def speed_camera(config, db, vs):
    """ Main speed camera processing function """
    logging.info("Begin Motion Tracking .....")
    storage_utils = StorageUtils(config)
    csv = CSVStorageService(config)
    tracking = MotionTrack(config)
    capture = Capture(config, vs)
    capture.init_capture_data()

    big_image = None
    while True:  # process camera thread images and calculate speed
        capture.calculate_speed_contours()
        # if contours found, find the one with biggest area
        if capture.contours:
            biggest_area, tracking_box = tracking.find_biggest_area_in_bounds(capture.contours)

            if tracking_box is not None:
                cur_track_time = time.time()  # record cur track time
                # Check if last motion event timed out
                if tracking.has_exceeded_track_timeout():
                    # event_timer exceeded so reset for new track
                    tracking.first_event = True
                    logging.info("Reset- event_timer %.2f sec Exceeded", config.event_timeout)
                ##############################
                # Process motion events and track object movement
                ##############################
                if tracking.is_first_event():   # This is a first valid motion event
                    tracking.reset_tracking(cur_track_time, tracking_box.track_x)
                    logging.info("New  - 0/%i xy(%i,%i) Start New Track", config.track_counter, tracking_box.track_x, tracking_box.track_y)
                else:
                    tracking.update_end_pos_x(tracking_box.track_x)
                    # check if movement is within acceptable distance range of last event
                    if tracking.is_within_range():
                        tracking.track_count += 1  # increment
                        tracking.record_speed(cur_track_time)
                        tracking.prev_start_time = cur_track_time
                        if tracking.has_track_count_exceeded_track_limit():
                            # Track length exceeded so take process speed photo
                            if tracking.is_object_speeding() or config.calibrate:
                                logging.info(" Add - %i/%i xy(%i,%i) %3.2f %s"
                                             " D=%i/%i C=%i %ix%i=%i sqpx %s",
                                             tracking.track_count, config.track_counter,
                                             tracking_box.track_x, tracking_box.track_y,
                                             tracking.cur_ave_speed, config.get_speed_units(),
                                             tracking.diff_x,
                                             config.x_diff_max,
                                             len(capture.contours),
                                             tracking_box.track_w, tracking_box.track_h, biggest_area,
                                             tracking.get_travel_dir())

                                img_file_utils = ImgFileUtils(config, storage_utils, tracking, cur_track_time)
                                big_image = capture.process_img(tracking.get_avg_speed(),
                                                                img_file_utils.filename,
                                                                tracking_box)
                                img_file_utils.save_img(big_image)

                                if db.is_available():
                                    db.save_speed_data(db.format_data(datetime.datetime.fromtimestamp(cur_track_time),
                                                                      img_file_utils.filename, tracking.get_travel_dir(),
                                                                      tracking.get_avg_speed(), tracking_box))
                                # Format and Save Data to CSV Log File
                                if csv.is_active:
                                    csv.write_line(csv.format_data(datetime.datetime.fromtimestamp(cur_track_time), img_file_utils.filename,
                                                                   tracking.get_travel_dir(), tracking.get_avg_speed(),
                                                                   tracking_box))

                                storage_utils.filesystem_housekeeping(img_file_utils.filename)

                                logging.info("End  - Ave Speed %.1f %s Tracked %i px in %.3f sec Calib %ipx %imm",
                                             tracking.get_avg_speed(), config.get_speed_units(),
                                             tracking.calculate_track_dist(tracking_box.track_x),
                                             tracking.calculate_track_time(cur_track_time),
                                             config.cal_obj_px,
                                             config.cal_obj_mm)
                                logging.info(HORZ_LINE)
                                # Wait to avoid dual tracking same object.
                                if config.track_timeout > 0:
                                    logging.info("Sleep - %0.2f seconds to Clear Track", config.track_timeout)
                                    time.sleep(config.track_timeout)
                            else:
                                logging.info("End  - Skip Photo SPEED %.1f %s"
                                             " max_speed_over=%i  %i px in %.3f sec"
                                             " C=%i A=%i sqpx",
                                             tracking.get_avg_speed(), config.get_speed_units(),
                                             config.max_speed_over, tracking.calculate_track_dist(tracking_box.track_x),
                                             tracking.calculate_track_time(cur_track_time), len(capture.contours),
                                             biggest_area)
                                # Optional Wait to avoid dual tracking
                                if config.track_timeout > 0:
                                    logging.info("Sleep - %0.2f seconds to Clear Track", config.track_timeout)
                                    time.sleep(config.track_timeout)
                            # Track Ended so Reset Variables ready for next tracking sequence
                            tracking.first_event = True  # Reset Track
                        else:
                            logging.info(" Add - %i/%i xy(%i,%i) %3.2f %s"
                                         " D=%i/%i C=%i %ix%i=%i sqpx %s",
                                         tracking.track_count, config.track_counter,
                                         tracking_box.track_x, tracking_box.track_y,
                                         tracking.cur_ave_speed, config.get_speed_units(),
                                         tracking.diff_x,
                                         config.x_diff_max,
                                         len(capture.contours),
                                         tracking_box.track_w, tracking_box.track_h, biggest_area,
                                         tracking.get_travel_dir())
                            # valid motion found so update event_timer
                            tracking.last_seen = time.time()
                    # Movement was not within range parameters
                    else:
                        if config.show_out_range:
                            if tracking.diff_x > config.x_diff_max:
                                out_of_range = "Max D=%i>%ipx" % (tracking.diff_x, config.x_diff_max)
                            else:
                                out_of_range = "Max D=%i<%ipx" % (tracking.diff_x, config.x_diff_min)

                            logging.info(" Out - %i/%i xy(%i,%i) %s"
                                         " C=%i %ix%i=%i sqpx %s",
                                         tracking.track_count, config.track_counter,
                                         tracking_box.track_x, tracking_box.track_y,
                                         out_of_range,
                                         len(capture.contours),
                                         tracking_box.track_w, tracking_box.track_h, biggest_area,
                                         tracking.get_travel_dir())
        update_gui(config, big_image)
        if config.display_fps:   # Optionally show motion image processing loop fps
            logging.info("%.2f fps", vs.get_fps())


def start():
    startup_helpers.init_boot_logger()
    logging.info("%s %s   written by Claude Pageau", APP_NAME, VERSION)
    logging.info(HORZ_LINE)
    logging.info("Loading ...")

    config = Config()
    config.display_config_verbose()
    startup_helpers.create_dir(config)
    db = SqlLiteStorageService(config)
    db.start()

    startup_helpers.gui_message(config)
    startup_helpers.init_logger(config)
    startup_helpers.look_for_picam(config)

    vs = None
    try:
        while True:
            # Start Web Cam stream (Note USB webcam must be plugged in)
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
                    sys.exit(1)
            else:
                logging.info("Initializing Pi Camera ....")
                picam_module = importlib.import_module("speedcam.camera.pi_video_stream")
                # Start a pi-camera video stream thread
                vs = picam_module.PiVideoStream(config).start()
                time.sleep(2.0)  # Allow PiCamera to initialize
            if config.calibrate:
                logging.warning("IMPORTANT: Camera Is In Calibration Mode ....")
            try:
                speed_camera(config, db, vs)  # run main speed camera processing loop
            except CameraException:
                vs.stop()
                logging.warning("Problem Connecting To Camera Stream.")
                logging.warning("Restarting Camera.  One Moment Please ...")
    except KeyboardInterrupt:
        sys.exit()
    except SystemExit:
        raise
    finally:
        if config.gui_window_on:
            cv2.destroyAllWindows()
        if vs is not None:
            vs.stop()
        logging.info("")
        logging.info("%s %s Exiting Program", APP_NAME, VERSION)
