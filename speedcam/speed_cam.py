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
from speedcam.camera.utils import *
from speedcam.camera import calibration
from config import app_constants
from config import Config
from speedcam.startup import startup_helpers
from speedcam.storage import SqlLiteStorageService, CSVStorageService, utils


# ------------------------------------------------------------------------------
def get_image_name(storage_utils, prefix):
    """ build image file names by number sequence or date/time Added tenth of second"""
    right_now = datetime.datetime.now()
    filename = ("%s/%s%04d%02d%02d-%02d%02d%02d%d.jpg" %
                (storage_utils.get_image_path(), prefix, right_now.year, right_now.month, right_now.day,
                 right_now.hour, right_now.minute, right_now.second, right_now.microsecond/100000))
    return filename


def crop_image(config, image):
    try:
        # crop image to motion tracking area only
        image_crop = image[config.y_upper:config.y_lower, config.x_left:config.x_right]
    except ValueError:
        logging.warning("image Stream Image is Not Complete. Cannot Crop.")
        image_crop = None
    return image_crop


def create_filename_log_time(config, storage_utils, ave_speed):
    # Create a calibration image file name
    # There are no subdirectories to deal with
    if config.calibrate:
        log_time = datetime.datetime.now()
        filename = get_image_name(storage_utils, "calib-")
    else:
        # Create image file name prefix
        if config.image_filename_speed:
            speed_prefix = (str(int(round(ave_speed)))
                            + "-" + config.image_prefix)
        else:
            speed_prefix = config.image_prefix
        # Record log_time for use later in csv and sqlite
        log_time = datetime.datetime.now()
        # create image file name path
        filename = get_image_name(storage_utils, speed_prefix)

    return filename, log_time


def draw_overlay(config, img, x, y, w, h):
    # show centre of motion if required
    if config.SHOW_CIRCLE:
        cv2.circle(img,
                   (x + config.x_left, y + config.y_upper),
                   config.CIRCLE_SIZE,
                   cvGreen, config.LINE_THICKNESS)
    else:
        cv2.rectangle(img,
                      (int(x + config.x_left),
                       int(y + config.y_upper)),
                      (int(x + config.x_left + w),
                       int(y + config.y_upper + h)),
                      cvGreen, config.LINE_THICKNESS)


def find_biggest_area_in_bounds(config, contours):
    track_x, track_y, track_w, track_h = None, None, None, None
    biggest_area = config.MIN_AREA
    for c in contours:
        # get area of contour
        found_area = cv2.contourArea(c)
        if found_area > biggest_area:
            (x, y, w, h) = cv2.boundingRect(c)
            # check if object contour is completely within crop area
            if x > config.get_x_buf() and x + w < config.x_right - config.x_left - config.get_x_buf():
                track_x = x
                track_y = y
                track_w = w  # movement width of object contour
                track_h = h  # movement height of object contour
                biggest_area = found_area
    return biggest_area, track_x, track_y, track_w, track_h


def update_gui(config, image, image_crop, track):
    # track = (x, y, w, h)
    if config.gui_window_on:
        # show small circle at contour xy if required
        # otherwise a rectangle around most recent contour
        if track is not None:
            draw_overlay(config, image, track[0], track[1], track[2], track[3])
        image = speed_image_add_lines(config, image, cvRed)
        image_view = cv2.resize(image, (config.get_image_width(), config.get_image_height()))
        cv2.imshow('Movement (q Quits)', image_view)
        if config.show_thresh_on:
            cv2.imshow('Threshold', config.thresholdimage)
        # Broken as it only ever shows first frame image_crop
        if config.show_crop_on:
            cv2.imshow('Crop Area', image_crop)
        # Close Window if q pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            sys.exit()


