#! /usr/bin/python3
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import threading
import uuid
import ipaddress
from src.nvcamera.thread_manager import thread_manager
from src.nv_logger import nv_logger
from src.nvdb.nvdb_manager import db_mgr_obj, nv_midbox_system
from src.nvdb.nvdb_manager import nv_camera
from src.nvdb.nvdb_manager import nv_webserver_system
from src.nvrelay.relay_handler import relay_main

try:
    from termcolor import colored
except ImportError:
    raise ImportError('Install colored by \"sudo pip3 install termcolor\"')

NV_MIDBOX_CLI_FNS = {
                "ADD-CAMERA" : "nv_midbox_add_camera",
                "DELETE-CAMERA" : "nv_midbox_del_camera",
                "START-CAMERA-STREAM" : "nv_midbox_start_stream",
                "STOP-CAMERA-STREAM" : "nv_midbox_stop_stream_cli",
                "LIST-ALL-CAMERAS" : "nv_midbox_list_cameras",
                "LIST-SYSTEM" : "list_midbox_system",
                "ADD-WEBSERVER" : "add_nv_webserver",
                "QUIT-MIDBOX" : "nv_midbox_stop"
                    }

def print_color_string(s, color='white'):
    print("%s" %(colored(s, color, attrs = ['bold'])))

