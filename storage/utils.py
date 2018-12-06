import logging
import os
import datetime
import glob
import shutil


def subDirLatest(directory):
    """ Scan for directories and return most recent """
    dirList = ([name for name in os.listdir(directory)
                if os.path.isdir(os.path.join(directory, name))])
    if len(dirList) > 0:
        lastSubDir = sorted(dirList)[-1]
        lastSubDir = os.path.join(directory, lastSubDir)
    else:
        lastSubDir = directory
    return lastSubDir


def subDirCreate(directory, prefix):
    """ Create media subdirectories base on required naming """
    now = datetime.datetime.now()
    # Specify folder naming
    subDirName = ('%s%d%02d%02d-%02d%02d' %
                  (prefix,
                   now.year, now.month, now.day,
                   now.hour, now.minute))
    subDirPath = os.path.join(directory, subDirName)
    if not os.path.exists(subDirPath):
        try:
            os.makedirs(subDirPath)
        except OSError as err:
            logging.error('Cannot Create Dir %s - %s, using default location.',
                          subDirPath, err)
            subDirPath = directory
        else:
            logging.info('Created %s', subDirPath)
    else:
        subDirPath = directory
    return subDirPath


def deleteOldFiles(maxFiles, dirPath, prefix):
    """
    Delete Oldest files gt or
    equal to maxfiles that match filename prefix
    """
    try:
        fileList = sorted(glob.glob(os.path.join(dirPath, prefix + '*')),
                          key=os.path.getmtime)
    except OSError as err:
        logging.error('Problem Reading Directory %s - %s', dirPath, err)
    else:
        while len(fileList) >= maxFiles:
            oldest = fileList[0]
            oldestFile = oldest
            try:   # Remove oldest file in recent folder
                fileList.remove(oldest)
                os.remove(oldestFile)
            except OSError as err:
                logging.error('Cannot Remove %s - %s', oldestFile, err)


def subDirCheckMaxFiles(directory, filesMax):
    """ Count number of files in a folder path """
    fileList = glob.glob(directory + '/*jpg')
    count = len(fileList)
    if count > filesMax:
        makeNewDir = True
        logging.info('Total Files in %s Exceeds %i ', directory, filesMax)
    else:
        makeNewDir = False
    return makeNewDir


def subDirCheckMaxHrs(directory, hrsMax, prefix):
    """ extract the date-time from the directory name """
    # Note to self need to add error checking
    dirName = os.path.split(directory)[1]   # split dir path and keep dirName
    # remove prefix from dirName so just date-time left
    dirStr = dirName.replace(prefix, '')
    # convert string to datetime
    dirDate = datetime.datetime.strptime(dirStr, "%Y-%m-%d-%H:%M")
    rightNow = datetime.datetime.now()   # get datetime now
    diff = rightNow - dirDate  # get time difference between dates
    days, seconds = diff.days, diff.seconds
    dirAgeHours = days * 24 + seconds // 3600  # convert to hours
    if dirAgeHours > hrsMax:   # See if hours are exceeded
        makeNewDir = True
        logging.info('MaxHrs %i Exceeds %i for %s',
                     dirAgeHours, hrsMax, directory)
    else:
        makeNewDir = False
    return makeNewDir


def subDirChecks(maxHours, maxFiles, directory, prefix):
    """ Check if motion SubDir needs to be created """
    if maxHours < 1 and maxFiles < 1:  # No Checks required
        # logging.info('No sub-folders Required in %s', directory)
        subDirPath = directory
    else:
        subDirPath = subDirLatest(directory)
        if subDirPath == directory:   # No subDir Found
            logging.info('No sub folders Found in %s', directory)
            subDirPath = subDirCreate(directory, prefix)
        elif (maxHours > 0 and maxFiles < 1): # Check MaxHours Folder Age Only
            if subDirCheckMaxHrs(subDirPath, maxHours, prefix):
                subDirPath = subDirCreate(directory, prefix)
        elif (maxHours < 1 and maxFiles > 0):   # Check Max Files Only
            if subDirCheckMaxFiles(subDirPath, maxFiles):
                subDirPath = subDirCreate(directory, prefix)
        elif maxHours > 0 and maxFiles > 0:   # Check both Max Files and Age
            if subDirCheckMaxHrs(subDirPath, maxHours, prefix):
                if subDirCheckMaxFiles(subDirPath, maxFiles):
                    subDirPath = subDirCreate(directory, prefix)
                else:
                    logging.info('MaxFiles Not Exceeded in %s', subDirPath)
    os.path.abspath(subDirPath)
    return subDirPath


