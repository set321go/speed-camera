import logging
import os
from config import app_constants


class CSVStorageService:
    INCLUDE_HEADER = False
    HEADER_TEXT = '''"YYYYMMDD","HH","MM","Speed","Unit","Speed Photo Path","X","Y","W","H","Area","Direction"' + "\n"'''
    CSV_FILE_NAME = 'speed_cam.csv'

    def __init__(self, config):
        self.is_active = config.log_data_to_CSV
        self.log_file_path = os.path.join(config.data_dir, self.CSV_FILE_NAME)
        self.config = config

    def write_line(self, data_to_append):
        """ Store date to a comma separated value file """
        line = data_to_append + "\n"

        if os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'a+') as f:
                f.write(line)
        else:
            with open(self.log_file_path, 'w') as f:
                if self.INCLUDE_HEADER:
                    f.write(self.HEADER_TEXT)
                f.write(line)
            logging.info("Create New Data Log File %s", self.log_file_path)

        logging.info("   CSV - Updated Data  %s", self.log_file_path)

    def format_data(self, log_time, filename, travel_direction, ave_speed, track_x, track_y, track_w, track_h):
        # Needs a bunch of cleanup. at least 50% of each row being saved are config constants.
        # Must be a better way of formatting date strings
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
        return ("%s,%.2f,%s%s%s,%s%s%s,%i,%i,%i,%i,%i,%s%s%s"
                % (log_csv_time,
                   ave_speed,
                   app_constants.QUOTE,
                   self.config.get_speed_units(),
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
