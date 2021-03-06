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
from src.nv_lib.ipc_data_obj import enum_ipcOpCode, camera_data
from src.nv_lib.nv_sync_lib import GBL_CONF_QUEUE
from src.nvdb.nvdb_manager import nv_camera
from src.nvdb.nvdb_manager import db_mgr_obj
from src.nvdb.nvdb_manager import enum_camStatus

import ipaddress
from threading import Thread
from threading import Event
from time import sleep

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
        self.live_thread_cmd = None
        self.live_cam_thread = None
        self.cam_live_stop_event = Event()
        # Do not modify the value in methods
        self.const_stream_len_sec = cam_tbl_entry.stream_file_time_sec
        # Do not modify this value in any of methods
        self.const_live_stream_timeout = self.const_stream_len_sec * 4
        self.stream_state = cam_tbl_entry.status
        self.state_chk_timeout = self.const_stream_len_sec

    def do_live_preview(self):
        '''
        Helper function to do the live preview operation
        '''
        cam_src_path = ["rtsp://" + self.cam_uname + ":" + self.cam_pwd + "@" +\
                        self.cam_ip + ":" + self.cam_listen_port]
        vlc_out_opts = cam_src_path + ["--live-caching=3000"]

        if self.os_context.is_pgm_installed('cvlc') is None:
            #The cvlc is not found.
            self.nv_log_handler.error("cvlc is not installed, cannot live-stream")
            return None
        if self.os_context.is_pgm_installed('ffmpeg') is None:
            #The ffmpeg is not found., canoot transcode.
            self.nv_log_handler.error("ffmpeg is not installed, cannot live-stream")
            return None
        port_num = str(self.os_context.get_free_listen_port())
        vlc_args = vlc_out_opts + [":sout=#transcode{vcodec=theo,vb=250,fps=20,"
                                   "scale=0.25,acodec=none,threads=4}:"
                                   "http{mux=ogg,dst=:"
                                   + port_num + "/" + str(self.cam_id) + "}",
                                   "--no-sout-audio" ]
        try:
            self.live_thread_cmd = self.os_context.execute_cmd_bg("cvlc", vlc_args)
            self.live_url = port_num + "/" + str(self.cam_id)
        except Exception as e:
            self.nv_log_handler.error("Failed to start the live stream"
                                      "Error is %s", e)
            self.live_thread_cmd = None
            raise e
        return self.live_url

    def is_camera_reachable(self):
        #Check if the port and camera ip is reachable.
        try:
            is_open = self.os_context.is_remote_port_open(ip=self.cam_ip,
                                        port=int(self.cam_listen_port))
            if is_open:
                return True
        except:
            self.nv_log_handler.error("Exception while checking "
                                      "connectivity to camera %s",
                                      self.cam_name)
        self.nv_log_handler.error("%s Camera is unreachable,"
                                "cannot start the live-preview..",
                                self.cam_name)
        return False

    def update_livestream_in_DB(self, new_liveUrl = None):
        '''
        Update the livestream in the configuration DB
        '''
        # Update the config module
        try:
            # Only name and new url needed to update the liveurl.
            live_obj = camera_data(op = enum_ipcOpCode.CONST_UPDATE_CAMERA_LIVESTREAM_URL,
                                   name = self.cam_name,
                                   # Everything else can be None
                                   status = None,
                                   ip = None,
                                   macAddr = None,
                                   port = None,
                                   time_len = None,
                                   uname = None,
                                   pwd = None,
                                   desc = None,
                                   live_url = new_liveUrl
                                   )
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1,
                                        obj_value = [live_obj])
        except Exception as e:
            self.nv_log_handler.error("Failed to update live stream url of %s"
                                      "Exception : %s",
                                       self.cam_name, e)
            raise e

    def restart_live_stream(self):
        '''
        Stop the current live stream thread and start a new one.
        Used to restart the live preview in case there are connection
        issues with the camera
        @return: url : the new url after starting the live stream
        '''
        new_liveUrl = None
        try:
            self.stop_live_preview__()
            new_liveUrl= self.do_live_preview()
        except Exception as e:
            self.nv_log_handler.info("Failed to start live preview again "
                                     " on %s Exception %s",
                                     self.cam_name, e)
            raise e
        finally:
            return new_liveUrl

    def stream_state_changed(self):
        '''
        Check if the state of camera streaming changed.
        Only valid states are considered, which are ON, OFF.
        Doesnt consider DISCONNECTED and DISABLED states are valid.
        @return: True : If state of streaming changed and new state is valid.
                 False : Either the state is not changed/currently not in valid
                         state.
        '''
        if self.state_chk_timeout:
            '''
            No need to do the camera status check in the loop.
            Validate only on the timeout. The purpose of this is to avoid
            unnecessary DB read for the validation.
            '''
            self.state_chk_timeout -= 1
            return False

        self.state_chk_timeout = self.const_stream_len_sec
        filter_arg = {'name' : self.cam_name}
        cam_record = None
        try:
            db_mgr_obj.db_start_transaction()
            cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera,
                                                                   filter_arg)
            db_mgr_obj.db_end_transaction()
        except:
            # Release the db lock in error in case its not yet released
            db_mgr_obj.db_end_transaction()
            return False
        if cam_record is None:
            self.nv_log_handler.error("Empty camera record for %s, Cannot read",
                                      self.cam_name)
            return False
        if cam_record.status is not enum_camStatus.CONST_CAMERA_READY and \
                cam_record.status is not enum_camStatus.CONST_CAMERA_RECORDING:
            return False
        if cam_record.status is self.stream_state:
            return False
        self.stream_state = cam_record.status
        return True

    def start_live_preview__(self, stop_event):
        '''
        (Class internal function)
        Start the preview thread to do the transcode and xmit the stream
        Set the HTTP url to view the live preview.
        @param  stop_event : Sets by thread manager to stop the live preview
        '''
        if self.live_url:
            self.nv_log_handler.info("The live stream is already running on %s"
                                     "Cannot start the stream again",
                                     self.live_url)
            return
        try:
            #Check if the port and camera ip is reachable.
            if not self.is_camera_reachable():
                self.live_url = None
                return
            self.do_live_preview()
        except Exception as e:
            self.live_url = None
            self.nv_log_handler.error("Failed to start the live preview on %s"
                                      "Exception :%s", self.cam_name, e)
            return

        # Live preview may disturbed by external connectivity issues. There is
        # no way liveview thread can detect those issues. Once the connection
        # is lost liveview thread becomes rogue and it cannot reconnect again
        # when camera become live.
        # As a fix liveview thread teardown connection when connection lost.
        # This allows the live view is not disturbed by connectivity issues
        if self.const_stream_len_sec <= 0:
            self.nv_log_handler.error("stream length in seconds is not valid,"
                                      " cannot run the live view thread")
            try:
                self.stop_live_preview__()
            except:
                self.nv_log_handler.error("Failed to stop streaming for %s"
                                          "when the stream timeout is invalid",
                                          self.cam_name)
            finally:
                self.live_url = None
            return
        timeout = 0
        cam_conn_ok = True
        new_liveUrl = None
        self.update_livestream_in_DB(new_liveUrl = self.live_url)
        while not stop_event.is_set():
            sleep(0.25) # 25 milliseconds to check the connections
            if timeout:
                # Camera disconnected and wait for reconnect mode
                timeout -= 1
                continue
            try:
                # Validate the camera reachability.
                if not self.is_camera_reachable():
                    timeout = self.const_live_stream_timeout
                    cam_conn_ok = False
                    continue
                # Vlc lib is not very stable to process the streaming for long
                # time. Sometime it hangs due to unknown issues. There is no
                # way liveview can detect it. As a fix, liveview is restarted
                # for every camera streaming switch status change.
                if self.stream_state_changed() or not cam_conn_ok:
                    # Have camera connectivity, but connection lost before. so
                    # reconnect
                    new_liveUrl = self.restart_live_stream()
                    cam_conn_ok = True
                    self.live_url = new_liveUrl
                    self.update_livestream_in_DB(new_liveUrl = new_liveUrl)
            except Exception as e:
                self.nv_log_handler.error("%s error in restarting the live", e)
                self.stop_live_preview__()

        # stop the thread as the live view is stopped by thread manager.
        self.stop_live_preview__()

    def start_live_preview(self):
        '''
        Start the camera live view thread
        '''
        if self.live_cam_thread:
            self.nv_log_handler.error("Cannot start live-view thread, "
                                        "its already exists")
            return
        self.live_cam_thread = Thread(name=self.cam_name + str(self.cam_id) +
                                      "-live",
                              target=self.start_live_preview__,
                              args = (self.cam_live_stop_event,))
        self.live_cam_thread.daemon = True
        self.live_cam_thread.start()

    def stop_live_preview(self):
        '''
        External function to stop the live view thread
        '''
        self.cam_live_stop_event.set()

    def stop_live_preview__(self):
        '''
        Stop the live preview of the camera.(Class internal function)
        '''
        if not self.live_thread_cmd or not self.live_url:
            self.nv_log_handler.info("live stream thread is not running for %s",
                                     self.cam_name)
            return
        try:
            self.os_context.kill_process(self.live_thread_cmd)
            self.live_url = None
            self.live_thread_cmd = None
        except Exception as e:
            self.nv_log_handler.error("Failed to kill the live stream for %s",
                                      self.cam_name)
            raise e

    def join_live_preview(self, timeout=2):
        '''
        Join wait call for the live view thread, Must called to make sure the
        thread is stopped successfully
        @param timeout: timeout to exit the join call. 
        '''
        if self.live_cam_thread is not None and self.live_cam_thread.isAlive():
            self.live_cam_thread.join(timeout=timeout)

    def get_live_preview_url(self):
        '''
        get the live preview URL for the specific camera
        '''
        return self.live_url

    def get_camera_name(self):
        return self.cam_name