class MotionTrack:
    def __init__(self, config):
        self.config = config
        self.track_count = 0
        self.speed_list = []
        self.event_timer = time.time()
        self.first_event = True
        self.track_start_time = None
        self.prev_start_time = None
        self.start_pos_x = None
        self.end_pos_x = None
        self.prev_end_pos_x = None
        self.cur_ave_speed = None

    def has_exceeded_track_timeout(self):
        reset_time_diff = time.time() - self.event_timer
        return reset_time_diff > self.config.event_timeout

    def has_track_count_exceeded_track_limit(self):
        return self.track_count >= self.config.track_counter

    def is_first_event(self):
        return self.first_event

    def get_avg_speed(self):
        # ave_speed = float((abs(tot_track_dist / tot_track_time)) * speed_conv)
        return sum(self.speed_list) / float(len(self.speed_list))

    def record_speed(self, curr_track_time):
        cur_track_dist = abs(self.end_pos_x - self.prev_end_pos_x)
        self.cur_ave_speed = float((abs(cur_track_dist /
                                   float(abs(curr_track_time -
                                             self.prev_start_time)))) *
                                   self.config.get_speed_conf())
        self.speed_list.append(self.cur_ave_speed)

    def restart_tracking(self, track_start_time, start_pos_x):
        self.track_start_time = track_start_time  # Record track start time
        self.prev_start_time = track_start_time
        self.start_pos_x = start_pos_x
        self.end_pos_x = start_pos_x
        self.event_timer = time.time()  # Reset event timeout
        self.track_count = 0
        self.speed_list = []
        self.first_event = False


class Capture:
    def __init__(self, config, vs):
        self.config = config
        self.stream = vs
        self.curr_img = None
        self.curr_img_crop = None
        self.curr_img_gray = None
        self.prev_img = None
        self.prev_img_crop = None
        self.prev_img_gray = None

    def update_curr_img(self):
        self.curr_img = self.stream.read()
        self.curr_img_crop = crop_image(self.config, self.curr_img)
        if self.curr_img_crop is not None:
            self.curr_img_gray = cv2.cvtColor(self.curr_img_crop, cv2.COLOR_BGR2GRAY)

    def speed_get_contours(self):
        self.prev_img = self.curr_img
        self.prev_img_crop = self.curr_img_crop
        self.prev_img_gray = self.curr_img_gray

        image_ok = False
        while not image_ok:
            self.curr_img = self.stream.read()  # Read image data from video steam thread instance
            # crop image to motion tracking area only
            self.curr_img_crop = crop_image(self.config, self.curr_img)
            if self.curr_img_crop is not None:
                image_ok = True

        # Convert to gray scale, which is easier
        self.curr_img_gray = cv2.cvtColor(self.curr_img_crop, cv2.COLOR_BGR2GRAY)
        # Get differences between the two greyed images
        grey_diff = cv2.absdiff(self.prev_img_gray, self.curr_img_gray)
        # Blur difference image to enhance motion vectors
        grey_diff = cv2.blur(grey_diff, (self.config.BLUR_SIZE, self.config.BLUR_SIZE))
        # Get threshold of blurred difference image
        # based on THRESHOLD_SENSITIVITY variable
        retval, thresholdimage = cv2.threshold(grey_diff,
                                               self.config.THRESHOLD_SENSITIVITY,
                                               255, cv2.THRESH_BINARY)
        try:
            # opencv 2 syntax default
            contours, hierarchy = cv2.findContours(thresholdimage,
                                                   cv2.RETR_EXTERNAL,
                                                   cv2.CHAIN_APPROX_SIMPLE)
        except ValueError:
            # opencv 3 syntax
            thresholdimage, contours, hierarchy = cv2.findContours(thresholdimage,
                                                                   cv2.RETR_EXTERNAL,
                                                                   cv2.CHAIN_APPROX_SIMPLE)

        return contours


