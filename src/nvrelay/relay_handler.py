'''
Created on 10 Sep 2016

@author: sugesh
'''

#! /usr/bin/python3
# -*- coding: utf8 -*-
# The camera handler module for nv-middlebox. 
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import time  
from watchdog.observers import Observer  
from watchdog.events import FileSystemEventHandler
from src.settings import NV_MID_BOX_CAM_STREAM_DIR

class relay_ftp_handler():
    '''
    the relay handler class to do the file copying from middlebox to webserver.
    '''
    def __init__(self):
        pass

    def local_file_transfer(self, nv_cam_src, dst):
        # Copy the file nv_cam_src to dst.
        pass

    def remote_file_transfer(self, nv_cam_src, dst):
        # Copy the file remotely.
        pass

    def is_webserver_local(self, webserver):
        '''
        Check if the webserver deployed on the same machine.
        Returns:
        True : Middlebox and webserver on the same machine
        False : Webserver deployed on a different machine
        '''
        # TODO :: Lets implement only local now.
        return True
 
class relay_watcher(FileSystemEventHandler):
    '''
    The watcher notified when a file change event happened. 
    '''
    def __init__(self):
        self.ftp_obj = relay_ftp_handler()
        self.is_local_wbs = self.ftp_obj.is_webserver_local(None)

    def process(self, event):
        """
        event.event_type 
            'modified' | 'created' | 'moved' | 'deleted'
        event.is_directory
            True | False
        event.src_path
            path/to/observed/file
        """
        # the file will be processed there
        print(event.src_path, event.event_type)  # print now only for degug

    def on_modified(self, event):
        self.process(event)

    def on_created(self, event):
        # Check if the webserver local, copy the file to a specified location
        if self.is_local_wbs:
            print("local copy")
        self.process(event)

    def on_deleted(self,event):
        self.process(event)

    def on_any_event(self,event):
        self.process(event)

class relay_main():
    '''
    The relay main thread class for the file event handling
    '''
    def __init__(self):
        self.watcher_obj = relay_watcher()
        self.observer_obj = Observer()

    def process_relay(self):
        self.observer_obj.schedule(self.watcher_obj, NV_MID_BOX_CAM_STREAM_DIR,
                                   recursive=True)
        self.observer_obj.start()

    def relay_stop(self):
        self.observer_obj.stop()

    def relay_join(self):
        self.observer_obj.join()
