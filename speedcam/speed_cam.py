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
from speedcam.config import app_constants
from speedcam.config.config import Config
from speedcam.startup import startup_helpers
from speedcam.storage import SqlLiteStorageService, CSVStorageService, utils


# ------------------------------------------------------------------------------
def get_fps(start_time, frame_count):
    """ Calculate and display frames per second processing """
    if frame_count >= 1000:
        duration = float(time.time() - start_time)
        fps = float(frame_count / duration)
        logging.info("%.2f fps Last %i Frames", fps, frame_count)
        frame_count = 0
        start_time = time.time()
    else:
        frame_count += 1
    return start_time, frame_count


# ------------------------------------------------------------------------------
def get_image_name(path, prefix):
    """ build image file names by number sequence or date/time Added tenth of second"""
    right_now = datetime.datetime.now()
    filename = ("%s/%s%04d%02d%02d-%02d%02d%02d%d.jpg" %
                (path, prefix, right_now.year, right_now.month, right_now.day,
                 right_now.hour, right_now.minute, right_now.second, right_now.microsecond/100000))
    return filename


# ------------------------------------------------------------------------------
def speed_get_contours(config, vs, grayimage1):
    image_ok = False
    while not image_ok:
        image = vs.read()  # Read image data from video steam thread instance
        if config.WEBCAM:
            if config.WEBCAM_HFLIP and config.WEBCAM_VFLIP:
                image = cv2.flip(image, -1)
            elif config.WEBCAM_HFLIP:
                image = cv2.flip(image, 1)
            elif config.WEBCAM_VFLIP:
                image = cv2.flip(image, 0)
        # crop image to motion tracking area only
        try:
            image_crop = image[config.y_upper:config.y_lower, config.x_left:config.x_right]
            image_ok = True
        except ValueError:
            logging.error("image Stream Image is Not Complete. Cannot Crop. Retry.")
            image_ok = False
    # Convert to gray scale, which is easier
    grayimage2 = cv2.cvtColor(image_crop, cv2.COLOR_BGR2GRAY)
    # Get differences between the two greyed images
    differenceimage = cv2.absdiff(grayimage1, grayimage2)
    # Blur difference image to enhance motion vectors
    differenceimage = cv2.blur(differenceimage, (config.BLUR_SIZE, config.BLUR_SIZE))
    # Get threshold of blurred difference image
    # based on THRESHOLD_SENSITIVITY variable
    retval, thresholdimage = cv2.threshold(differenceimage,
                                           config.THRESHOLD_SENSITIVITY,
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
    # Update grayimage1 to grayimage2 ready for next image2
    grayimage1 = grayimage2
    return grayimage1, contours, thresholdimage


# ------------------------------------------------------------------------------
def speed_camera(config, db, vs):
    """ Main speed camera processing function """
    # initialize variables
    frame_count = 0
    fps_time = time.time()
    first_event = True   # Start a New Motion Track
    start_pos_x = None
    end_pos_x = None
    font = cv2.FONT_HERSHEY_SIMPLEX
    # Calculate position of text on the images
    if config.image_text_bottom:
        text_y = (config.get_image_height() - 50)  # show text at bottom of image
    else:
        text_y = 10  # show text at top of image
    # Initialize prev_image used for taking speed image photo
    last_space_check = datetime.datetime.now()
    speed_path = config.image_path
    csv = CSVStorageService(config)
    if config.calibrate:
        logging.warning("IMPORTANT: Camera Is In Calibration Mode ....")

    logging.info("Begin Motion Tracking .....")
    # initialize a cropped grayimage1 image
    image2 = vs.read()  # Get image from PiVideoSteam thread instance
    try:
        # crop image to motion tracking area only
        image_crop = image2[config.y_upper:config.y_lower, config.x_left:config.x_right]
    except:
        vs.stop()
        logging.warning("Problem Connecting To Camera Stream.")
        logging.warning("Restarting Camera.  One Moment Please ...")
        time.sleep(4)
        return
    grayimage1 = cv2.cvtColor(image_crop, cv2.COLOR_BGR2GRAY)
    track_count = 0
    speed_list = []
    event_timer = time.time()
    still_scanning = True
    while still_scanning:  # process camera thread images and calculate speed
        image2 = vs.read()  # Read image data from video steam thread instance
        grayimage1, contours, thresholdimage = speed_get_contours(config, vs, grayimage1)
        # if contours found, find the one with biggest area
        if contours:
            total_contours = len(contours)
            motion_found = False
            biggest_area = config.MIN_AREA
            for c in contours:
                # get area of contour
                found_area = cv2.contourArea(c)
                if found_area > biggest_area:
                    (x, y, w, h) = cv2.boundingRect(c)
                    # check if object contour is completely within crop area
                    if x > config.get_x_buf() and x + w < config.x_right - config.x_left - config.get_x_buf():
                        cur_track_time = time.time()  # record cur track time
                        track_x = x
                        track_y = y
                        track_w = w  # movement width of object contour
                        track_h = h  # movement height of object contour
                        motion_found = True
                        biggest_area = found_area
            if motion_found:
                # Check if last motion event timed out
                reset_time_diff = time.time() - event_timer
                if reset_time_diff > config.event_timeout:
                    # event_timer exceeded so reset for new track
                    first_event = True
                    start_pos_x = None
                    end_pos_x = None
                    logging.info("Reset- event_timer %.2f>%.2f sec Exceeded",
                                 reset_time_diff, config.event_timeout)
                ##############################
                # Process motion events and track object movement
                ##############################
                if first_event:   # This is a first valid motion event
                    first_event = False  # Only one first track event
                    track_start_time = cur_track_time  # Record track start time
                    prev_start_time = cur_track_time
                    start_pos_x = track_x
                    end_pos_x = track_x
                    logging.info("New  - 0/%i xy(%i,%i) Start New Track",
                                 config.track_counter, track_x, track_y)
                    event_timer = time.time() # Reset event timeout
                    track_count = 0
                    speed_list = []
                else:
                    prev_pos_x = end_pos_x
                    end_pos_x = track_x
                    if end_pos_x - prev_pos_x > 0:
                        travel_direction = "L2R"
                    else:
                        travel_direction = "R2L"
                    # check if movement is within acceptable distance
                    # range of last event
                    if config.x_diff_min < abs(end_pos_x - prev_pos_x) < config.x_diff_max:
                        track_count += 1  # increment
                        cur_track_dist = abs(end_pos_x - prev_pos_x)
                        cur_ave_speed = float((abs(cur_track_dist /
                                               float(abs(cur_track_time -
                                                         prev_start_time)))) *
                                                         config.get_speed_conf())
                        speed_list.append(cur_ave_speed)
                        prev_start_time = cur_track_time
                        if track_count >= config.track_counter:
                            tot_track_dist = abs(track_x - start_pos_x)
                            tot_track_time = abs(track_start_time - cur_track_time)
                            # ave_speed = float((abs(tot_track_dist / tot_track_time)) * speed_conv)
                            ave_speed = sum(speed_list) / float(len(speed_list))
                            # Track length exceeded so take process speed photo
                            if ave_speed > config.max_speed_over or config.calibrate:
                                logging.info(" Add - %i/%i xy(%i,%i) %3.2f %s"
                                             " D=%i/%i C=%i %ix%i=%i sqpx %s",
                                             track_count, config.track_counter,
                                             track_x, track_y,
                                             cur_ave_speed, config.get_speed_units(),
                                             abs(track_x - prev_pos_x),
                                             config.x_diff_max,
                                             total_contours,
                                             track_w, track_h, biggest_area,
                                             travel_direction)
                                # Resize and process previous image
                                # before saving to disk
                                prev_image = image2
                                # Create a calibration image file name
                                # There are no subdirectories to deal with
                                if config.calibrate:
                                    log_time = datetime.datetime.now()
                                    filename = get_image_name(speed_path, "calib-")
                                    prev_image = calibration.take_calibration_image(config, ave_speed, filename, prev_image)
                                else:
                                    # Check if subdirectories configured
                                    # and create as required
                                    speed_path = utils.subDirChecks(config.imageSubDirMaxHours,
                                                                    config.imageSubDirMaxFiles,
                                                                    config.image_path,
                                                                    config.image_prefix)
                                    # Create image file name prefix
                                    if config.image_filename_speed:
                                        speed_prefix = (str(int(round(ave_speed)))
                                                        + "-" + config.image_prefix)
                                    else:
                                        speed_prefix = config.image_prefix
                                    # Record log_time for use later in csv and sqlite
                                    log_time = datetime.datetime.now()
                                    # create image file name path
                                    filename = get_image_name(speed_path,
                                                              speed_prefix)
                                # Add motion rectangle to image if required
                                if config.image_show_motion_area:
                                    prev_image = speed_image_add_lines(config, prev_image, cvRed)
                                    # show centre of motion if required
                                    if config.SHOW_CIRCLE:
                                        cv2.circle(prev_image,
                                                   (track_x + config.x_left, track_y + config.y_upper),
                                                   config.CIRCLE_SIZE,
                                                   cvGreen, config.LINE_THICKNESS)
                                    else:
                                        cv2.rectangle(prev_image,
                                                      (int(track_x + config.x_left),
                                                       int(track_y + config.y_upper)),
                                                      (int(track_x + config.x_left + track_w),
                                                       int(track_y + config.y_upper + track_h)),
                                                      cvGreen, config.LINE_THICKNESS)
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
                                                font,
                                                config.FONT_SCALE,
                                                cvWhite,
                                                2)
                                logging.info(" Saved %s", filename)
                                # Save resized image
                                cv2.imwrite(filename, big_image)
                                # if required check free disk space
                                # and delete older files (jpg)
                                if db.is_available():
                                    log_idx = ("%04d%02d%02d-%02d%02d%02d%d" %
                                               (log_time.year,
                                                log_time.month,
                                                log_time.day,
                                                log_time.hour,
                                                log_time.minute,
                                                log_time.second,
                                                log_time.microsecond/100000))
                                    log_date = ("%04d%02d%02d" %
                                                (log_time.year,
                                                 log_time.month,
                                                 log_time.day))
                                    log_hour = ("%02d" % log_time.hour)
                                    log_minute = ("%02d" % log_time.minute)
                                    m_area = track_w*track_h
                                    ave_speed = round(ave_speed, 2)
                                    if config.WEBCAM:
                                        camera = "WebCam"
                                    else:
                                        camera = "PiCam"
                                    if config.pluginEnable:
                                        plugin_name = config.pluginName
                                    else:
                                        plugin_name = "None"
                                    # create the speed data list ready for db insert
                                    speed_data = (log_idx,
                                                  log_date, log_hour, log_minute,
                                                  camera,
                                                  ave_speed, config.get_speed_units(), filename,
                                                  config.get_image_width(), config.get_image_height(), config.image_bigger,
                                                  travel_direction, plugin_name,
                                                  track_x, track_y,
                                                  track_w, track_h, m_area,
                                                  config.x_left, config.x_right,
                                                  config.y_upper, config.y_lower,
                                                  config.max_speed_over,
                                                  config.MIN_AREA, config.track_counter,
                                                  config.cal_obj_px, config.cal_obj_mm)
                                    db.save_speed_data(speed_data)
                                    # Insert speed_data into sqlite3 database table
                                # Format and Save Data to CSV Log File
                                if csv.is_active:
                                    log_csv_time = ("%s%04d%02d%02d%s,"
                                                    "%s%02d%s,%s%02d%s"
                                                    % (app_constants.QUOTE,
                                                       log_time.year,
                                                       log_time.month,
                                                       log_time.day,
                                                       app_constants.QUOTE,
                                                       app_constants.QUOTE,
                                                       log_time.hour,
                                                       app_constants.QUOTE,
                                                       app_constants.QUOTE,
                                                       log_time.minute,
                                                       app_constants.QUOTE))
                                    log_csv_text = ("%s,%.2f,%s%s%s,%s%s%s,"
                                                    "%i,%i,%i,%i,%i,%s%s%s"
                                                    % (log_csv_time,
                                                       ave_speed,
                                                       app_constants.QUOTE,
                                                       config.get_speed_units(),
                                                       app_constants.QUOTE,
                                                       app_constants.QUOTE,
                                                       filename,
                                                       app_constants.QUOTE,
                                                       track_x, track_y,
                                                       track_w, track_h,
                                                       track_w * track_h,
                                                       app_constants.QUOTE,
                                                       travel_direction,
                                                       app_constants.QUOTE))
                                    csv.write_line(log_csv_text)
                                if config.spaceTimerHrs > 0:
                                    last_space_check = utils.freeDiskSpaceCheck(last_space_check, config)
                                # Manage a maximum number of files
                                # and delete oldest if required.
                                if config.image_max_files > 0:
                                    utils.deleteOldFiles(config.image_max_files,
                                                         speed_path,
                                                         config.image_prefix)
                                # Save most recent files
                                # to a recent folder if required
                                if config.imageRecentMax > 0 and not config.calibrate:
                                    utils.saveRecent(config.imageRecentMax,
                                                     config.imageRecentDir,
                                                     filename,
                                                     config.image_prefix)

                                logging.info("End  - Ave Speed %.1f %s Tracked %i px in %.3f sec Calib %ipx %imm",
                                             ave_speed, config.get_speed_units(),
                                             tot_track_dist,
                                             tot_track_time,
                                             config.cal_obj_px,
                                             config.cal_obj_mm)
                                logging.info(app_constants.horz_line)
                                # Wait to avoid dual tracking same object.
                                if config.track_timeout > 0:
                                    logging.info("Sleep - %0.2f seconds to Clear Track"
                                                 % config.track_timeout)
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
                                    logging.info("Sleep - %0.2f seconds to Clear Track"
                                                 % config.track_timeout)
                                time.sleep(config.track_timeout)
                            # Track Ended so Reset Variables ready for
                            # next tracking sequence
                            start_pos_x = None
                            end_pos_x = None
                            first_event = True  # Reset Track
                            track_count = 0
                            event_timer = time.time()
                        else:
                            logging.info(" Add - %i/%i xy(%i,%i) %3.2f %s"
                                         " D=%i/%i C=%i %ix%i=%i sqpx %s",
                                         track_count, config.track_counter,
                                         track_x, track_y,
                                         cur_ave_speed, config.get_speed_units(),
                                         abs(track_x - prev_pos_x),
                                         config.x_diff_max,
                                         total_contours,
                                         track_w, track_h, biggest_area,
                                         travel_direction)
                            end_pos_x = track_x
                            # valid motion found so update event_timer
                            event_timer = time.time()
                    # Movement was not within range parameters
                    else:
                        if config.show_out_range:
                            # movements exceeds Max px movement
                            # allowed so Ignore and do not update event_timer
                            if abs(track_x - prev_pos_x) >= config.x_diff_max:
                                logging.info(" Out - %i/%i xy(%i,%i) Max D=%i>=%ipx"
                                             " C=%i %ix%i=%i sqpx %s",
                                             track_count, config.track_counter,
                                             track_x, track_y,
                                             abs(track_x - prev_pos_x),
                                             config.x_diff_max,
                                             total_contours,
                                             track_w, track_h, biggest_area,
                                             travel_direction)
                                # if track_count is over half way then do not start new track
                                if track_count > config.track_counter / 2:
                                    pass
                                else:
                                    first_event = True    # Too Far Away so restart Track
                            # Did not move much so update event_timer
                            # and wait for next valid movement.
                            else:
                                logging.info(" Out - %i/%i xy(%i,%i) Min D=%i<=%ipx"
                                             " C=%i %ix%i=%i sqpx %s",
                                             track_count, config.track_counter,
                                             track_x, track_y,
                                             abs(track_x - end_pos_x),
                                             config.x_diff_min,
                                             total_contours,
                                             track_w, track_h, biggest_area,
                                             travel_direction)
                                # Restart Track if first event otherwise continue
                                if track_count == 0:
                                    first_event = True
                        event_timer = time.time()  # Reset Event Timer
                if config.gui_window_on:
                    # show small circle at contour xy if required
                    # otherwise a rectangle around most recent contour
                    if config.SHOW_CIRCLE:
                        cv2.circle(image2,
                                   (track_x + config.x_left * config.WINDOW_BIGGER,
                                    track_y + config.y_upper * config.WINDOW_BIGGER),
                                   config.CIRCLE_SIZE, cvGreen, config.LINE_THICKNESS)
                    else:
                        cv2.rectangle(image2,
                                      (int(config.x_left + track_x),
                                       int(config.y_upper + track_y)),
                                      (int(config.x_left + track_x + track_w),
                                       int(config.y_upper + track_y + track_h)),
                                      cvGreen, config.LINE_THICKNESS)
        if config.gui_window_on:
            image2 = speed_image_add_lines(config, image2, cvRed)
            image_view = cv2.resize(image2, (config.get_image_width(), config.get_image_height()))
            cv2.imshow('Movement (q Quits)', image_view)
            if config.show_thresh_on:
                cv2.imshow('Threshold', config.thresholdimage)
            if config.show_crop_on:
                cv2.imshow('Crop Area', image_crop)
            # Close Window if q pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                logging.info("End Motion Tracking ......")
                vs.stop()
                still_scanning = False
        if config.display_fps:   # Optionally show motion image processing loop fps
            fps_time, frame_count = get_fps(fps_time, frame_count)


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

    try:
        WEBCAM_TRIES = 0
        while True:
            # Start Web Cam stream (Note USB webcam must be plugged in)
            if config.WEBCAM:
                WEBCAM_TRIES += 1
                logging.info("Initializing USB Web Camera (Tries %i)..", WEBCAM_TRIES)
                # Start video stream on a processor Thread for faster speed
                webcam_module = importlib.import_module("speedcam.camera.webcam_video_stream")
                vs = webcam_module.WebcamVideoStream(config).start()
                # Not sure how this retry logic works and if it even does, i think this works based on
                # speed_camera handling errors and returning. Regardless this should be encapsulated in
                # the video stream class
                if WEBCAM_TRIES > 3:
                    logging.error("USB Web Cam Not Connecting to WEBCAM_SRC %i",
                                  config.WEBCAM_SRC)
                    logging.error("Check Camera is Plugged In and Working")
                    logging.error("on Specified SRC")
                    logging.error("and Not Used(busy) by Another Process.")
                    logging.error("%s %s Exiting Due to Error",
                                  app_constants.progName, app_constants.progVer)
                    vs.stop()
                    sys.exit(1)
                time.sleep(4.0)  # Allow WebCam to initialize
            else:
                logging.info("Initializing Pi Camera ....")
                picam_module = importlib.import_module("speedcam.camera.pi_video_stream")
                # Start a pi-camera video stream thread
                vs = picam_module.PiVideoStream(config).start()
                time.sleep(2.0)  # Allow PiCamera to initialize
            speed_camera(config, db, vs)  # run main speed camera processing loop
    except KeyboardInterrupt:
        vs.stop()
        print("")
        logging.info("User Pressed Keyboard ctrl-c")
        logging.info("%s %s Exiting Program", app_constants.progName, app_constants.progVer)
        sys.exit()


if __name__ == '__main__':
    main()
