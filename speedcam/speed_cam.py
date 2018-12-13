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
import collections
from speedcam.camera.utils import *
from speedcam.camera import calibration
from config import app_constants
from config import Config
from speedcam.startup import startup_helpers
from speedcam.storage import SqlLiteStorageService, CSVStorageService, utils


def draw_geom_overlay(config, img, x, y, w, h):
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


def update_gui(config, image, image_crop, track):
    # track = (x, y, w, h)
    if config.gui_window_on:
        # show small circle at contour xy if required
        # otherwise a rectangle around most recent contour
        if track is not None:
            draw_geom_overlay(config, image, track[0], track[1], track[2], track[3])
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


class ImgProcessor:
    def __init__(self, config, storage_utils, tracking, cur_track_time):
        self.track_time = datetime.datetime.fromtimestamp(cur_track_time)
        self.tracking = tracking
        self.storage_utils = storage_utils
        self.config = config
        self.filename = self.__create_filename()

    def __create_filename(self):
        # Create a calibration image file name
        # There are no subdirectories to deal with
        if self.config.calibrate:
            return self.__get_image_name("calib-")
        else:
            # Create image file name prefix
            if self.config.image_filename_speed:
                speed_prefix = (str(int(round(self.tracking.ave_speed)))
                                + "-" + self.config.image_prefix)
            else:
                speed_prefix = self.config.image_prefix
            # create image file name path
            return self.__get_image_name(speed_prefix)

    def __get_image_name(self, prefix):
        """ build image file names by number sequence or date/time Added tenth of second"""
        return ("%s/%s%04d%02d%02d-%02d%02d%02d%d.jpg" %
                (self.storage_utils.get_image_path(), prefix, self.track_time.year, self.track_time.month, self.track_time.day,
                 self.track_time.hour, self.track_time.minute, self.track_time.second, self.track_time.microsecond/100000))

    def save_img(self, capture, tracking_box):
        big_image = capture.process_img(self.tracking.get_avg_speed(), self.filename,
                                        tracking_box.track_x, tracking_box.track_y, tracking_box.track_w, tracking_box.track_h)

        logging.info(" Saved %s", self.filename)
        # Save resized image
        cv2.imwrite(self.filename, big_image)


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

    def get_travel_dir(self):
        return "L2R" if self.end_pos_x - self.prev_end_pos_x > 0 else "R2L"

    def calculate_track_dist(self, track_x):
        return abs(track_x - self.start_pos_x)

    def calculate_track_time(self, cur_track_time):
        return abs(self.track_start_time - cur_track_time)

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

    def find_biggest_area_in_bounds(self, contours):
        track_x, track_y, track_w, track_h = None, None, None, None
        biggest_area = self.config.MIN_AREA
        for c in contours:
            # get area of contour
            found_area = cv2.contourArea(c)
            if found_area > biggest_area:
                (x, y, w, h) = cv2.boundingRect(c)
                # check if object contour is completely within crop area
                if x > self.config.get_x_buf() and x + w < self.config.x_right - self.config.x_left - self.config.get_x_buf():
                    track_x = x
                    track_y = y
                    track_w = w  # movement width of object contour
                    track_h = h  # movement height of object contour
                    biggest_area = found_area
        TrackingBox = collections.namedtuple('TrackingBox', ['track_x', 'track_y', 'track_w', 'track_h'])
        return biggest_area, TrackingBox(track_x, track_y, track_w, track_h) if (track_x, track_y, track_w, track_h) is not None else None


