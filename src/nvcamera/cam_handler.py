#! /usr/bin/python3
# -*- coding: utf8 -*-
# The camera handler module for nv-middlebox. 
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from src.nv_logger import nv_logger
from src.nv_lib.nv_os_lib import nv_os_lib
import time
import ipaddress
from src.settings import NV_MID_BOX_CAM_STREAM_DIR
from threading import Thread
from threading import Event
from src.nv_lib.ipc_data_obj import camera_data, enum_ipcOpCode
from src.nv_lib.nv_sync_lib import GBL_CONF_QUEUE
from src.nvdb.nvdb_manager import enum_camStatus

class cam_handler():

    '''
    Each camera had a camera handler instance to stream and store the video file
    in the local media-box server 
    '''
    def __init__(self, cam_tbl_entry=None):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.time_lapse = cam_tbl_entry.stream_file_time_sec

        self.cam_id = str(cam_tbl_entry.cam_id)
        self.name = cam_tbl_entry.name
        self.cam_dir = self.name
        self.username = cam_tbl_entry.username
        self.pwd = cam_tbl_entry.password
        self.cam_ip = str(ipaddress.IPv4Address(cam_tbl_entry.ip_addr))
        self.cam_listen_port = str(cam_tbl_entry.listen_port)
        self.os_context = nv_os_lib()
        self.nv_log_handler.debug("Initialized the camera handler for %s.",
                                  self.name)
        self.cam_thread_obj = None
        self.cam_stream_stop_event = Event()
        self.vlc_thread = None

    def save_camera_stream_in_multifile(self, stop_event):
        cam_src_path = ["rtsp://" + self.username + ":" + self.pwd + "@" +\
                        self.cam_ip + ":" + self.cam_listen_port]
        vlc_out_opts = cam_src_path +\
                       ["--no-loop", "--no-repeat", "--play-and-exit",
                        "--live-caching=3000", #"--rt-priority",
                       "--stop-time=" +
                        str(self.time_lapse)]
        if self.os_context.is_pgm_installed('cvlc') is None:
            #The cvlc is not found.
            self.nv_log_handler.error("cvlc not installed, cannot stream")
            return
        out_file_path = NV_MID_BOX_CAM_STREAM_DIR.rstrip('/') + "/" +\
                        self.cam_dir + "/"
        self.os_context.make_dir(out_file_path)
        while not stop_event.is_set():
            # Camera streaming loop to stream from camera, cut and store in
            # multiple files. No error validation here, the files might be
            # created without any video data. The restreaming server validates
            # the files later.
            out_file = out_file_path +\
                    time.strftime("%d-%b-%Y:%H-%M-%S", time.gmtime()) + ".mp4"
            vlc_args = vlc_out_opts + [":sout=#file{dst=" + out_file + "}"]
            self.nv_log_handler.debug("Streaming  to a file %s" %str(vlc_args))
            self.vlc_thread = self.os_context.execute_cmd_bg("cvlc", vlc_args)
            self.os_context.wait_cmd_complete(self.vlc_thread)
        # Delete the last file as it may be not safe to share.
        self.nv_log_handler.debug("delete last video snip %s before exiting,",
                                  out_file)
        self.os_context.remove_file(out_file)
        # Set the camera status to ready while exiting the streaming.
        cam_ipcData = camera_data(op = enum_ipcOpCode.CONST_UPDATE_CAMERA_STATUS,
                                  name = self.name,
                                  status = enum_camStatus.CONST_CAMERA_READY,
                                  # Everything else is None.
                                  ip = None,
                                  macAddr = None,
                                  port = None,
                                  time_len = None,
                                  uname = None,
                                  pwd =  None,
                                  desc = None
                                  )
        try:
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1, obj_value = [cam_ipcData])
        except Exception as e:
            self.nv_log_handler.error("Failed to change the camera status while"
                                      "stopping the streaming, %s", e)
        self.nv_log_handler.debug("Exiting the camera thread for %s" \
                                  % self.cam_id)

    def start_camera_thread(self):
        '''
        Start the camera streaming from the camera named cam_id
        '''
        if self.cam_thread_obj:
            self.nv_log_handler.error("Cannot start streaming thread, " 
                                        "its already exists")
            return
        self.cam_thread_obj = Thread(name=self.cam_id,
                              target=self.save_camera_stream_in_multifile,
                              args = (self.cam_stream_stop_event,))
        self.cam_thread_obj.daemon = True
        self.cam_thread_obj.start()

    def stop_camera_thread(self):
        '''
        Stop the camera streaming of camera with id 'cam_id'
        '''
        self.cam_stream_stop_event.set()

    def kill_camera_thread(self):
        '''
        Kill the camera thread in the emergency event.
        '''
        self.cam_stream_stop_event.set()
        try:
            self.os_context.kill_process(self.vlc_thread)
        except Exception as e:
            self.nv_log_handler.error("Failed to kill the vlc thread in force"
                                      "%s", e)

    def join_camera_thread(self):
        '''
        Wait for camera streamer thread to join in the main thread.
        '''
        if self.cam_thread_obj is not None and self.cam_thread_obj.isAlive():
            self.cam_thread_obj.join()

    def get_camid_by_name(self, cam_name):
        '''
        Find the camera ID for a camera with given name. Its expected the camera
        names has to be unique. Otherwise the result is undetermined.
        '''
        pass
