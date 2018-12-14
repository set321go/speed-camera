import cv2
import datetime
import logging


class ImgFileUtils:
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

    def save_img(self, big_image):

        logging.info(" Saved %s", self.filename)
        # Save resized image
        cv2.imwrite(self.filename, big_image)
