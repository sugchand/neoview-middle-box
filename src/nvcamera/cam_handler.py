#! /usr/bin/python3
# -*- coding: utf8 -*-
# The camera handler module for nv-middlebox. 
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from builtins import None
from vlc import *
from nvdb.nvdb_manager import nv_camera

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
        self.tot_out_file_cnt = cam_tbl_entry.stream_file_cnt
        self.time_lapse = cam_tbl_entry.stream_file_time_sec
        self.curr_stream_cnt = 0
        self.file_prefix = str(cam_tbl_entry.cam_id)  
        pass
        
    
    def stream_out_file
        self.vlc_instance = vlc.Instance("""-vvv --start-time 0 --stop-time 60 --sout=#standard{access=file,mux=ts,dst=/home/sugesh/outtest.mp4}""")
        med = inst.media_new("/tmp/testvideo.mp4")
        p = med.player_new_from_media()
        p.play()
        