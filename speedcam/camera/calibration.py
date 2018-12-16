import cv2
import os
import click
import inquirer
import importlib.util
import subprocess
from speedcam.camera import utils
from config.config import Config
from speedcam.camera.utils import connect_to_stream
from config.app_constants import VERSION, APP_NAME


def calibrate():
    config = Config()

    camera_type = __get_camera_type()
    if camera_type == "webcam":
        config.WEBCAM = True
    elif camera_type == "picam":
        config.WEBCAM = False
    else:
        return

    cal_obj_px, cal_obj_mm = __get_img_scale_values(config)

    if cal_obj_px is None or cal_obj_mm is None:
        return

    speed_units = __get_speed_units()

    __write_calibration(camera_type, cal_obj_px, cal_obj_mm, speed_units)

    click.echo("""
    You should test the measured speed against real speed
    You should adjust the value of cal_obj_mm in the config.ini
    if recorded speed is to low increase and if to high decrease
    =====================Notes on Performance=======================
    This application is calculating speed based on distance traveled
    between frames, this means that it is sensitive to the real
    distance of a pixel this will show up as a fixed error.

    The load on your system will also affect accuracy. A camera at 10fps
    will capture an image ever 100ms, even at 50kph the distance travelled
    can vary considerably at such a low fps, start with the lowest possible
    resolution for the highest fps""")


def create_calibration_img(config, path, cal_image):
    # If there is bad contrast with background you can change the hash
    # colors to give more contrast.  You need to change values below
    # per values cvRed, cvBlue, cvWhite, cvBlack, cvGreen

    hash_color = utils.cvRed
    motion_win_color = utils.cvBlue

    for i in range(10, config.get_image_width() - 9, 10):
        cv2.line(cal_image, (i, config.y_upper - 5), (i, config.y_upper + 30), hash_color, 1)
    # This is motion window
    utils.speed_image_add_lines(config, cal_image, motion_win_color)

    click.echo(os.path.join(path, 'calibrate.jpg'))
    cv2.imwrite(os.path.join(path, 'calibrate.jpg'), cal_image)


def __get_camera_type():
    questions = [
        inquirer.List('camera',
                      message="What type of camera are you using?",
                      choices=['Pi Camera', 'Webcam'],
                      ),
    ]

    answers = inquirer.prompt(questions)

    if answers['camera'] == 'Webcam':
        return "webcam"
    elif answers['camera'] == 'Pi Camera':
        picam_spec = importlib.util.find_spec("picamera")
        if not picam_spec:
            click.echo("You specified Pi Camera but the picamera module could not be found")
            if click.confirm("Should we attempt to install the picamera module?"):
                click.echo('installing stuff.... honest')
            else:
                click.echo('cannot continue, exiting camera calibration')
                return ""
        cam_result = subprocess.check_output("vcgencmd get_camera", shell=True)
        cam_result = cam_result.decode("utf-8")
        cam_result = cam_result.replace("\n", "")
        if (cam_result.find("0")) >= 0:   # -1 is zero not found. Cam OK
            click.echo("Pi Camera Module Not Found %s" % cam_result)
            click.echo("if supported=0 Enable Camera per command sudo raspi-config")
            click.echo("if detected=0 Check Pi Camera Module is Installed Correctly")
            click.echo("%s %s Exiting Due to Error" % APP_NAME, VERSION)
            click.echo('cannot continue, exiting camera calibration')
            return ""
        else:
            click.echo("Pi Camera Module is Enabled and Connected %s" % cam_result)
            return "picam"


def __get_img_scale_values(config):
    if click.confirm('Do you want a new calibration image?', default=True):
        value = click.prompt('Calibration image folder/dir', default=os.getcwd())
        if not os.path.exists(value):
            click.echo('The folder/dir (%s) does not exist, make sure the folder exists then try again' % value)
            return None, None
        vs = connect_to_stream(config)
        create_calibration_img(config, value, vs.read())
    click.echo("    Open the calibration image, it will contain a red grid")
    click.echo("    for best results you need to find an object in the image that")
    click.echo("    will be the same size as vehicles in the image.")
    click.echo("    Using the vertical red marks (10 points apart), measure the size of your object")
    obj_px_length = click.prompt("What is the length of the object (e.g 2 red dashes is 20 points)?")
    click.echo("To calculate speed correctly we need some idea of the real size of the object in your image")
    real_length = click.prompt("What is the real length of the object (this needs to be in millimeters)?")
    click.echo("Your values are img %s, real world %s" % (obj_px_length, real_length))
    return obj_px_length, real_length


def __get_speed_units():
    questions = [
        inquirer.List('speed',
                      message="What units are you using?",
                      choices=['kph', 'mph'],
                      ),
    ]

    answers = inquirer.prompt(questions)

    return answers['speed']


def __write_calibration(camera_type, cal_obj_px, cal_obj_mm, speed_units):
    value = click.prompt('Config file folder/dir (existing config.ini will be updated', default=os.getcwd())
    if not os.path.exists(value):
        click.echo('The folder/dir (%s) does not exist, make sure the folder exists then try again' % value)
        return

    # Don't like having this stuff here it should be encapsulated in teh config class
    config = Config.create_from(os.path.join(value, 'config.ini'))
    if not config.has_section('GENERAL'):
        config.add_section('GENERAL')
    config.set('GENERAL', 'calibrate', str(False))
    config.set('GENERAL', 'cal_obj_px', str(cal_obj_px))
    config.set('GENERAL', 'cal_obj_mm', str(cal_obj_mm))
    if not config.has_section('TRACKING'):
        config.add_section('TRACKING')
    config.set('TRACKING', 'SPEED_MPH', str(speed_units == 'mph'))
    if not config.has_section('CAMERA'):
        config.add_section('CAMERA')
    config.set('CAMERA', 'WEBCAM', str(camera_type == 'webcam'))

    with open(os.path.join(value, 'config.ini'), 'w+') as file:
        config.write(file)
