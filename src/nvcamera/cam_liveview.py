#! /usr/bin/python3
# -*- coding: utf8 -*-
# The camera live view handler module.. 
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from src.nv_logger import nv_logger
from src.nv_lib.nv_os_lib import nv_os_lib
import ipaddress

class nv_cam_liveview():
    '''
    Class to handle the live view of camera stream. Cameras output the streams
    in rtsp format. browser doesnnt support rtsp support. This module transcode
    the rtsp into http and send it to browser for the live preview.
    '''
    def __init__(self, cam_tbl_entry = None):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        if cam_tbl_entry is None:
            self.nv_log_handler.error("Cannot start live preview for empty"
                                      "camera entry")
            return
        self.cam_id = cam_tbl_entry.cam_id
        self.cam_name = cam_tbl_entry.name
        self.live_url = cam_tbl_entry.live_url
        self.cam_uname = cam_tbl_entry.username
        self.cam_pwd = cam_tbl_entry.password
        self.cam_ip = str(ipaddress.IPv4Address(cam_tbl_entry.ip_addr))
        self.cam_listen_port = str(cam_tbl_entry.listen_port)
        self.os_context = nv_os_lib()
        self.live_thread = None

    def start_live_preview(self):
        '''
        Start the preview thread to do the transcode and xmit the stream
        @return live_url : HTTP url to view the live preview.
        '''
        cam_src_path = ["rtsp://" + self.cam_uname + ":" + self.cam_pwd + "@" +\
                        self.cam_ip + ":" + self.cam_listen_port]
        vlc_out_opts = cam_src_path + ["--live-caching=3000"]

        if self.live_url:
            self.nv_log_handler.info("The live stream is already running on %s",
                                     "Cannot start the stream again", 
                                     self.live_url)
            return None
        if self.os_context.is_pgm_installed('cvlc') is None:
            #The cvlc is not found.
            self.nv_log_handler.error("cvlc is not installed, cannot live-stream")
            return None
        if self.os_context.is_pgm_installed('ffmpeg') is None:
            #The ffmpeg is not found., canoot transcode.
            self.nv_log_handler.error("ffmpeg is not installed, cannot live-stream")
            return None
        port_num = str(self.os_context.get_free_listen_port())
        vlc_args = vlc_out_opts + [":sout=#transcode{vcodec=theo,vb=200,fps=5,"
                                   "scale=0.25,acodec=none}:http{mux=ogg,dst=:"
                                   + port_num + "/" + str(self.cam_id) + "}",
                                   "--no-sout-audio" ]
        try:
            self.live_thread = self.os_context.execute_cmd_bg("cvlc", vlc_args)
            self.live_url = port_num + "/" + self.cam_name
        except Exception as e:
            self.nv_log_handler.error("Failed to start the live stream"
                                      "Error is %s", e)
            self.live_thread = None
            raise e
        return self.live_url

    def stop_live_preview(self):
        '''
        Stop the live preview of the camera.
        '''
        if not self.live_thread:
            self.nv_log_handler.info("live stream thread is not running for %s",
                                     self.cam_name)
            return
        try:
            self.os_context.kill_process(self.live_thread)
        except Exception as e:
            self.nv_log_handler.error("Failed to kill the live stream for %s",
                                      self.cam_name)
            raise e

    def get_live_preview_url(self):
        '''
        get the live preview URL for the specific camera
        '''
        return self.live_url

    def get_camera_name(self):
        return self.cam_name