class Capture:
    def __init__(self, config, vs):
        self.config = config
        self.stream = vs
        self.contours = []
        self.curr_img = None
        self.curr_img_crop = None
        self.curr_img_gray = None
        self.prev_img = None
        self.prev_img_crop = None
        self.prev_img_gray = None

    def __draw_text_overlay(self, filename, ave_speed, big_image):
        image_text = ("SPEED %.1f %s - %s"
                      % (ave_speed,
                         self.config.get_speed_units(),
                         filename))
        text_x = int((self.config.get_image_width() / 2) -
                     (len(image_text) *
                      self.config.image_font_size / 3))
        if text_x < 2:
            text_x = 2
        # Calculate position of text on the images
        if self.config.image_text_bottom:
            text_y = (self.config.get_image_height() - 50)  # show text at bottom of image
        else:
            text_y = 10  # show text at top of image
        cv2.putText(big_image,
                    image_text,
                    (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    self.config.FONT_SCALE,
                    cvWhite,
                    2)

    def __crop_image(self):
        try:
            # crop image to motion tracking area only
            image_crop = self.curr_img[self.config.y_upper:self.config.y_lower, self.config.x_left:self.config.x_right]
        except ValueError:
            logging.warning("image Stream Image is Not Complete. Cannot Crop.")
            image_crop = None
        return image_crop

    def update_curr_img(self):
        self.curr_img = self.stream.read()
        self.curr_img_crop = self.__crop_image()
        if self.curr_img_crop is not None:
            self.curr_img_gray = cv2.cvtColor(self.curr_img_crop, cv2.COLOR_BGR2GRAY)

    def calculate_speed_contours(self):
        self.prev_img = self.curr_img
        self.prev_img_crop = self.curr_img_crop
        self.prev_img_gray = self.curr_img_gray

        image_ok = False
        while not image_ok:
            self.curr_img = self.stream.read()  # Read image data from video steam thread instance
            # crop image to motion tracking area only
            self.curr_img_crop = self.__crop_image()
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

        self.contours = contours

    def process_img(self, ave_speed, filename, track_x, track_y, track_w, track_h):
        processed_img = self.curr_img
        if self.config.calibrate:
            processed_img = calibration.take_calibration_image(self.config, ave_speed, filename, processed_img)
        # Add motion rectangle to image if required
        if self.config.image_show_motion_area:
            processed_img = speed_image_add_lines(self.config, processed_img, cvRed)
            draw_geom_overlay(self.config, processed_img, track_x, track_y, track_w, track_h)
        # Write text on image
        if self.config.image_text_on:
            self.__draw_text_overlay(filename, ave_speed, processed_img)

        return cv2.resize(processed_img, (self.config.get_image_width(), self.config.get_image_height()))


# ------------------------------------------------------------------------------
def speed_camera(config, db, vs):
    """ Main speed camera processing function """
    logging.info("Begin Motion Tracking .....")
    storage_utils = utils.StorageUtils(config)
    csv = CSVStorageService(config)
    capture = Capture(config, vs)
    tracking = MotionTrack(config)
    # ---------------------------
    # This logic doesn't really belong here we should encapsulate this
    capture.update_curr_img()
    if capture.curr_img_crop is None:
        # Should maybe use an exception here
        vs.stop()
        logging.warning("Problem Connecting To Camera Stream.")
        logging.warning("Restarting Camera.  One Moment Please ...")
        time.sleep(4)
        return
    # ---------------------------
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
                    tracking.restart_tracking(cur_track_time, tracking_box.track_x)
                    logging.info("New  - 0/%i xy(%i,%i) Start New Track", config.track_counter, tracking_box.track_x, tracking_box.track_y)
                else:
                    tracking.prev_end_pos_x = tracking.end_pos_x
                    tracking.end_pos_x = tracking_box.track_x
                    # check if movement is within acceptable distance range of last event
                    if config.x_diff_min < abs(tracking.end_pos_x - tracking.prev_end_pos_x) < config.x_diff_max:
                        tracking.track_count += 1  # increment
                        tracking.record_speed(cur_track_time)
                        tracking.prev_start_time = cur_track_time
                        if tracking.has_track_count_exceeded_track_limit():
                            # Track length exceeded so take process speed photo
                            if tracking.get_avg_speed() > config.max_speed_over or config.calibrate:
                                logging.info(" Add - %i/%i xy(%i,%i) %3.2f %s"
                                             " D=%i/%i C=%i %ix%i=%i sqpx %s",
                                             tracking.track_count, config.track_counter,
                                             tracking_box.track_x, tracking_box.track_y,
                                             tracking.cur_ave_speed, config.get_speed_units(),
                                             abs(tracking_box.track_x - tracking.prev_end_pos_x),
                                             config.x_diff_max,
                                             len(capture.contours),
                                             tracking_box.track_w, tracking_box.track_h, biggest_area,
                                             tracking.get_travel_dir())

                                img_processor = ImgProcessor(config, storage_utils, tracking, cur_track_time)
                                img_processor.save_img(capture, tracking_box)

                                if db.is_available():
                                    db.save_speed_data(db.format_data(datetime.datetime.fromtimestamp(cur_track_time),
                                                                      img_processor.filename, tracking.get_travel_dir(),
                                                                      tracking.get_avg_speed(), tracking_box))
                                # Format and Save Data to CSV Log File
                                if csv.is_active:
                                    csv.write_line(csv.format_data(datetime.datetime.fromtimestamp(cur_track_time), img_processor.filename,
                                                                   tracking.get_travel_dir(), tracking.get_avg_speed(),
                                                                   tracking_box))
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
                                    storage_utils.save_recent(img_processor.filename)

                                logging.info("End  - Ave Speed %.1f %s Tracked %i px in %.3f sec Calib %ipx %imm",
                                             tracking.get_avg_speed(), config.get_speed_units(),
                                             tracking.calculate_track_dist(tracking_box.track_x),
                                             tracking.calculate_track_time(cur_track_time),
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
                                         abs(tracking_box.track_x - tracking.prev_end_pos_x),
                                         config.x_diff_max,
                                         len(capture.contours),
                                         tracking_box.track_w, tracking_box.track_h, biggest_area,
                                         tracking.get_travel_dir())
                            tracking.end_pos_x = tracking_box.track_x
                            # valid motion found so update event_timer
                            tracking.event_timer = time.time()
                    # Movement was not within range parameters
                    else:
                        if config.show_out_range:
                            # movements exceeds Max px movement
                            # allowed so Ignore and do not update event_timer
                            if abs(tracking_box.track_x - tracking.prev_end_pos_x) >= config.x_diff_max:
                                logging.info(" Out - %i/%i xy(%i,%i) Max D=%i>=%ipx"
                                             " C=%i %ix%i=%i sqpx %s",
                                             tracking.track_count, config.track_counter,
                                             tracking_box.track_x, tracking_box.track_y,
                                             abs(tracking_box.track_x - tracking.prev_end_pos_x),
                                             config.x_diff_max,
                                             len(capture.contours),
                                             tracking_box.track_w, tracking_box.track_h, biggest_area,
                                             tracking.get_travel_dir())
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
                                             tracking_box.track_x, tracking_box.track_y,
                                             abs(tracking_box.track_x - tracking.end_pos_x),
                                             config.x_diff_min,
                                             len(capture.contours),
                                             tracking_box.track_w, tracking_box.track_h, biggest_area,
                                             tracking.get_travel_dir())
                                # Restart Track if first event otherwise continue
                                if tracking.track_count == 0:
                                    tracking.first_event = True
                        tracking.event_timer = time.time()  # Reset Event Timer
                update_gui(config, capture.curr_img, capture.curr_img_crop, tracking_box)
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
