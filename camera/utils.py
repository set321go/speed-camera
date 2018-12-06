import cv2

# Color data for OpenCV lines and text
cvWhite = (255, 255, 255)
cvBlack = (0, 0, 0)
cvBlue = (255, 0, 0)
cvGreen = (0, 255, 0)
cvRed = (0, 0, 255)


def speed_image_add_lines(config, image, color):
    cv2.line(image, (config.x_left, config.y_upper),
             (config.x_right, config.y_upper), color, 1)
    cv2.line(image, (config.x_left, config.y_lower),
             (config.x_right, config.y_lower), color, 1)
    cv2.line(image, (config.x_left, config.y_upper),
             (config.x_left, config.y_lower), color, 1)
    cv2.line(image, (config.x_right, config.y_upper),
             (config.x_right, config.y_lower), color, 1)
    return image
