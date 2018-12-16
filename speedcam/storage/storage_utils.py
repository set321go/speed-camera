import logging
import os
import datetime
import glob
import shutil


class StorageUtils:
    MB_TO_BYTE = 1048576

    def __init__(self, config):
        self.config = config
        self.curr_img_path = self.__get_correct_media_path(self.config.image_path)
        self.last_space_check = datetime.datetime.now()

    def __get_correct_media_path(self, path=None):
        if path is None:
            return os.path.join(self.config.base_dir, self.config.media_dir)
        elif os.path.isabs(path):
            return path
        else:
            return os.path.join(self.config.base_dir, self.config.media_dir, path)

    def __is_max_files_exceeded(self, path):
        """ Count number of files in a folder path """
        count = len(glob.glob(path + '/*' + self.config.image_format))
        if count > self.config.imageSubDirMaxFiles:
            logging.info('Total Files in %s Exceeds %i ', path, self.config.imageSubDirMaxFiles)
            return True
        else:
            return False

    def __is_max_dir_time_exceeded(self, path):
        """ extract the date-time from the directory name """
        # Note to self need to add error checking
        # split dir path and get the directory name and remove the prefix
        dir_name = os.path.basename(path).replace(self.config.image_prefix, '')
        # convert string to datetime
        dir_name_date = datetime.datetime.strptime(dir_name, "%Y-%m-%d-%H:%M")
        diff = datetime.datetime.now() - dir_name_date  # get time difference between dates
        diff_in_hrs = diff.days * 24 + diff.seconds // 3600  # convert to hours
        if diff_in_hrs > self.config.imageSubDirMaxHours:   # See if hours are exceeded
            logging.info('MaxHrs %i Exceeds %i for %s', diff_in_hrs, self.config.imageSubDirMaxHours, path)
            return True
        else:
            return False

    def __free_space_check(self):
        """ Free disk space by deleting some older files """
        if self.config.spaceTimerHrs > 0:   # Check if disk free space timer hours is enabled
            # See if it is time to do disk clean-up check
            current_time = datetime.datetime.now()
            if (current_time - self.last_space_check).total_seconds() > self.config.spaceTimerHrs * 3600:
                self.free_space()
                self.last_space_check = current_time

    def __rotate_image_dir(self):
        """ Check if motion SubDir needs to be created """
        # only create subdirectories if max files or max hours is greater than zero
        if self.config.imageSubDirMaxHours > 1 or self.config.imageSubDirMaxFiles > 1:
            # if the current img directory is the image path look for sub directories
            if self.curr_img_path == self.__get_correct_media_path(self.config.image_path):
                sub_dir_path = self.__scan_dir_for_latest(self.curr_img_path)
                # if no sub dirs were found create one
                if sub_dir_path is None:
                    logging.info('No sub folders Found in %s', self.curr_img_path)
                    self.curr_img_path = self.create_dir(self.generate_dir_name(self.config.image_prefix))
            else:
                sub_dir_path = self.curr_img_path

            # If max hours is enabled and max files is disabled and max hours has been exceeded create new dir
            if self.config.imageSubDirMaxHours > 0 \
                    and self.config.imageSubDirMaxFiles < 1 \
                    and self.__is_max_dir_time_exceeded(sub_dir_path):
                self.curr_img_path = self.create_dir(self.generate_dir_name(self.config.image_prefix))
            # If max files is enabled and max hours is disabled and max files has been exceeded create new dir
            elif self.config.imageSubDirMaxHours < 1 \
                    and self.config.imageSubDirMaxFiles > 0 \
                    and self.__is_max_files_exceeded(sub_dir_path):
                self.curr_img_path = self.create_dir(self.generate_dir_name(self.config.image_prefix))
            # If max files is enabled and max hours is enabled and both have been exceeded create new dir
            elif self.config.imageSubDirMaxHours > 0 \
                    and self.config.imageSubDirMaxFiles > 0 \
                    and self.__is_max_dir_time_exceeded(sub_dir_path) \
                    and self.__is_max_files_exceeded(sub_dir_path):
                self.curr_img_path = self.create_dir(self.generate_dir_name(self.config.image_prefix))

    def __save_recent(self, filename):
        """
        Create a symlink file in recent folder or file if non unix system
        or symlink creation fails.
        Delete Oldest symlink file if recentMax exceeded.
        """
        src = os.path.abspath(filename)  # Original Source File Path
        # Destination Recent Directory Path
        dest = os.path.abspath(os.path.join(self.get_image_recent_path(), os.path.basename(filename)))
        StorageUtils.__delete_old_files(self.config.imageRecentMax, self.get_image_recent_path(), self.config.image_prefix)
        try:    # Create symlink in recent folder
            logging.info('   symlink %s', dest)
            os.symlink(src, dest)  # Create a symlink to actual file
        except NotImplementedError:
            logging.info("Symlinks not supported on pre Windows Vista attempting copy")
            try:  # Copy image file to recent folder (if no support for symlinks)
                shutil.copy(filename, self.config.imageRecentDir)
            except OSError as err:
                logging.error('Copy failed from %s to %s - %s', filename, self.config.imageRecentDir, err)
        except OSError as err:
            logging.error('symlink Failed: %s', err)

    def get_image_path(self):
        return self.curr_img_path

    def get_image_recent_path(self):
        if os.path.isabs(self.config.imageRecentDir):
            return self.config.imageRecentDir
        else:
            return os.path.join(self.get_image_path(), self.config.imageRecentDir)

    def get_html_path(self):
        return self.__get_correct_media_path(self.config.html_path)

    def get_search_results_path(self):
        return self.__get_correct_media_path(self.config.search_dest_path)

    def filesystem_housekeeping(self, filename):
        # Check if we need to clean the disk
        self.__free_space_check()
        # Check if we need to rotate the image dir
        self.__rotate_image_dir()
        # Manage a maximum number of files
        # and delete oldest if required.
        if self.config.image_max_files > 0:
            StorageUtils.__delete_old_files(self.config.image_max_files,
                                            self.get_image_path(),
                                            self.config.image_prefix)
        # Save most recent files
        # to a recent folder if required
        if self.config.imageRecentMax > 0 and not self.config.calibrate:
            self.__save_recent(filename)

    def free_space(self):
        """
        Walks mediaDir and deletes oldest files
        until spaceFreeMB is achieved Use with Caution
        """
        logging.info('Free disk space with spaceTimerHrs=%i  diskFreeMB=%i  spaceMediaDir=%s spaceFileExt=%s',
                     self.config.spaceTimerHrs,
                     self.config.spaceFreeMB,
                     self.config.spaceMediaDir,
                     self.config.spaceFileExt)
        media_path = self.__get_correct_media_path()
        if os.path.isdir(media_path):
            target_free = self.config.spaceFreeMB * self.MB_TO_BYTE
            files = StorageUtils.__find_files(self.config.mediaDir, self.config.spaceFileExt)
            initial_files_count = len(files)
            delcnt = 0
            logging.info('Cleanup Disk Space Session Started')
            while files:
                statv = os.statvfs(media_path)
                available_free = statv.f_bfree * statv.f_bsize
                if available_free >= target_free:
                    break
                file_path = files.pop()
                try:
                    os.remove(file_path)
                except OSError as err:
                    logging.error('Del Failed %s', file_path)
                    logging.error('Error: %s', err)
                else:
                    delcnt += 1
                    logging.info('Del %s', file_path)
                    logging.info('Target=%i MB  Avail=%i MB  Deleted %i of %i Files ',
                                 target_free / self.MB_TO_BYTE,
                                 available_free / self.MB_TO_BYTE,
                                 delcnt, initial_files_count)
                    # Avoid deleting more than 1/4 of files at one time
                    if delcnt > initial_files_count / 4:
                        logging.warning('Max Deletions Reached %i of %i', delcnt, initial_files_count)
                        logging.warning('Deletions Restricted to 1/4 of total files per session.')
                        break
            logging.info('Cleanup Disk Space Session Ended')
        else:
            logging.error('Directory Not Found - %s', media_path)

    @staticmethod
    def __scan_dir_for_latest(directory):
        """ Scan for directories and return most recent """
        dir_list = ([name for name in os.listdir(directory)
                    if os.path.isdir(os.path.join(directory, name))])
        if len(dir_list) > 0:
            sub_dir = sorted(dir_list)[-1]
            sub_dir = os.path.join(directory, sub_dir)
        else:
            sub_dir = None
        return sub_dir

    @staticmethod
    def __find_files(dir_path, extension):
        """ Return a list of files to be deleted """
        return sorted({dirEntry.stat.st_mtime: dirEntry.path
                      for dirEntry in os.scandir(dir_path)
                      if dirEntry.name.endswith(extension)},
                      reverse=True)

    @staticmethod
    def __delete_old_files(max_files, path, prefix):
        """
        Delete Oldest files gt or
        equal to maxfiles that match filename prefix
        """
        try:
            files = sorted(glob.glob(os.path.join(path, prefix + '*')),
                           key=os.path.getmtime)
        except OSError as err:
            logging.error('Problem Reading Directory %s - %s', path, err)
        else:
            while len(files) >= max_files:
                oldest = files.pop(0)
                try:   # Remove oldest file in recent folder
                    os.remove(oldest)
                except OSError as err:
                    logging.error('Cannot Remove %s - %s', oldest, err)

    @staticmethod
    def create_dir(path):
        if not os.path.isdir(path):
            logging.info("Creating Folder %s", path)
            try:
                os.makedirs(path)
                return path
            except OSError as err:
                logging.error('Failed to Create Folder %s - %s', path, err)
                return None

    @staticmethod
    def generate_dir_name(prefix):
        now = datetime.datetime.now()
        return '%s%d%02d%02d-%02d%02d' % (prefix, now.year, now.month, now.day, now.hour, now.minute)
