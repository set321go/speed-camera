#!/usr/bin/python
"""
 SimpleHTTPServer python program to allow selection of images from right panel and display in an iframe left panel
 Use for local network use only since this is not guaranteed to be a secure web server.
 based on original code by zeekay and modified by Claude Pageau Nov-2015 for use with pi-timolo.py on a Raspberry Pi
 from http://stackoverflow.com/questions/8044873/python-how-to-override-simplehttpserver-to-show-timestamp-in-directory-listing

 1 - Use nano editor to change webserver.py web_server_root and other variables to suit at bottom of config.py
     nano config.py         # Webserver settings are near the end of the file
     ctrl-x y to save changes

 2 - On Terminal session execute command below.  This will display file access information
     ./webserver.py    # ctrl-c to stop web server.  Note if you close terminal session webserver.py will stop.

 3 - To Run this script as a background daemon execute the command below.
     Once running you can close the terminal session and webserver will continue to run.
     ./webserver.sh start
     To check status of webserver type command below with no parameter
     ./webserver.sh

 4 - On a LAN computer web browser url bar, input this RPI ip address and port number per below
     example    http://192.168.1.110:8080

 Variable Settings are imported from config.py
"""
import os
import socket
import socketserver
import sys
import time
import logging
from http.server import SimpleHTTPRequestHandler
from pystache import renderer
import io
from server.__version__ import __version__
from config import Config
from speedcam.startup import startup_helpers


def map_file(fullname):
    if os.path.isdir(fullname):
        displayname = os.path.basename(fullname) + "/"
    else:
        displayname = os.path.basename(fullname)

    return {
        'is_img': not os.path.isdir(fullname),
        'modified': time.strftime('%H:%M:%S %d-%b-%Y', time.localtime(os.path.getmtime(fullname))) if not os.path.isdir(fullname) else "",
        'path': os.path.basename(fullname),
        'name': displayname
    }


def DirectoryHandlerCompanion(config):
    class DirectoryHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.config = config

            if config.web_list_by_datetime:
                dir_sort = 'Sort DateTime'
            else:
                dir_sort = 'Sort Filename'

            if config.web_list_sort_descending:
                dir_order = 'Desc'
            else:
                dir_order = 'Asc'

            self.list_title = "%s %s" % (dir_sort, dir_order)
            # non standard order here because handler is calling http methods inside the init method up the tree somewhere
            super(DirectoryHandler, self).__init__(*args, directory=config.web_server_root, **kwargs)

        def log_message(self, msg_format, *args):
            logging.info("%s - - %s" %
                         (self.client_address[0],
                          msg_format % args))

        def list_directory(self, path):
            try:
                file_list = os.listdir(path)
                all_entries = len(file_list)
            except os.error:
                self.send_error(404, "No permission to list directory")
                return None

            if self.config.web_list_by_datetime:
                # Sort by most recent modified date/time first
                file_list.sort(key=lambda x: os.stat(os.path.join(path, x)).st_mtime, reverse=self.config.web_list_sort_descending)
            else:
                # Sort by File Name
                file_list.sort(key=lambda a: a.lower(), reverse=self.config.web_list_sort_descending)

            file_found = False
            cnt = 0
            for entry in file_list:  # See if there is a file for initializing iframe
                fullname = os.path.join(path, entry)
                if os.path.islink(fullname) or os.path.isfile(fullname):
                    file_found = True
                    break
                cnt += 1

            file_list = list(map(lambda filename: os.path.join(path, filename), file_list))
            file_list = list(map(map_file, file_list))
            params = {'refresh_enabled': self.config.web_page_refresh_on,
                      'refresh_rate': self.config.web_page_refresh_sec,
                      'title': self.config.web_page_title + " " + self.path,
                      'iframe_width': self.config.web_iframe_width_usage,
                      'iframe_height': self.config.web_image_height,
                      'iframe_src': file_list[cnt]['name'] if file_found else "about:blank",
                      'iframe_alt': self.config.web_page_title,
                      'list_height': self.config.web_list_height,
                      'list_title': self.list_title,
                      'is_root': self.path is "/",
                      'files': file_list,
                      'web_root': self.config.web_server_root,
                      'web_title': self.config.web_page_title,
                      'max_list': self.config.web_max_list_entries > 1,
                      'all_entries': all_entries,
                      'path': self.path}

            template_renderer = renderer.Renderer()
            processed_page = template_renderer.render_path(os.path.join(self.config.base_dir, 'server', 'index.mustache'), params)
            enc = sys.getfilesystemencoding()
            encoded = processed_page.encode(enc, 'surrogateescape')
            out = io.BytesIO()
            out.write(encoded)
            length = out.tell()
            out.seek(0)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=%s" % enc)
            self.send_header("Content-Length", str(length))
            self.end_headers()
            return out
    return DirectoryHandler


def main():
    startup_helpers.init_boot_logger()
    app_name = os.path.basename(__file__)    # Name of this program

    config = Config()
    startup_helpers.init_logger(config)

    try:
        myip = ([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1],
                             [[(s.connect(('8.8.8.8', 53)),
                                s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET,
                                                                                       socket.SOCK_DGRAM)]][0][1]]) if l][0][0])
    except socket.gaierror:
        logging.warning("Can't Find a Network IP Address on this Device")
        logging.warning("Configure Network and Try Again")
        myip = None

    socketserver.TCPServer.allow_reuse_address = True
    HandlerClass = DirectoryHandlerCompanion(config)
    httpd = socketserver.TCPServer(("", config.web_server_port), HandlerClass)

    print("----------------------------------------------------------------")
    print("ver %s %s written by Claude Pageau" % (app_name, __version__))
    print("---------------------------- Settings --------------------------")
    print("Server  - web_page_title   = %s" % config.web_page_title)
    print("          web_server_root  = %s/%s" % (config.base_dir, config.web_server_root))
    print("          web_server_port  = %i " % config.web_server_port)
    print("Content - web_image_height = %s px (height of content)" % config.web_image_height)
    print("          web_iframe_width = %s  web_iframe_height = %s" % (config.web_iframe_width, config.web_iframe_height))
    print("          web_iframe_width_usage = %s (of avail screen)" % config.web_iframe_width_usage)
    print("          web_page_refresh_sec = %s  (default=180 sec)" % config.web_page_refresh_sec)
    print("          web_page_blank = %s ( True=blank left pane until item selected)" % config.web_page_blank)
    print("Listing - web_max_list_entries = %s ( 0=all )" % config.web_max_list_entries)
    print("          web_list_by_datetime = %s  sort_decending = %s" % (config.web_list_by_datetime, config.web_list_sort_descending))
    print("----------------------------------------------------------------")
    print("From a computer on the same LAN. Use a Web Browser to access this server at")
    print("Type the URL below into the browser url bar then hit enter key.")
    print("")
    print("                 http://%s:%i" % (myip, config.web_server_port))
    print("")
    print("IMPORTANT: If You Get - socket.error: [Errno 98] Address already in use")
    print("           Wait a minute or so for webserver to timeout and Retry.")
    print("              ctrl-c to exit this webserver script")
    print("----------------------------------------------------------------")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("")
        print("User Pressed ctrl-c")
        print("%s %s" % (app_name, __version__))
        print("Exiting Bye ...")
        httpd.shutdown()
        httpd.socket.close()
    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))


if __name__ == '__main__':
    main()
