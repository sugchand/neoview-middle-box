#! /usr/bin/python3
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import threading
from src.nvcamera.thread_manager import thread_manager
from src.nv_logger import nv_logger
try:
    from termcolor import colored
except ImportError:
    raise ImportError('Install colored by \"sudo pip3 install termcolor\"')

NV_MIDBOX_CLI_FNS = {
                "ADD-CAMERA" : "nv_midbox_add_camera",
                "DELETE-CAMERA" : "nv_midbox_del_camera",
                "START-CAMERA-STREAM" : "nv_midbox_start_stream",
                "STOP-CAMERA-STREAM" : "nv_midbox_stop_stream",
                "LIST-ALL-CAMERAS" : "nv_midbox_list_cameras",
                "QUIT-MIDBOX" : "nv_midbox_stop"
                    }

def print_color_string(s, color='white'):
    print("%s" %(colored(s, color, attrs = ['bold'])))

class nv_middlebox_cli(threading.Thread):

    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        threading.Thread.__init__(self, None, None, "nv_midbox_cli")
        self.cam_thread_mgr = thread_manager()

    def run(self):
        self.nv_middlebox_cli_main()

    def stop(self):
        self.cam_thread_mgr.stop_all_camera_threads()
        super(nv_middlebox_cli, self).stop()

    def do_execute_nv_midbox_cli(self):
        for i, (key, value) in enumerate(NV_MIDBOX_CLI_FNS.items()):
            print_color_string(str(i) + " : " + key, color="cyan")
        choice = (input("Enter your choice[0-%d] : " %i))

        if choice == "":
            print_color_string("Invalid Choice, Exiting...", color = "red")
            return 0

        choice = int(choice)
        if choice < 0 or choice > i:
            print_color_string("Invalid Choice, Exiting...", color = "red")
            return 0 

        quit_key = list(NV_MIDBOX_CLI_FNS.keys()).index('QUIT-MIDBOX')
        if choice is quit_key:
            self.cam_thread_mgr.stop()
            return -1

        fn = list(NV_MIDBOX_CLI_FNS.values())[choice]
        fn = "self." + fn
        eval(fn)()
        return 0

    def nv_middlebox_cli_main(self):
        while(1):
            try:
                res = self.do_execute_nv_midbox_cli()
                if res == -1:
                    break
            except KeyboardInterrupt:
                self.cam_thread_mgr.stop_all_camera_threads()
                break

    def nv_midbox_add_camera(self):
        cam_name = "None"
        self.nv_log_handler.debug("Added a new camera %s to DB" % cam_name)
        pass

    def nv_midbox_del_camera(self):
        cam_name = "None"
        self.nv_log_handler.debug("Deleted the camera %s from the DB" % cam_name)
        pass

    def nv_midbox_start_stream(self):
        cam_name = "None"
        self.nv_log_handler.debug("staring the stream recording on camera %s"
                                  % cam_name)
        pass

    def nv_midbox_stop_stream(self):
        cam_name = None
        self.nv_log_handler.debug("Stop streaming on camera %s" %cam_name)
        pass

    def nv_midbox_list_cameras(self):
        self.nv_log_handler.debug("Listing all the cameras in the DB")
        pass

    def nv_midbox_stop(self):
        self.nv_log_handler.debug("Quit the middlebox")
