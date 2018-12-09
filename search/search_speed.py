#!/usr/bin/env python
"""
speed-search.py written by Claude Pageau pageauc@gmail.com
Raspberry (Pi) - python opencv2 find images matching search image using cv2 template matching
GitHub Repo here https://github.com/pageauc/rpi-speed-camera/tree/master/

This is program works in conjunction with speed-cam.py data output images and csv file.
It needs a speed camera csv file and related images.  To initiate a search make sure
there is sufficient images (suggest > 100).  Find a single speed image that you want
to find matches for.  Copy this image into the search folder (default media/search)
Start search-speed.py

    cd ~/rpi-speed-camera
    ./search-speed.py

If config.py variable copy_results_on = True then copies of the matching image files
will be put in a subfolder named the same as the search image filename minus the extension.
The search file will be copied to the subfolder as well.
If copy_results = False then no copying will take place.  This can be used for testing
various config.py search_value settings.  higher will get more results lower more results
This setting is used to determine how close the original image matches other speed images.
Note Only the cropped rectangle area is used for this search.

This is still under development.  If you have suggestions or issues post a GitHub issue
to the Repo.  The search will generate false positives but can reduce the amount of
searching if you are looking for a specific image match. I have not implemented logging
results at this time.  Also the code still needs more work but thought it was
good enough to release.

Claude  ...

"""
import os
import time
import cv2
import csv
import glob
import shutil
import sys
from config import Config
from search import __version__


# -----------------------------------------------------------------------------------------------
def print_at(x, y, text):
    sys.stdout.write("\x1b7\x1b[%d;%df%s\x1b8" % (x, y, text))
    sys.stdout.flush()


# -----------------------------------------------------------------------------------------------
def check_image_match(config, full_image, small_image):
    # Look for small_image in full_image and return best and worst results
    # Try other MATCH_METHOD settings per config.py comments
    # For More Info See http://docs.opencv.org/3.1.0/d4/dc6/tutorial_py_template_matching.html
    result = cv2.matchTemplate(full_image, small_image, config.search_match_method)
    # Process result to return probabilities and Location of best and worst image match
    minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)  # find search rect match in new image
    return maxVal


# -----------------------------------------------------------------------------------------------
def get_search_rect(config, search_filepath):
    if os.path.isfile(search_filepath):   # check if file exists
        print("Loading Target Search Image %s" % search_filepath)
        image1 = cv2.imread(search_filepath)  # read color image in BGR format
        crop_x_L = int((config.x_left + 10) * config.image_bigger)
        crop_x_R = int((config.x_right - 10) * config.image_bigger)
        crop_y_U = int((config.y_upper + 10) * config.image_bigger)
        crop_y_D = int((config.y_lower - 10) * config.image_bigger)
        try:
            search_rect = image1[crop_y_U:crop_y_D, crop_x_L:crop_x_R]
        except:
            print("ERROR: Problem Extracting search_rect from %s" % search_filepath)
            return None
    else:
        print("ERROR: File Not Found %s" % search_filepath)
        return None
    print("Successfully Created Target Search Rectangle from %s" % search_filepath)
    return search_rect


