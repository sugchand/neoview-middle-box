#! /usr/bin/python3
# -*- coding: utf8 -*-
# The camera handler module for nv-middlebox.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from src.nvcamera.cam_handler import cam_handler
from src.nv_logger import nv_logger
from src.nvcamera.cam_liveview import nv_cam_liveview
from time import sleep
'''
Camera handler thread dictionary. the format for the dictionary should be
{ cam_id : cam_handler obj }
'''


'''
camera handler threads that are marked to stop. The list is used to wait for
camera threads before exiting the application
'''

class thread_manager():
    '''
    Handle threads of each camera. A thread is created for every camera handler
    operation. Only one instance of thread manager should be present in the
    middle box application.
    '''
    def __init__(self):
        # Initialize the thread manager
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.cam_thread_dic = {}
        self.join_cam_thread_dic = {}
        # Live streaming dictionary, A dictionary maintained for live streaming
        # threads.
        self.cam_live_threads = {}
        # camera live threads for join
        self.join_cam_live_threads = {}

    def start_camera_thread(self,cam_table_entry):
        # Create a thread for camera stream handling if not exists
        # Store the thread details in the global list.
        cam_id = cam_table_entry.cam_id
        if cam_id in self.cam_thread_dic.keys() and\
            self.cam_thread_dic[cam_id] is not None:
            self.nv_log_handler.error("A thread is already exists for the"
                                      "camera with id %d" % cam_id)
            return
        cam_obj = cam_handler(cam_table_entry)
        self.cam_thread_dic[cam_id] = cam_obj
        cam_obj.start_camera_thread()
        self.nv_log_handler.debug("camera thread is created for %d", cam_id)

    def cleanup_camera_dic(self):
        '''
        Function to delete all the unwanted saved camera information.
        '''
        self.cam_thread_dic = dict((cam_id, cam_obj) for cam_id, cam_obj in \
                              self.cam_thread_dic.items() if cam_obj)
        self.join_cam_thread_dic = dict((cam_id, cam_obj) for cam_id, cam_obj in \
                                   self.join_cam_thread_dic.items() if cam_obj)
        self.cam_live_threads = dict((cam_id, cam_obj) for cam_id, cam_obj in \
                                   self.cam_live_threads.items() if cam_obj)
        self.join_cam_live_threads = dict((cam_id, cam_obj) for cam_id, cam_obj in \
                                   self.join_cam_live_threads.items() if cam_obj)

    def stop_camera_thread(self, cam_id, cam_obj = None):
        # Do a cleanup to remove all rogue data before stopping the threads.
        self.cleanup_camera_dic()
        self.stop_camera_thread_(cam_id, cam_obj)

    def stop_camera_thread_(self, cam_id, cam_obj = None):
        # Destroy the camera thread that created earlier.
        if cam_obj is None:
            cam_obj = self.cam_thread_dic.get(cam_id)
        if not cam_obj:
            self.nv_log_handler.debug("The camera handler thread not exists for"
                                      " %d", cam_id)
            return
        try:
            cam_obj.stop_camera_thread()
            # Append the camera thread to the join list
            self.join_cam_thread_dic[cam_id] = self.cam_thread_dic[cam_id]
            self.cam_thread_dic[cam_id] = None
            self.nv_log_handler.debug("The camera handler thread stopped for"
                                  " camera id %d", cam_id)
        except Exception as e:
            self.nv_log_handler.debug("Failed to stop camera %d"
                                      "with exception %s", cam_id, str(e))
            raise e

    def stop_all_camera_threads(self):
        # Destroy all the threads that created by the thread manager.
        for cam_id, cam_obj in self.cam_thread_dic.items():
            self.stop_camera_thread(cam_id, cam_obj)

    def join_camera_thread(self, cam_id, cam_obj):
        if cam_obj is None:
            cam_obj = self.join_cam_thread_dic[cam_id]
        if not cam_obj:
            self.nv_log_handler.debug("The camera handler thread doesnt exists"
                                      " to join cam-id : %d" % cam_id)
            return
        try:
            cam_obj.join_camera_thread()
            self.join_cam_thread_dic[cam_id] = None
        except:
            self.nv_log_handler.error("Failed to join the camera thread %d"
                                      % cam_id)
        finally:
            self.cleanup_camera_dic()

    def join_all_camera_threads(self):
        try:
            for cam_id, cam_obj in self.join_cam_thread_dic.items():
                self.join_camera_thread(cam_id, cam_obj)
        except:
            self.nv_log_handler.error("Failed to join the camera threads.")

    def start_cam_live(self, cam_tbl_entry):
        if not cam_tbl_entry:
            self.nv_log_handler.debug("Empty table entry, cannot start live")
            return
        cam_id = cam_tbl_entry.cam_id
        if cam_id is None:
            self.nv_log_handler.info("Invalid camera ID, Cannot start live "
                                     "streaming")
            return
        if self.cam_live_threads.get(cam_id):
            self.nv_log_handler.error("Cannot start live streaming, "
                                      "some other live streaming obj exists")
            return
        live_obj = nv_cam_liveview(cam_tbl_entry = cam_tbl_entry)
        try:
            self.nv_log_handler.debug("starting the live on %s", cam_tbl_entry.name)
            live_obj.start_live_preview()
            self.nv_log_handler.info("Live-url is getting ready.... ")
            sleep(2) # Make sure the live url is populated in the live thread.
            url = live_obj.get_live_preview_url()
            self.cam_live_threads[cam_id] = live_obj
            return url
        except Exception as e:
            self.nv_log_handler.error("Failed to start live streaming on %s",
                                      " exception : %s", cam_tbl_entry.name, e)
            return None

    def stop_cam_live(self, cam_id):
        if not cam_id:
            self.nv_log_handler.debug("Cam_id is empty cannot stop live")
            return
        if cam_id not in self.cam_live_threads.keys():
            self.nv_log_handler.error("Failed to find %d, cannot stop live",
                                      cam_id)
            return
        live_obj = self.cam_live_threads.get(cam_id)
        if not live_obj:
            self.nv_log_handler.error("Failed to find live obj for %d",
                                      cam_id)
            return
        try:
            live_obj.stop_live_preview()
            self.join_cam_live_threads[cam_id] =self.cam_live_threads[cam_id]
            self.cam_live_threads[cam_id] = None
            self.nv_log_handler.info("Stopped the camera live thread for %s",
                                     live_obj.get_camera_name())
        except Exception as e:
            self.nv_log_handler.error("Failed to stop live preview on %s"
                                      "Exception is %s",
                                      live_obj.get_camera_name(), e)
        try:
            live_obj.join_live_preview()
            self.join_cam_live_threads[cam_id] = None
        except Exception as e:
            self.nv_log_handler.info("Failed to do join on livethread "
                                     "of camera %s", live_obj.get_camera_name())

    def stop_all_camlive(self):
        self.nv_log_handler.debug("stopping all the camera live streams")
        for cam_id, _ in self.cam_live_threads.items():
            self.stop_cam_live(cam_id)
