from speedcam.camera.utils import *
from speedcam.tracking import utils


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

    def init_capture_data(self):
        self.curr_img = self.stream.read()
        self.curr_img_crop = self.__crop_image()
        if self.curr_img_crop is None:
            raise CameraException()
        self.curr_img_gray = cv2.cvtColor(self.curr_img_crop, cv2.COLOR_BGR2GRAY)

    def calculate_speed_contours(self):
        self.prev_img = self.curr_img
        self.prev_img_crop = self.curr_img_crop
        self.prev_img_gray = self.curr_img_gray

        for attempt in range(10):
            self.curr_img = self.stream.read()  # Read image data from video steam thread instance
            # crop image to motion tracking area only
            try:
                self.curr_img_crop = self.__crop_image()
            except CameraException:
                if attempt == 9:
                    raise

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

    def process_img(self, ave_speed, filename, tracking_box):
        processed_img = self.curr_img
        # Add motion rectangle to image if required
        if self.config.image_show_motion_area:
            processed_img = speed_image_add_lines(self.config, processed_img, cvRed)
            utils.draw_geom_overlay(self.config, processed_img, tracking_box.track_x, tracking_box.track_y,
                                    tracking_box.track_w, tracking_box.track_h)
        # Write text on image
        if self.config.image_text_on:
            self.__draw_text_overlay(filename, ave_speed, processed_img)

        return cv2.resize(processed_img, (self.config.get_image_width(), self.config.get_image_height()))


class CameraException(BaseException):
    """ General Exception for camera connection errors. """
    pass