class nv_middlebox_conf(threading.Thread):

    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        threading.Thread.__init__(self, None, None, "nv_midbox_cli")
        self.cam_thread_mgr = thread_manager()
        self.nv_relay_mgr =  None # Thread to copy files to dst webserver

    def run(self):
        try:
            self.nv_relay_mgr = relay_main()
            self.nv_relay_mgr.process_relay()
            self.nv_middlebox_cli_main()
        except:
            self.nv_log_handler.error("Unknown exception while starting"
                                      " the middlebox")
            self.exit_all_threads()

    def stop(self):
        self.exit_all_threads()
        super(nv_middlebox_conf, self).stop()

    def exit_all_threads(self):
        '''
        Function to stop all the threads that are started by the midbox cli.
        relay manager and all camera threads are stopped.
        '''
        self.nv_relay_mgr.relay_stop()
        self.nv_relay_mgr.relay_join()
        self.cam_thread_mgr.stop_all_camera_threads()
        self.cam_thread_mgr.join_all_camera_threads()

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
            return -1

        fn = list(NV_MIDBOX_CLI_FNS.values())[choice]
        fn = "self." + fn
        eval(fn)()
        return 0

    def nv_middlebox_cli_main(self):
        print_color_string("** NOTE :: THE MIDDLE BOX MACHINE SETTING MUST BE SET "
                           "BEFORE RUNNING ANY COMMAND BELOW **", color = "red")
        while(1):
            try:
                res = self.do_execute_nv_midbox_cli()
                if res == -1:
                    self.nv_midbox_stop()
                    break
            except KeyboardInterrupt:
                self.exit_all_threads()
                break

    def add_nv_webserver(self):
        srv_name = input("Enter webserver Name: ")
        if not srv_name:
            srv_name = 'localhost'
        srv_path = input("Enter webserver video path(default = /tmp): ")
        if not srv_path:
            srv_path = '/tmp/'
        wbsrv_entry = nv_webserver_system(name = srv_name,
                                    server_id = (uuid.uuid4().int>>64)
                                                & 0xFFFFFFFF,
                                    video_path = srv_path)
        db_mgr_obj.init_webserver_params(wbsrv_entry)

    def nv_midbox_add_camera(self):
        nv_midbox_db_entry = db_mgr_obj.get_own_system_record()
        if nv_midbox_db_entry is None:
            self.nv_log_handler.error("System table is not available, "
                                      "Cannot add a Camera")
            return
        # TODO :: Validate user inputs for right input data,
        #cam_name = (input("Enter Camera Name: "))
        #cam_ip = (input("Enter Camera IP Address: "))
        #cam_mac = (input("Enter Camera MAC Address: "))
        #cam_listen_port = (input("Enter Camera Listen port: "))
        #cam_uname = (input("Enter Camera User name: "))
        #cam_pwd = (input("Enter Camera password: "))
        ### TODO ::: STATIV values , remove it #####
        cam_name = 'camera-1'
        cam_ip = int(ipaddress.IPv4Address('192.168.192.32'))
        cam_mac = "00:00:00:00:00:01"
        cam_listen_port = 554
        time_len = 60
        cam_uname = 'admin'
        cam_pwd = 'sugu&deepu'
        #########################

        filter_arg = {'name' : cam_name}
        cam_cnt = db_mgr_obj.get_tbl_records_filterby_cnt(nv_camera, filter_arg)
        if cam_cnt != 0:
            self.nv_log_handler.error("%d camera records are already present"
                                      " Cannot add camera %s", cam_cnt, cam_name)
            print_color_string("Cannot add existing camera %s" % cam_name, 
                               color = "blue")
            return
        cam_entry = nv_camera(cam_id = (uuid.uuid4().int>>64) & 0xFFFFFFFF,
                               name = cam_name,
                               ip_addr = int(ipaddress.IPv4Address(cam_ip)),
                               mac_addr = cam_mac,
                               listen_port = cam_listen_port,
                               stream_file_time_sec = time_len,
                               username = cam_uname,
                               password = cam_pwd,
                               nv_midbox = nv_midbox_db_entry
                               )
        db_mgr_obj.add_record(cam_entry)
        db_mgr_obj.db_commit()
        self.nv_log_handler.debug("Added a new camera %s to DB" % cam_name)

    def nv_midbox_del_camera(self):
        cam_name = "None"
        self.nv_log_handler.debug("Deleted the camera %s from the DB" % cam_name)
        pass

    def nv_midbox_start_stream(self):
        # TODO :: Validate the camera name
        cam_name = (input("Enter Camera Name: "))
        filter_arg = {'name' : cam_name}
        cam_cnt = db_mgr_obj.get_tbl_records_filterby_cnt(nv_camera, filter_arg)
        if cam_cnt == 0:
            self.nv_log_handler.error("No record found with given name %s"
                                      % cam_name)
            return
        if cam_cnt > 1:
            self.nv_log_handler.error("Exiting, More than one record found"
                                      " with same name %s" % cam_name)
            return
        cam_record = db_mgr_obj.get_tbl_records_filterby(nv_camera, filter_arg)[0]
        self.cam_thread_mgr.start_camera_thread(cam_record)
        self.nv_log_handler.debug("staring the stream recording on camera %s"
                                  % cam_name)

    def nv_midbox_stop_stream_cli(self):
        cam_name = input("Enter camera Name: ")
        if cam_name is None:
            return
        self.nv_midbox_stop_stream(cam_name)

    def nv_midbox_stop_stream(self, cam_name):
        filter_arg = {'name' : cam_name}
        cam_record = db_mgr_obj.get_tbl_records_filterby(nv_camera, filter_arg)[0]
        if cam_record is None:
            self.nv_log_handler.error("No camera record found for %s", cam_name)
            return
        self.cam_thread_mgr.stop_camera_thread(cam_record.cam_id, None)
        self.nv_log_handler.debug("Stop streaming on camera %s" %cam_name)

    def list_midbox_system(self):
        if not db_mgr_obj.get_tbl_record_cnt(nv_midbox_system):
            print_color_string("No record found in system table", color='red')
            self.nv_log_handler.debug("Empty system table in the DB")
            return
        sys_record = db_mgr_obj.get_tbl_records(nv_midbox_system)
        print_color_string(sys_record, color = "green")
        self.nv_log_handler.debug("Listing system details the DB")

    def nv_midbox_list_cameras(self):
        if not db_mgr_obj.get_tbl_record_cnt(nv_camera):
            print_color_string("No camera record found in the system", color='red')
            self.nv_log_handler.debug("Camera table empty in the system")
            return
        cam_records = db_mgr_obj.get_tbl_records(nv_camera)
        print_color_string(cam_records, color = "green")
        self.nv_log_handler.debug("Listing all the cameras in the DB")

    def nv_midbox_stop(self):
        self.nv_log_handler.info("Quit the middlebox, "
                                  "Waiting for all threads to coalesce...")
        self.exit_all_threads()
