import os
import configparser
import logging
import sys
from config import config_validation
from config import app_constants


class Config:

    def __init__(self):
        self.base_dir = os.getcwd()
        config = configparser.ConfigParser()
        config_file_path = os.path.join(self.base_dir, "config.ini")
        if not os.path.exists(config_file_path):
            logging.warning("Missing config.ini file - Looking for %s", config_file_path)
            logging.info("Using preconfigured defaults")
            config_file = os.path.join(self.base_dir, 'config', 'default_config.ini')
            config.read(config_file)
        else:
            config.read(config_file_path)

        # Load plugin config
        self.pluginEnable = config.getboolean('GENERAL', 'pluginEnable', fallback=False)
        self.pluginName = config_validation.remove_python_extension(config.get('GENERAL', 'pluginName', fallback='picam240'))
        plugin_config = self.__load_plugin_overrides()
        # load data with config & possible plugin

        self.calibrate = self.__get_boolean(config, plugin_config, 'GENERAL', 'calibrate', True)
        self.cal_obj_px = self.__get_int(config, plugin_config, 'GENERAL', 'cal_obj_px', 90)
        self.cal_obj_mm = self.__get_float(config, plugin_config, 'GENERAL', 'cal_obj_mm', 4700.0)
        self.x_left = self.__get_int(config, plugin_config, 'GENERAL', 'x_left', 25)
        self.x_right = self.__get_int(config, plugin_config, 'GENERAL', 'x_right', 295)
        self.y_upper = self.__get_int(config, plugin_config, 'GENERAL', 'y_upper', 75)
        self.y_lower = self.__get_int(config, plugin_config, 'GENERAL', 'y_lower', 185)
        self.gui_window_on = self.__get_boolean(config, plugin_config, 'GENERAL', 'gui_window_on', False)
        self.show_thresh_on = self.__get_boolean(config, plugin_config, 'GENERAL', 'show_thresh_on', False)
        self.show_crop_on = self.__get_boolean(config, plugin_config, 'GENERAL', 'show_crop_on', False)
        self.verbose = self.__get_boolean(config, plugin_config, 'GENERAL', 'verbose', True)
        self.display_fps = self.__get_boolean(config, plugin_config, 'GENERAL', 'display_fps', False)
        self.data_dir = self.__get_str(config, plugin_config, 'GENERAL', 'data_dir', 'data')
        self.log_data_to_CSV = self.__get_boolean(config, plugin_config, 'GENERAL', 'log_data_to_CSV', True)
        self.loggingToFile = self.__get_boolean(config, plugin_config, 'GENERAL', 'loggingToFile', False)
        self.logFilePath = self.__get_str(config, plugin_config, 'GENERAL', 'logFilePath', 'speed-cam.log')
        self.SPEED_MPH = self.__get_boolean(config, plugin_config, 'GENERAL', 'SPEED_MPH', False)
        self.track_counter = self.__get_int(config, plugin_config, 'GENERAL', 'track_counter', 5)
        self.MIN_AREA = self.__get_int(config, plugin_config, 'GENERAL', 'MIN_AREA', 100)
        self.track_len_trig = self.__get_int(config, plugin_config, 'GENERAL', 'track_len_trig', 70)
        self.show_out_range = self.__get_boolean(config, plugin_config, 'GENERAL', 'show_out_range', True)
        self.x_diff_max = self.__get_int(config, plugin_config, 'GENERAL', 'x_diff_max', 20)
        self.x_diff_min = self.__get_int(config, plugin_config, 'GENERAL', 'x_diff_min', 1)
        self.x_buf_adjust = self.__get_int(config, plugin_config, 'GENERAL', 'x_buf_adjust', 10)
        self.track_timeout = self.__get_float(config, plugin_config, 'GENERAL', 'track_timeout', 0.0)
        self.event_timeout = self.__get_float(config, plugin_config, 'GENERAL', 'event_timeout', 0.3)
        self.max_speed_over = self.__get_int(config, plugin_config, 'GENERAL', 'max_speed_over', 0)

        self.WEBCAM = self.__get_boolean(config, plugin_config, 'CAMERA', 'WEBCAM', False)
        self.WEBCAM_SRC = self.__get_int(config, plugin_config, 'CAMERA', 'WEBCAM_SRC', 0)
        self.WEBCAM_WIDTH = self.__get_int(config, plugin_config, 'CAMERA', 'WEBCAM_WIDTH', 320)
        self.WEBCAM_HEIGHT = self.__get_int(config, plugin_config, 'CAMERA', 'WEBCAM_HEIGHT', 240)
        self.WEBCAM_HFLIP = self.__get_boolean(config, plugin_config, 'CAMERA', 'WEBCAM_HFLIP', True)
        self.WEBCAM_VFLIP = self.__get_boolean(config, plugin_config, 'CAMERA', 'WEBCAM_VFLIP', False)
        self.CAMERA_WIDTH = self.__get_int(config, plugin_config, 'CAMERA', 'CAMERA_WIDTH', 320)
        self.CAMERA_HEIGHT = self.__get_int(config, plugin_config, 'CAMERA', 'CAMERA_HEIGHT', 240)
        self.CAMERA_FRAMERATE = self.__get_int(config, plugin_config, 'CAMERA', 'CAMERA_FRAMERATE', 20)
        self.CAMERA_ROTATION = self.__get_int(config, plugin_config, 'CAMERA', 'CAMERA_ROTATION', 0)
        self.CAMERA_VFLIP = self.__get_boolean(config, plugin_config, 'CAMERA', 'CAMERA_VFLIP', True)
        self.CAMERA_HFLIP = self.__get_boolean(config, plugin_config, 'CAMERA', 'CAMERA_HFLIP', True)
        self.image_path = self.__get_str(config, plugin_config, 'CAMERA', 'image_path', 'media/images')
        self.image_prefix = self.__get_str(config, plugin_config, 'CAMERA', 'image_prefix', 'speed-')
        self.image_format = self.__get_str(config, plugin_config, 'CAMERA', 'image_format', '.jpg')
        self.image_show_motion_area = self.__get_boolean(config, plugin_config, 'CAMERA', 'image_show_motion_area', True)
        self.image_filename_speed = self.__get_boolean(config, plugin_config, 'CAMERA', 'image_filename_speed', False)
        self.image_text_on = self.__get_boolean(config, plugin_config, 'CAMERA', 'image_text_on', True)
        self.image_text_bottom = self.__get_boolean(config, plugin_config, 'CAMERA', 'image_text_bottom', True)
        self.image_font_size = self.__get_int(config, plugin_config, 'CAMERA', 'image_font_size', 12)
        self.image_bigger = config_validation.enforce_lower_bound_float(
            self.__get_float(config, plugin_config, 'CAMERA', 'image_bigger', 3.0), 1.0)
        self.image_max_files = self.__get_int(config, plugin_config, 'CAMERA', 'image_max_files', 0)
        self.imageSubDirMaxFiles = self.__get_int(config, plugin_config, 'CAMERA', 'imageSubDirMaxFiles', 1000)
        self.imageSubDirMaxHours = self.__get_int(config, plugin_config, 'CAMERA', 'imageSubDirMaxHours', 0)
        self.imageRecentMax = self.__get_int(config, plugin_config, 'CAMERA', 'imageRecentMax', 100)
        self.imageRecentDir = self.__get_str(config, plugin_config, 'CAMERA', 'imageRecentDir', 'media/recent')
        self.spaceTimerHrs = self.__get_int(config, plugin_config, 'CAMERA', 'spaceTimerHrs', 0)
        self.spaceFreeMB = self.__get_int(config, plugin_config, 'CAMERA', 'spaceFreeMB', 500)
        self.spaceMediaDir = self.__get_str(config, plugin_config, 'CAMERA', 'spaceMediaDir', 'media/images')
        self.spaceFileExt = self.__get_str(config, plugin_config, 'CAMERA', 'spaceFileExt', 'media/recent')
        self.SHOW_CIRCLE = self.__get_boolean(config, plugin_config, 'CAMERA', 'SHOW_CIRCLE', False)
        self.CIRCLE_SIZE = self.__get_int(config, plugin_config, 'CAMERA', 'CIRCLE_SIZE', 5)
        self.LINE_THICKNESS = self.__get_int(config, plugin_config, 'CAMERA', 'LINE_THICKNESS', 1)
        self.FONT_SCALE = self.__get_float(config, plugin_config, 'CAMERA', 'FONT_SCALE', 0.5)
        self.WINDOW_BIGGER = config_validation.enforce_lower_bound_float(
            self.__get_float(config, plugin_config, 'CAMERA', 'WINDOW_BIGGER', 1.0), 1.0)
        self.BLUR_SIZE = self.__get_int(config, plugin_config, 'CAMERA', 'BLUR_SIZE', 10)
        self.THRESHOLD_SENSITIVITY = self.__get_int(config, plugin_config, 'CAMERA', 'THRESHOLD_SENSITIVITY', 20)

        self.web_server_port = self.__get_int(config, plugin_config, 'SERVER', 'web_server_port', 8080)
        self.web_server_root = self.__get_str(config, plugin_config, 'SERVER', 'web_server_root', 'media')
        self.web_page_title = self.__get_str(config, plugin_config, 'SERVER', 'web_page_title', 'SPEED-CAMERA Media')
        self.web_page_refresh_on = self.__get_boolean(config, plugin_config, 'SERVER', 'web_page_refresh_on', True)
        self.web_page_refresh_sec = self.__get_str(config, plugin_config, 'SERVER', 'web_page_refresh_sec', '900')
        self.web_page_blank = self.__get_boolean(config, plugin_config, 'SERVER', 'web_page_blank', False)
        self.web_image_height = self.__get_str(config, plugin_config, 'SERVER', 'web_image_height', '768')
        self.web_iframe_width_usage = self.__get_str(config, plugin_config, 'SERVER', 'web_iframe_width_usage', '70%%')
        self.web_iframe_width = self.__get_str(config, plugin_config, 'SERVER', 'web_iframe_width', '100%%')
        self.web_iframe_height = self.__get_str(config, plugin_config, 'SERVER', 'web_iframe_height', '100%%')
        self.web_max_list_entries = self.__get_int(config, plugin_config, 'SERVER', 'web_max_list_entries', 0)
        self.web_list_height = self.__get_str(config, plugin_config, 'SERVER', 'web_image_height', '768')
        self.web_list_by_datetime = self.__get_boolean(config, plugin_config, 'SERVER', 'web_list_by_datetime', True)
        self.web_list_sort_descending = self.__get_boolean(config, plugin_config, 'SERVER', 'web_list_sort_descending', True)

    def __get_str(self, config, plugin, section, attr_name, default_value):
        value = config.get(section, attr_name, fallback=default_value)
        if plugin is not None:
            return plugin.get(section, attr_name, fallback=value)
        else:
            return value

    def __get_boolean(self, config, plugin, section, attr_name, default_value):
        value = config.getboolean(section, attr_name, fallback=default_value)
        if plugin is not None:
            return plugin.getboolean(section, attr_name, fallback=value)
        else:
            return value

    def __get_int(self, config, plugin, section, attr_name, default_value):
        value = config.getint(section, attr_name, fallback=default_value)
        if plugin is not None:
            return plugin.getint(section, attr_name, fallback=value)
        else:
            return value

    def __get_float(self, config, plugin, section, attr_name, default_value):
        value = config.getfloat(section, attr_name, fallback=default_value)
        if plugin is not None:
            return plugin.getfloat(section, attr_name, fallback=value)
        else:
            return value

    def __load_plugin_overrides(self):
        if self.pluginEnable:
            plugin_path = os.path.join(self.base_dir, "plugins", self.pluginName + '.ini')
            logging.info("pluginEnabled - loading pluginName %s", plugin_path)
            if not os.path.exists(plugin_path):
                logging.error("File Not Found pluginName %s", plugin_path)
                logging.info("Check Spelling of pluginName Value in %s", "config.ini")
                sys.exit(1)
            plugin_config = configparser.ConfigParser()
            plugin_config.read(plugin_path)
            return plugin_config
        else:
            logging.info("plugins not enabled")
            return None

    # Ideally these values should be pre computed not calculated repeatedly at runtime
    def get_speed_units(self):
        return "mph" if self.SPEED_MPH else "kph"

    def get_speed_conf(self):
        # Calculate conversion from camera pixel width to actual speed.
        px_to_kph = float(self.cal_obj_mm/self.cal_obj_px * 0.0036)
        return 0.621371 * px_to_kph if self.SPEED_MPH else px_to_kph

    def get_image_width(self):
        return int(self.WEBCAM_WIDTH * self.image_bigger) if self.WEBCAM else int(self.CAMERA_WIDTH * self.image_bigger)

    def get_image_height(self):
        return int(self.WEBCAM_HEIGHT * self.image_bigger) if self.WEBCAM else int(self.CAMERA_HEIGHT * self.image_bigger)

    def get_x_buf(self):
        # setup buffer area to ensure contour is mostly contained in crop area
        return int((self.x_right - self.x_left) / self.x_buf_adjust)

    def display_config_verbose(self):
        """Initialize and Display program variable settings from config.py"""

        if self.verbose:
            logging.info(app_constants.horz_line)
            logging.info("Note: To Send Full Output to File Use command")
            logging.info("python -u ./%s | tee -a log.txt", app_constants.progName)
            logging.info("Set log_data_to_file=True to Send speed_Data to CSV File %s.log", app_constants.progName)
            logging.info(app_constants.horz_line)
            logging.info("")

            logging.info("Debug Messages .. verbose=%s  display_fps=%s calibrate=%s", self.verbose, self.display_fps, self.calibrate)
            logging.info("                  show_out_range=%s", self.show_out_range)
            logging.info("Plugins ......... pluginEnable=%s  pluginName=%s", self.pluginEnable, self.pluginName)
            logging.info("Calibration ..... cal_obj_px=%i px  cal_obj_mm=%i mm (longer is faster) speed_conv=%.5f",
                         self.cal_obj_px, self.cal_obj_mm, self.get_speed_conf())
            if self.pluginEnable:
                logging.info("                  (Change Settings in %s)", os.path.join(self.base_dir, "plugins", self.pluginName + '.ini'))
            else:
                logging.info("                  (Change Settings in %s)", 'config.ini')
            logging.info("Logging ......... Log_data_to_CSV=%s  log_filename=%s.csv (CSV format)",
                         self.log_data_to_CSV, os.path.join(self.data_dir, 'speed_cam.csv'))
            logging.info("                  loggingToFile=%s  logFilePath=%s", self.loggingToFile, self.logFilePath)
            logging.info("                  SQLITE3 DB_PATH=%s  DB_TABLE=%s", os.path.join(self.data_dir, 'speed_cam.db'), 'speed')
            logging.info("Speed Trigger ... Log only if max_speed_over > %i %s", self.max_speed_over, self.get_speed_units())
            logging.info("                  and track_counter >= %i consecutive motion events", self.track_counter)
            logging.info("Exclude Events .. If  x_diff_min < %i or x_diff_max > %i px", self.x_diff_min, self.x_diff_max)
            logging.info("                  If  y_upper < %i or y_lower > %i px", self.y_upper, self.y_lower)
            logging.info("                  or  x_left < %i or x_right > %i px", self.x_left, self.x_right)
            logging.info("                  If  max_speed_over < %i %s", self.max_speed_over, self.get_speed_units())
            logging.info("                  If  event_timeout > %.2f seconds Start New Track", self.event_timeout)
            logging.info("                  track_timeout=%.2f sec wait after Track Ends (avoid retrack of same object)", self.track_timeout)
            logging.info("Speed Photo ..... Size=%ix%i px  image_bigger=%.1f  rotation=%i  VFlip=%s  HFlip=%s ",
                         self.get_image_width(), self.get_image_height(), self.image_bigger, self.CAMERA_ROTATION,
                         self.CAMERA_VFLIP, self.CAMERA_HFLIP)
            logging.info("                  image_path=%s  image_Prefix=%s", self.image_path, self.image_prefix)
            logging.info("                  image_font_size=%i px high  image_text_bottom=%s", self.image_font_size, self.image_text_bottom)
            logging.info("Motion Settings . Size=%ix%i px  speed_conv=%f  speed_units=%s",
                         self.CAMERA_WIDTH, self.CAMERA_HEIGHT, self.get_speed_conf(), self.get_speed_units())
            logging.info("OpenCV Settings . MIN_AREA=%i sq-px  BLUR_SIZE=%i THRESHOLD_SENSITIVITY=%i  CIRCLE_SIZE=%i px",
                         self.MIN_AREA, self.BLUR_SIZE, self.THRESHOLD_SENSITIVITY, self.CIRCLE_SIZE)
            logging.info("                  WINDOW_BIGGER=%i gui_window_on=%s (Display OpenCV Status Windows on GUI Desktop)",
                         self.WINDOW_BIGGER, self.gui_window_on)
            logging.info("                  CAMERA_FRAMERATE=%i fps video stream speed", self.CAMERA_FRAMERATE)
            logging.info("Sub-Directories . imageSubDirMaxHours=%i (0=off) imageSubDirMaxFiles=%i (0=off)",
                         self.imageSubDirMaxHours, self.imageSubDirMaxFiles)
            logging.info("                  imageRecentDir=%s imageRecentMax=%i (0=off)", self.imageRecentDir, self.imageRecentMax)
            if self.spaceTimerHrs > 0:   # Check if disk mgmt is enabled
                logging.info("Disk Space  ..... Enabled - Manage Target Free Disk Space. Delete Oldest %s Files if Needed", self.spaceFileExt)
                logging.info("                  Check Every spaceTimerHrs=%i hr(s) (0=off)  Target spaceFreeMB=%i MB  min is 100 MB)",
                             self.spaceTimerHrs, self.spaceFreeMB)
                logging.info("                  If Needed Delete Oldest spaceFileExt=%s  spaceMediaDir=%s",
                             self.spaceFileExt, self.spaceMediaDir)
            else:
                logging.info("Disk Space  ..... Disabled - spaceTimerHrs=%i Manage Target Free Disk Space. Delete Oldest %s Files",
                             self.spaceTimerHrs, self.spaceFileExt)
                logging.info("                  spaceTimerHrs=%i (0=Off) Target spaceFreeMB=%i (min=100 MB)",
                             self.spaceTimerHrs, self.spaceFreeMB)
            logging.info("")
            logging.info(app_constants.horz_line)
