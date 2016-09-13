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

from watchdog.observers import Observer  
from watchdog.events import FileSystemEventHandler
from src.settings import NV_MID_BOX_CAM_STREAM_DIR
from src.nvdb.nvdb_manager import db_mgr_obj
from src.nv_logger import nv_logger
from src.nv_lib.nv_os_lib import nv_os_lib
class relay_ftp_handler():
    '''
    the relay handler class to do the file copying from middlebox to webserver.
    '''
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.os_context = nv_os_lib()
        self.copy_selector = False
        '''
        A list to buffer the file copy information. each entry in the list holds
        src and dst information for the file copy.
        The file to be copied selected using copy_selector.
        the list should be like [[src1, dst1], [src2, dst2]]
        '''
        self.copy_file_list = [[None, None], [None, None]]

    def is_file_to_copy_valid(self, file_path):
        '''
        Function to validate if the file_path is a corrupted file or not.
        For now we assume if the file size is greater than 10MB its good to go,
        though its not an right assumption.
        '''
        ten_mb = 10000000 # 10MB in Bytes
        file_size = self.os_context.get_filesize_in_bytes(file_path)
        if file_size < ten_mb:
            return False
        return True

    def enqeue_copy_file_list(self, src, dst):
        '''
        NOTE ::: the list is not thread safe. Its responsibility of caller to
        access to the list and selector in thread safe manner.Also this function
        must be executed in atomic manner.
        The assumption here is copying of file must be faster than getting a file
        generated.
        '''
        self.copy_file_list[self.copy_selector] = [src, dst]
        # Toggle the index
        self.copy_selector = self.copy_selector ^ True
        # Copy if a valid file exists
        copy_path = self.copy_file_list[self.copy_selector]
        if not copy_path[0]:
            return
        self.nv_log_handler.debug("Copying file %s to %s"% \
                                  (copy_path[0], copy_path[1]))
        self.os_context.copy_file(copy_path[0], copy_path[1])
        # Reset the data after copying.
        self.copy_file_list[self.copy_selector] = [None, None]

    def local_file_transfer(self, nv_cam_src, webserver):
        # Copy the file nv_cam_src to dst.
        if not self.is_media_file(nv_cam_src):
            self.nv_log_handler.debug("%s is not a media file, Do not copy" % \
                                      nv_cam_src)
            return
        dst_path = webserver.video_path
        # Get the absolute path directory name of the file.
        cam_src_dir = self.os_context.get_dirname(nv_cam_src)
        # Find the camera folder name in the absolute path.
        cam_src_dir = self.os_context.get_last_filename(cam_src_dir)
        dst_dir = self.os_context.join_dir(dst_path, cam_src_dir)
        if not self.os_context.is_path_exists(dst_dir):
            self.nv_log_handler.debug("Create the directory %s" % dst_dir)
            self.os_context.make_dir(dst_dir)
        self.enqeue_copy_file_list(nv_cam_src, dst_dir)
        self.nv_log_handler.debug("Enqueued file %s to %s" %(nv_cam_src, dst_dir))

    def remote_file_transfer(self, nv_cam_src, webserver):
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

    def is_media_file(self, file_path):
        '''
        Check if the file is media
        '''
        file_ext = '.mp4'
        return file_path.endswith(file_ext)

class relay_watcher(FileSystemEventHandler):
    '''
    The watcher notified when a file change event happened. 
    '''
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
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
    #    print(event.src_path, event.event_type)  # print now only for degug

    #def on_modified(self, event):
    #    self.process(event)

    def on_created(self, event):
        # Check if the webserver local, copy the file to a specified location
        websrv = db_mgr_obj.get_webserver_record()
        if not websrv:
            self.nv_log_handler.debug("Webserver is not configured")
            return
        if self.is_local_wbs:
            cam_src_path = event.src_path
            self.ftp_obj.local_file_transfer(cam_src_path, websrv)
    #    self.process(event)

    #def on_deleted(self,event):
    #    self.process(event)

    #def on_any_event(self,event):
    #    self.process(event)

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