# -----------------------------------------------------------------------------------------------
def search_for_match(config, config_file_path, search_image, search_rect):
    cnt = 0             # Initialize csv file row counter
    work_count = 0      # initialize number of images processed
    result_count = 0    # initialize search result counter
    result_list = []    # initialize blank result list
    crop_x_L = (config.x_left + 10) * config.image_bigger
    crop_x_R = (config.x_right - 10) * config.image_bigger
    crop_y_U = (config.y_upper + 10) * config.image_bigger
    crop_y_D = (config.y_lower - 10) * config.image_bigger
    # Construct a results folder name based on original search filename minus extension
    results_dir_path = os.path.join(config.search_dest_path,
                       os.path.splitext(os.path.basename(search_image))[0])
    print_at(2,1,"Target  : %s with search_match_value>%.4f" % ( search_image, config.search_match_value))
    if config.search_copy_on:  # Create a search results dest folder if required otherwise results is view only
        if not os.path.exists(results_dir_path):
            try:
                os.makedirs(results_dir_path)
            except OSError as err:
                print('ERROR: Cannot Create Directory %s - %s, using default location.' %
                                                 ( results_dir_path, err))
            else:
                print('Created Search Results Dir %s' % (results_dir_path))

    # Construct path of search file in original images folder
    search_image_path = os.path.join(config.search_source_images_path, os.path.basename(search_image))
    work_start = time.time()      # Start a timer for processing duration
    try:
        if config.search_using_csv:
            f = open(config.search_csv_path, 'rt')  # Open csv file for reading
            reader = csv.reader(f)    # Read csv file into reader list
            image_data = list(reader)
        else:
            image_data = glob.glob(os.path.join(config.search_source_images_path, '/*jpg'))
        search_images_total = len(image_data)

        for row in image_data:  # row is a list of one row of data
            work_count += 1  # increment counter for number of images processed
            if config.search_using_csv:
                current_image_path = row[5]  # Get target image filename
            else:
                current_image_path = image_data[cnt]
            cnt += 1  # Increment Row Counter
            if os.path.isfile(current_image_path):   # check if file exists
                target_image = cv2.imread(current_image_path)  # read color image in BGR format
                target_rect = target_image[crop_y_U:crop_y_D, crop_x_L:crop_x_R]
                search_result_value = check_image_match(config, target_rect, search_rect)  # get search result

                # Check if result is OK and not itself
                if search_result_value >= config.search_match_value and not (current_image_path == search_image_path):
                    result_count += 1   # increment valid search result counter
                    result_list.append([search_result_value, current_image_path])  # Update search result_list
                    print_at(4, 1, "Matched : %i Last: %i/%i  value: %.4f/%.4f  MATCH=%s       " %
                             (result_count, cnt, search_images_total, search_result_value, config.search_match_value, current_image_path))
                    if config.search_copy_on:
                        # Put a copy of search match file into results subfolder (named with search file name without ext)
                        try:
                            shutil.copy(current_image_path, results_dir_path)  # put a copy of file in results folder
                        except OSError as err:
                            print('ERROR: Copy Failed from %s to %s - %s' % (current_image_path, results_dir_path, err))
                    if config.gui_window_on:
                        cv2.imshow("Searching", search_rect)
                        cv2.imshow("Target", target_rect)
                        cv2.waitKey(3000)  # pause for 3 seconds if match found
                else:
                    print_at(3, 1, "Progress: %i/%i  value: %.4f/%.4f  SKIP=%s    " %
                             (cnt, search_images_total, search_result_value, config.search_match_value, current_image_path))
                    if config.gui_window_on:
                        cv2.imshow("Searching", search_rect)
                        cv2.imshow("Target", target_rect)
                        cv2.waitKey(20)  # Not a match so display for a short time
        try:
            if config.search_copy_on:
                # At end of search Copy search file to search results folder
                shutil.copy(search_image, results_dir_path)
                if os.path.exists(search_image):
                    os.remove(search_image)
        except OSError as err:
            print('ERROR: Copy Failed from %s to %s - %s' % (search_image, results_dir_path, err))
    finally:
        if config.search_using_csv:
            f.close()   # close csv file
        work_end = time.time()  # stop work timer
        print("------------------------------------------------")
        print("Search Results Matching %s" % search_image)
        print("with search_match_value >= %.4f" % config.search_match_value)
        print("------------------------------------------------")
        if result_list:  # Check if results_list has search file entries
            result_list.sort(reverse=True)
            for filename in result_list:
                print(filename)
            print("------------------------------------------------")
            if config.search_copy_on:
                print("Search Match Files Copied to Folder: %s " % results_dir_path)
            else:
                print("search_copy_on=%s  No Search Match Files Copied to Folder: %s" % (config.search_copy_on, results_dir_path))
        else:
            print("------------- Instructions ---------------------")
            print("")
            print("No Search Matches Found.")
            print("You May Need to Reduce %s variable search_match_value = %.4f" % (config_file_path, config.search_match_value))
            print("From %.4f to a lower value." % config.search_match_value)
            print("Then Try Again")
            print("")
        print("Processed %i Images in %i seconds Found %i Matches" %
                       (work_count, work_end - work_start, result_count))
    return result_list

