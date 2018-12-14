from speedcam.camera.utils import *


def draw_geom_overlay(config, img, x, y, w, h):
    # show centre of motion if required
    if config.SHOW_CIRCLE:
        cv2.circle(img,
                   (x + config.x_left, y + config.y_upper),
                   config.CIRCLE_SIZE,
                   cvGreen, config.LINE_THICKNESS)
    else:
        cv2.rectangle(img,
                      (int(x + config.x_left),
                       int(y + config.y_upper)),
                      (int(x + config.x_left + w),
                       int(y + config.y_upper + h)),
                      cvGreen, config.LINE_THICKNESS)