# ------------------------------------------------------------------------------
def speed_camera(config, db, vs):
    """ Main speed camera processing function """
    # Calculate position of text on the images
    if config.image_text_bottom:
        text_y = (config.get_image_height() - 50)  # show text at bottom of image
    else:
        text_y = 10  # show text at top of image
    storage_utils = utils.StorageUtils(config)
    csv = CSVStorageService(config)
    logging.info("Begin Motion Tracking .....")
    capture = Capture(config, vs)
    capture.update_curr_img()
    if capture.curr_img_crop is None:
        # Should maybe use an exception here
        vs.stop()
        logging.warning("Problem Connecting To Camera Stream.")
        logging.warning("Restarting Camera.  One Moment Please ...")
        time.sleep(4)
        return
    tracking = MotionTrack(config)
    still_scanning = True
    while still_scanning:  # process camera thread images and calculate speed
        image2 = vs.read()  # Read image data from video steam thread instance
        contours = capture.speed_get_contours()
        # if contours found, find the one with biggest area
        motion_found = False
        if contours:
            total_contours = len(contours)
            biggest_area, track_x, track_y, track_w, track_h = find_biggest_area_in_bounds(config, contours)

            if track_x is not None:
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
                    tracking.restart_tracking(cur_track_time, track_x)
                    logging.info("New  - 0/%i xy(%i,%i) Start New Track", config.track_counter, track_x, track_y)
                else:
                    tracking.prev_end_pos_x = tracking.end_pos_x
                    tracking.end_pos_x = track_x
                    if tracking.end_pos_x - tracking.prev_end_pos_x > 0:
                        travel_direction = "L2R"
                    else:
                        travel_direction = "R2L"
                    # check if movement is within acceptable distance range of last event
                    if config.x_diff_min < abs(tracking.end_pos_x - tracking.prev_end_pos_x) < config.x_diff_max:
                        tracking.track_count += 1  # increment
                        tracking.record_speed(cur_track_time)
                        tracking.prev_start_time = cur_track_time
                        if tracking.has_track_count_exceeded_track_limit():
                            # track_x only read after this
                            # tracking.start_pos_x doesn't change below this
                            tot_track_dist = abs(track_x - tracking.start_pos_x)
                            # cur_track_time not used after this
                            # tracking.track_start_time doesn't change below this
                            tot_track_time = abs(tracking.track_start_time - cur_track_time)
                            ave_speed = tracking.get_avg_speed()
                            # Track length exceeded so take process speed photo
                            if ave_speed > config.max_speed_over or config.calibrate:
                                logging.info(" Add - %i/%i xy(%i,%i) %3.2f %s"
                                             " D=%i/%i C=%i %ix%i=%i sqpx %s",
                                             tracking.track_count, config.track_counter,
                                             track_x, track_y,
                                             tracking.cur_ave_speed, config.get_speed_units(),
                                             abs(track_x - tracking.prev_end_pos_x),
                                             config.x_diff_max,
                                             total_contours,
                                             track_w, track_h, biggest_area,
                                             travel_direction)
                                # Resize and process previous image
                                # before saving to disk
                                prev_image = image2
                                filename, log_time = create_filename_log_time(config, storage_utils, ave_speed)
                                if config.calibrate:
                                    prev_image = calibration.take_calibration_image(config, ave_speed, filename, prev_image)
                                # Add motion rectangle to image if required
                                if config.image_show_motion_area:
                                    prev_image = speed_image_add_lines(config, prev_image, cvRed)
                                    draw_overlay(config, prev_image, track_x, track_y, track_w, track_h)
                                big_image = cv2.resize(prev_image,
                                                       (config.get_image_width(),
                                                        config.get_image_height()))
                                # Write text on image before saving
                                # if required.
                                if config.image_text_on:
                                    image_text = ("SPEED %.1f %s - %s"
                                                  % (ave_speed,
                                                     config.get_speed_units(),
                                                     filename))
                                    text_x = int((config.get_image_width() / 2) -
                                                 (len(image_text) *
                                                  config.image_font_size / 3))
                                    if text_x < 2:
                                        text_x = 2
                                    cv2.putText(big_image,
                                                image_text,
                                                (text_x, text_y),
                                                cv2.FONT_HERSHEY_SIMPLEX,
                                                config.FONT_SCALE,
                                                cvWhite,
                                                2)
                                logging.info(" Saved %s", filename)
                                # Save resized image
                                cv2.imwrite(filename, big_image)
                                # if required check free disk space
                                # and delete older files (jpg)
                                if db.is_available():
                                    db.save_speed_data(db.format_data(log_time, filename, travel_direction,
                                                                      ave_speed, track_x, track_y, track_w, track_h))
                                # Format and Save Data to CSV Log File
                                if csv.is_active:
                                    csv.write_line(csv.format_data(log_time, filename, travel_direction,
                                                                   ave_speed, track_x, track_y, track_w, track_h))
                                # Check if we need to clean the disk
                                storage_utils.free_space_check()
                                # Check if we need to rotate the image dir
                                storage_utils.rotate_image_dir()
                                # Manage a maximum number of files
                                # and delete oldest if required.
                                if config.image_max_files > 0:
                                    utils.StorageUtils.delete_old_files(config.image_max_files,
                                                                        storage_utils.get_image_path(),
                                                                        config.image_prefix)
                                # Save most recent files
                                # to a recent folder if required
                                if config.imageRecentMax > 0 and not config.calibrate:
                                    storage_utils.save_recent(filename)

                                logging.info("End  - Ave Speed %.1f %s Tracked %i px in %.3f sec Calib %ipx %imm",
                                             ave_speed, config.get_speed_units(),
                                             tot_track_dist,
                                             tot_track_time,
                                             config.cal_obj_px,
                                             config.cal_obj_mm)
                                logging.info(app_constants.horz_line)
                                # Wait to avoid dual tracking same object.
                                if config.track_timeout > 0:
                                    logging.info("Sleep - %0.2f seconds to Clear Track", config.track_timeout)
                                    time.sleep(config.track_timeout)
                            else:
                                logging.info("End  - Skip Photo SPEED %.1f %s"
                                             " max_speed_over=%i  %i px in %.3f sec"
                                             " C=%i A=%i sqpx",
                                             ave_speed, config.get_speed_units(),
                                             config.max_speed_over, tot_track_dist,
                                             tot_track_time, total_contours,
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
                                         track_x, track_y,
                                         tracking.cur_ave_speed, config.get_speed_units(),
                                         abs(track_x - tracking.prev_end_pos_x),
                                         config.x_diff_max,
                                         total_contours,
                                         track_w, track_h, biggest_area,
                                         travel_direction)
                            tracking.end_pos_x = track_x
                            # valid motion found so update event_timer
                            tracking.event_timer = time.time()
                    # Movement was not within range parameters
                    else:
                        if config.show_out_range:
                            # movements exceeds Max px movement
                            # allowed so Ignore and do not update event_timer
                            if abs(track_x - tracking.prev_end_pos_x) >= config.x_diff_max:
                                logging.info(" Out - %i/%i xy(%i,%i) Max D=%i>=%ipx"
                                             " C=%i %ix%i=%i sqpx %s",
                                             tracking.track_count, config.track_counter,
                                             track_x, track_y,
                                             abs(track_x - tracking.prev_end_pos_x),
                                             config.x_diff_max,
                                             total_contours,
                                             track_w, track_h, biggest_area,
                                             travel_direction)
                                # if track_count is over half way then do not start new track
                                if tracking.track_count > config.track_counter / 2:
                                    pass
                                else:
                                    tracking.first_event = True    # Too Far Away so restart Track
                            # Did not move much so update event_timer
                            # and wait for next valid movement.
                            else:
                                logging.info(" Out - %i/%i xy(%i,%i) Min D=%i<=%ipx"
                                             " C=%i %ix%i=%i sqpx %s",
                                             tracking.track_count, config.track_counter,
                                             track_x, track_y,
                                             abs(track_x - tracking.end_pos_x),
                                             config.x_diff_min,
                                             total_contours,
                                             track_w, track_h, biggest_area,
                                             travel_direction)
                                # Restart Track if first event otherwise continue
                                if tracking.track_count == 0:
                                    tracking.first_event = True
                        tracking.event_timer = time.time()  # Reset Event Timer
        track = (track_x, track_y, track_w, track_h) if contours and motion_found else None
        update_gui(config, image2, capture.curr_img_crop, track)
        if config.display_fps:   # Optionally show motion image processing loop fps
            logging.info("%.2f fps", vs.get_fps())


def main():
    startup_helpers.init_boot_logger()
    logging.info("%s %s   written by Claude Pageau", app_constants.progName, app_constants.progVer)
    logging.info(app_constants.horz_line)
    logging.info("Loading ...")

    config = Config()
    config.display_config_verbose()
    startup_helpers.create_dir(config)
    db = SqlLiteStorageService(config)
    db.start()

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
                    logging.error("%s %s Exiting Due to Error", app_constants.progName, app_constants.progVer)
                    sys.exit(1)
            else:
                logging.info("Initializing Pi Camera ....")
                picam_module = importlib.import_module("speedcam.camera.pi_video_stream")
                # Start a pi-camera video stream thread
                vs = picam_module.PiVideoStream(config).start()
                time.sleep(2.0)  # Allow PiCamera to initialize
            if config.calibrate:
                logging.warning("IMPORTANT: Camera Is In Calibration Mode ....")
            speed_camera(config, db, vs)  # run main speed camera processing loop
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
        logging.info("%s %s Exiting Program", app_constants.progName, app_constants.progVer)


if __name__ == '__main__':
    main()
