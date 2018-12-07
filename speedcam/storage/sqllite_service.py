import os
import logging
import sqlite3


class SqlLiteStorageService:
    DB_NAME = "speed_cam.db"
    DB_TABLE = "speed"
    CREATE_TABLE = '''create table if not exists speed (idx text primary key,
                 log_date text, log_hour text, log_minute text,
                 camera text,
                 ave_speed real, speed_units text, image_path text,
                 image_w integer, image_h integer, image_bigger integer,
                 direction text, plugin_name text,
                 cx integer, cy integer,
                 mw integer, mh integer, m_area integer,
                 x_left integer, x_right integer,
                 y_upper integer, y_lower integer,
                 max_speed_over integer,
                 min_area integer, track_counter integer,
                 cal_obj_px integer, cal_obj_mm integer)'''
    INSERT_DATA = '''insert into speed values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''

    def __init__(self, config):
        if not os.path.exists(config.data_dir):
            os.makedirs(config.data_dir)

        self.DB_PATH = os.path.join(config.data_dir, self.DB_NAME)
        self.conn = None

    def start(self):
        if not self.__exists():
            self.__create()
        self.conn = self.__connect()

    def is_available(self):
        return True if self.conn is not None else False

    def save_speed_data(self, speed_data):
        try:
            self.conn.cursor().execute(self.INSERT_DATA, speed_data)
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error("sqlite3 DB %s", self.DB_PATH)
            logging.error("Failed: To INSERT Speed Data into TABLE %s", self.DB_TABLE)
            logging.error("Err Msg: %s", e)
        else:
            logging.info(" SQL - Update sqlite3 Data in %s", self.DB_PATH)

    def __create(self):
        logging.warning("File Not Found %s", self.DB_PATH)
        logging.info("Create sqlite3 database File %s", self.DB_PATH)
        try:
            conn = sqlite3.connect(self.DB_PATH)
        except sqlite3.Error as e:
            logging.error("Failed: Create Database %s.", self.DB_PATH)
            logging.error("Error Msg: %s", e)
            return False
        else:
            conn.commit()
        logging.info("Success: Created sqlite3 Database %s", self.DB_PATH)

        try:
            conn.cursor().execute(self.CREATE_TABLE)
        except sqlite3.Error as e:
            logging.error("Failed: To Create Table %s on sqlite3 DB %s", self.DB_TABLE, self.DB_PATH)
            logging.error("Error Msg: %s", e)
            return None
        else:
            conn.commit()
        logging.info("Success: Created Database table %s", self.DB_TABLE)
        conn.close()
        return True

    def __exists(self):
        if os.path.isfile(self.DB_PATH):
            if os.path.getsize(self.DB_PATH) < 100: # SQLite database file header is 100 bytes
                size = os.path.getsize(self.DB_PATH)
                logging.error("%s %d is Less than 100 bytes", self.DB_PATH, size)
                return False
            with open(self.DB_PATH, 'rb') as fd:
                header = fd.read(100)
                if header.startswith(b'SQLite format 3'):
                    logging.info("Success: File is sqlite3 Format %s", self.DB_PATH)
                    return True
                else:
                    logging.error("Failed: File NOT sqlite3 Header Format %s", self.DB_PATH)
                    return False
        else:
            return False

    def __connect(self):
        try:
            conn = sqlite3.connect(self.DB_PATH)
        except sqlite3.Error as e:
            logging.error("Failed: sqlite3 Connect to DB %s", self.DB_PATH)
            logging.error("Error Msg: %s", e)
            return None
        else:
            conn.commit()
        logging.info("Success: sqlite3 Connected to DB %s", self.DB_PATH)
        return conn
