#! /usr/bin/python3
# -*- coding: utf8 -*-
# The camera handler module for nv-middlebox. 
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from src.nv_logger import nv_logger
from src.nvdb.nvdb_manager import nv_camera
from src.nv_lib.nv_os_lib import nv_os_lib
import time
import ipaddress
from src.settings import NV_MID_BOX_CAM_STREAM_DIR

class cam_handler():
    #Stream count used to specify the current file to stream out.
    curr_stream_cnt = 0
    out_file_prefix = ""
    vlc_instance = None
    player_obj = None
    tot_out_file_cnt = 0
    time_lapse = 0

    '''
    Each camera had a camera handler instance to stream and store the video file
    in the local media-box server 
    '''
    def __init__(self, cam_tbl_entry=None):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.tot_out_file_cnt = cam_tbl_entry.stream_file_cnt
        self.time_lapse = cam_tbl_entry.stream_file_time_sec
        
        self.curr_stream_cnt = 0
        self.cam_dir = str(cam_tbl_entry.cam_id)
        self.username = cam_tbl_entry.username
        self.pwd = cam_tbl_entry.password
        self.cam_ip = str(ipaddress.IPv4Address(cam_tbl_entry.ip_addr))
        self.cam_listen_port = str(cam_tbl_entry.listen_port)
        self.os_context = nv_os_lib()
        self.nv_log_handler.debug("Initialized the camera handler thread.")

    def save_camera_stream_in_multifile(self):
        cam_src_path = ["rtsp://" + self.username + ":" + self.pwd + "@" +\
                        self.cam_ip + ":" + self.cam_listen_port]
        vlc_out_opts = cam_src_path +\
                       ["--no-loop", "--no-repeat", "--play-and-exit",
                        "--live-caching=8", #"--rt-priority",
                       "--stop-time=" +
                        str(self.time_lapse)]
        if self.os_context.is_pgm_installed('cvlc') is None:
            #The cvlc not found.
            self.nv_log_handler.error("cvlc not installed, cannot stream")
            return
        out_file_path = NV_MID_BOX_CAM_STREAM_DIR.rstrip('/') + "/" +\
                        self.cam_dir + "/"
        self.os_context.make_dir(out_file_path)
        while True:
            # Camera streaming loop to stream from camera, cut and store in
            # multiple files. No error validation here, the files might be
            # created without any video data. The restreaming server validates
            # the files later.
            out_file = out_file_path +\
                    time.strftime("%d-%b-%Y:%H-%M-%S", time.gmtime()) + ".mp4"
            vlc_args = vlc_out_opts + [":sout=#file{dst=" + out_file + "}"]
            self.nv_log_handler.debug("Streaming  to a file %s" %str(vlc_args))
            self.os_context.execute_cmd("cvlc", vlc_args)
