import collections
import cv2
import time


TrackingBox = collections.namedtuple('TrackingBox', ['track_x', 'track_y', 'track_w', 'track_h'])


class MotionTrack:
    def __init__(self, config):
        self.config = config
        self.track_count = 0
        self.speed_list = []
        self.last_seen = time.time()
        self.first_event = True
        self.track_start_time = None
        self.prev_start_time = None
        self.start_pos_x = None
        self.end_pos_x = None
        self.diff_x = None
        self.prev_end_pos_x = None
        self.cur_ave_speed = None
        self.travel_dir = ""

    def has_exceeded_track_timeout(self):
        reset_time_diff = time.time() - self.last_seen
        return reset_time_diff > self.config.event_timeout

    def has_track_count_exceeded_track_limit(self):
        return self.track_count >= self.config.track_counter

    def is_within_range(self):
        return self.config.x_diff_min < self.diff_x < self.config.x_diff_max

    def is_first_event(self):
        return self.first_event

    def is_object_speeding(self):
        return self.get_avg_speed() > self.config.max_speed_over

    def get_avg_speed(self):
        # ave_speed = float((abs(tot_track_dist / tot_track_time)) * speed_conv)
        return sum(self.speed_list) / float(len(self.speed_list))

    def get_travel_dir(self):
        return self.travel_dir

    def update_end_pos_x(self, track_x):
        diff = track_x - self.end_pos_x
        self.travel_dir = "L2R" if diff > 0 else "R2L"
        self.diff_x = abs(diff)
        self.end_pos_x = track_x

    def calculate_track_dist(self, track_x):
        return abs(track_x - self.start_pos_x)

    def calculate_track_time(self, cur_track_time):
        return abs(self.track_start_time - cur_track_time)

    def record_speed(self, curr_track_time):
        self.cur_ave_speed = float((abs(self.diff_x /
                                        float(abs(curr_track_time -
                                                  self.prev_start_time)))) *
                                   self.config.get_speed_conf())
        self.speed_list.append(self.cur_ave_speed)

    def reset_tracking(self, track_start_time, start_pos_x):
        self.track_start_time = track_start_time  # Record track start time
        self.prev_start_time = track_start_time
        self.start_pos_x = start_pos_x
        self.end_pos_x = start_pos_x
        self.last_seen = time.time()  # Reset event timeout
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
        box = TrackingBox(track_x, track_y, track_w, track_h)
        return biggest_area, box if all(box) else None
