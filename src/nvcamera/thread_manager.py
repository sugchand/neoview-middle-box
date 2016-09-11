#! /usr/bin/python3
# -*- coding: utf8 -*-
# The camera handler module for nv-middlebox.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

cam_thread_list = {}

class thread_manager():
    '''
    Handle threads of each camera. A thread is created for every camera handler
    operation. Only one instance of thread manager should be present in the
    middle box application.
    '''
    def __init__(self):
        # Initialize the thread manager.
        pass

    def start_camera_thread(self,cam_id):
        # Create a thread for camera stream handling if not exists
        # Store the thread details in the global list.
        pass

    def stop_camera_thread(self, cam_id):
        # Destroy the camera thread that created earlier.
        pass

    def stop_all_camera_threads(self):
        # Destroy all the threads that created by the thread manager.
        pass

    def start_all_camera_threads(self):
        # Read camera DB for each camera entry.
        # create handler thread for each entry and store it in the thread list.
        # function get called while initilizing.
        pass

    def join_camera_thread(self,cam_id):
        pass 