# ------------------- Start Main --------------------------------


def main():
    ver = __version__  # Original issue on 26-Jul-2017 by Claude Pageau

    os.system('clear')
    # Create some system variables
    mypath = os.path.abspath(__file__)       # Find the full path of this python script
    baseDir = mypath[0:mypath.rfind("/")+1]  # get the path location only (excluding script name)
    progName = os.path.basename(__file__)  # Get name of this script with no path

    print("%s %s Loading  Please Wait ....." % (progName, ver))

    configFilePath = baseDir + "search_config.py"
    if not os.path.exists(configFilePath):  # check if config.py file exist if not wget github copy
        print("ERROR - Could Not Find Configuration File %s" % (configFilePath))
        import urllib2
        config_url = "https://raw.github.com/pageauc/rpi-speed-camera/master/search_config.py"
        print("   Attempting to Download config File from %s" % ( config_url ))
        try:
            wgetfile = urllib2.urlopen(config_url)
        except:
            print("ERROR: Download of config Failed")
            print("   Try Rerunning the speed-install.sh Again.")
            print("   or")
            print("   Perform GitHub curl install per Readme.md")
            print("   and Try Again")
            print("Exiting %s" % progName)
            quit()
        f = open('search_config.py', 'wb')
        f.write(wgetfile.read())
        f.close()

    config = Config()

    blank = "                                                              "

    if not os.path.isdir(config.search_dest_path):
        print("Creating Search Folder %s" % config.search_dest_path)
        os.makedirs(config.search_dest_path)

    search_list = glob.glob(config.search_dest_path + '/*jpg')
    target_total = len(search_list)
    try:
        if search_list:  # Are there any search files found in search_path
            for filePath in search_list:  # process each search_list entry
                os.system('clear')
                for i in range(1, 5):
                    print("")
                    print_at(1, i, blank)
                print_at(1, 1, "%s %s written by Claude Pageau       " % (progName, ver))
                print("------------------------------------------------")
                print("Found %i Target Search Image Files in %s" %
                      (target_total, config.search_dest_path))
                print("------------------------------------------------")
                for files in search_list:
                    current = files
                    if current == filePath:
                        print("%s  Current Search" % current)
                    else:
                        print(files)
                print("------------------------------------------------")
                search_rect = get_search_rect(config, filePath)  # Get search_rect of file
                if search_rect is None:  # Check if search_rect created
                    print("ERROR: Problem Creating Search Rectangle.")
                    print("       Cannot Search Match %s" % filePath)
                else:
                    results = search_for_match(config, configFilePath, filePath, search_rect)  # Look for matches
                # if results:
                #     for rows in results:
                #         print(rows)
        else:
            print("------------- Instructions ---------------------")
            print("")
            print("No Search Files Found in Folder %s" % config.search_dest_path)
            print("To enable a search")
            print("1 Copy one or more Speed Image File(s) to Folder: %s" % config.search_dest_path)
            print("2 Restart this script.")
            print("")
            print("Note: search_config.py variable search_copy_on = %s" % config.search_copy_on)
            print("if True Then a copy of all search match files will be copied")
            print("To a search subfolder named after the search image name minus extension")
            print("Otherwise search results will be displayed with no copying (useful for testing)")
            print("")
        print("------------------------------------------------")
        print("%s %s  written by Claude Pageau" % (progName, ver))
        print("Done ...")
    except KeyboardInterrupt:
        print("")
        print("+++++++++++++++++++++++++++++++++++")
        print("User Pressed Keyboard ctrl-c")
        print("%s %s - Exiting ..." % (progName, ver))
        print("+++++++++++++++++++++++++++++++++++")
        print("")
        quit(0)


if __name__ == '__main__':
    main()
