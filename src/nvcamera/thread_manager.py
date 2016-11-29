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
'''
Camera handler thread dictionary. the format for the dictionary should be
{ cam_id : cam_handler obj }
'''
cam_thread_dic = {}

'''
camera handler threads that are marked to stop. The list is used to wait for
camera threads before exiting the application
'''
join_cam_thread_dic = {}

class thread_manager():
    '''
    Handle threads of each camera. A thread is created for every camera handler
    operation. Only one instance of thread manager should be present in the
    middle box application.
    '''
    def __init__(self):
        # Initialize the thread manager.
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        pass

    def start_camera_thread(self,cam_table_entry):
        # Create a thread for camera stream handling if not exists
        # Store the thread details in the global list.
        cam_id = cam_table_entry.cam_id
        if cam_id in cam_thread_dic.keys() and\
            cam_thread_dic[cam_id] is not None:
            self.nv_log_handler.error("A thread is already exists for the"
                                      "camera with id %d" % cam_id)
            return
        cam_obj = cam_handler(cam_table_entry)
        cam_thread_dic[cam_id] = cam_obj
        cam_obj.start_camera_thread()
        self.nv_log_handler.debug("camera thread is created for %d", cam_id)

    def stop_camera_thread(self, cam_id, cam_obj = None):
        # Destroy the camera thread that created earlier.
        if cam_obj is None:
            cam_obj = cam_thread_dic.get(cam_id)
        if not cam_obj:
            self.nv_log_handler.debug("The camera handler thread not exists for"
                                      " %d", cam_id)
            return
        try:
            cam_obj.stop_camera_thread()
            # Append the camera thread to the join list
            join_cam_thread_dic[cam_id] = cam_thread_dic[cam_id]
            cam_thread_dic[cam_id] = None
            self.nv_log_handler.debug("The camera handler thread stopped for"
                                  " camera id %d", cam_id)
        except Exception as e:
            self.nv_log_handler.debug("Failed to stop camera %d"
                                      "with exception %s", cam_id, str(e))
            raise e

    def stop_all_camera_threads(self):
        # Destroy all the threads that created by the thread manager.
        for cam_id, cam_obj in cam_thread_dic.items():
            self.stop_camera_thread(cam_id, cam_obj)

    def start_all_camera_threads(self):
        # Read camera DB for each camera entry.
        # create handler thread for each entry and store it in the thread list.
        # function get called while initilizing.
        pass

    def join_camera_thread(self, cam_id, cam_obj):
        if cam_obj is None:
            cam_obj = join_cam_thread_dic[cam_id]
        if not cam_obj:
            self.nv_log_handler.debug("The camera handler thread doesnt exists"
                                      "%d" % cam_id)
            return
        try:
            cam_obj.join_camera_thread()
            join_cam_thread_dic[cam_id] = None
        except:
            self.nv_log_handler.error("Failed to join the camera thread %d"
                                      % cam_id)

    def join_all_camera_threads(self):
        try:
            for cam_id, cam_obj in join_cam_thread_dic.items():
                self.join_camera_thread(cam_id, cam_obj)
        except:
            self.nv_log_handler.error("Failed to join the camera threads.")