def filesToDelete(mediaDirPath, extension):
    """ Return a list of files to be deleted """
    return sorted(
        (os.path.join(dirname, filename)
         for dirname, dirnames, filenames in os.walk(mediaDirPath)
         for filename in filenames
         if filename.endswith(extension)),
        key=lambda fn: os.stat(fn).st_mtime, reverse=True)


def saveRecent(recentMax, recentDir, filename, prefix):
    """
    Create a symlink file in recent folder or file if non unix system
    or symlink creation fails.
    Delete Oldest symlink file if recentMax exceeded.
    """
    src = os.path.abspath(filename)  # Original Source File Path
    # Destination Recent Directory Path
    dest = os.path.abspath(os.path.join(recentDir,
                                        os.path.basename(filename)))
    deleteOldFiles(recentMax, os.path.abspath(recentDir), prefix)
    try:    # Create symlink in recent folder
        logging.info('   symlink %s', dest)
        os.symlink(src, dest)  # Create a symlink to actual file
    # Symlink can fail on non unix systems so copy file to Recent Dir instead
    except OSError as err:
        logging.error('symlink Failed: %s', err)
        try:  # Copy image file to recent folder (if no support for symlinks)
            shutil.copy(filename, recentDir)
        except OSError as err:
            logging.error('Copy from %s to %s - %s', filename, recentDir, err)


def freeSpaceUpTo(freeMB, mediaDir, extension):
    """
    Walks mediaDir and deletes oldest files
    until spaceFreeMB is achieved Use with Caution
    """
    mediaDirPath = os.path.abspath(mediaDir)
    if os.path.isdir(mediaDirPath):
        MB2Bytes = 1048576  # Conversion from MB to Bytes
        targetFreeBytes = freeMB * MB2Bytes
        fileList = filesToDelete(mediaDir, extension)
        totFiles = len(fileList)
        delcnt = 0
        logging.info('Session Started')
        while fileList:
            statv = os.statvfs(mediaDirPath)
            availFreeBytes = statv.f_bfree*statv.f_bsize
            if availFreeBytes >= targetFreeBytes:
                break
            filePath = fileList.pop()
            try:
                os.remove(filePath)
            except OSError as err:
                logging.error('Del Failed %s', filePath)
                logging.error('Error: %s', err)
            else:
                delcnt += 1
                logging.info('Del %s', filePath)
                logging.info('Target=%i MB  Avail=%i MB  Deleted %i of %i Files ',
                             targetFreeBytes / MB2Bytes,
                             availFreeBytes / MB2Bytes,
                             delcnt, totFiles)
                # Avoid deleting more than 1/4 of files at one time
                if delcnt > totFiles / 4:
                    logging.warning('Max Deletions Reached %i of %i', delcnt, totFiles)
                    logging.warning('Deletions Restricted to 1/4 of total files per session.')
                    break
        logging.info('Session Ended')
    else:
        logging.error('Directory Not Found - %s', mediaDirPath)


def freeDiskSpaceCheck(lastSpaceCheck, config):
    """ Free disk space by deleting some older files """
    if config.spaceTimerHrs > 0:   # Check if disk free space timer hours is enabled
        # See if it is time to do disk clean-up check
        if (datetime.datetime.now() - lastSpaceCheck).total_seconds() > config.spaceTimerHrs * 3600:
            lastSpaceCheck = datetime.datetime.now()
            # Set freeSpaceMB to reasonable value if too low
            if config.spaceFreeMB < 100:
                diskFreeMB = 100
            else:
                diskFreeMB = config.spaceFreeMB
            logging.info('spaceTimerHrs=%i  diskFreeMB=%i  spaceMediaDir=%s spaceFileExt=%s',
                         config.spaceTimerHrs, diskFreeMB, config.spaceMediaDir, config.spaceFileExt)
            freeSpaceUpTo(diskFreeMB, config.spaceMediaDir, config.spaceFileExt)
    return lastSpaceCheck
