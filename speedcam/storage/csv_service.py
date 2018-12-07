import logging
import os


class CSVStorageService:
    INCLUDE_HEADER = False
    HEADER_TEXT = '''"YYYYMMDD","HH","MM","Speed","Unit","Speed Photo Path","X","Y","W","H","Area","Direction"' + "\n"'''
    CSV_FILE_NAME = 'speed_cam.csv'

    def __init__(self, config):
        self.is_active = config.log_data_to_CSV
        self.log_file_path = os.path.join(config.data_dir, self.CSV_FILE_NAME)

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
