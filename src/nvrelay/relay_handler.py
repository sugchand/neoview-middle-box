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
from src.nv_lib.nv_sync_lib import GBL_NV_SYNC_OBJ
from src.settings import NV_CAM_VALID_FILE_SIZE
import queue

class relay_queue_mgr():
    '''
    Class to manage files to copy. It maintain one queue per camera stream.
    '''
    def __init__(self):
        '''
        Dictionary to hold the different queues. the dictionary will be looks
        like
        cam_stream_queue_dic = {
                            'camera1' : queue1,
                            'camera2' : queue2
                             }
        '''
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.cam_stream_queue_dic = {}

    def enqueue_file_pair(self, cam_name, src, dst):
        if not cam_name in self.cam_stream_queue_dic:
            # There is no queue for specific camera, create it.
            rel_queue = queue.Queue()
            self.cam_stream_queue_dic[cam_name] = rel_queue
        else:
            rel_queue = self.cam_stream_queue_dic[cam_name]
        rel_queue.put([src, dst])

    def dequeue_file_pair(self, cam_name):
        if not cam_name in self.cam_stream_queue_dic:
            self.nv_log_handler.debug("Cannot dequeue from a non-existent queue"
                                      ": %s" % cam_name)
            return [None, None]
        rel_queue = self.cam_stream_queue_dic[cam_name]
        if rel_queue.empty():
            self.nv_log_handler.debug("Cannot dequeue from a empty queue")
            return [None, None]
        return rel_queue.get()

class relay_ftp_handler():
    '''
    the relay handler class to do the file copying from middlebox to webserver.
    '''
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.os_context = nv_os_lib()
        self.websrv = None 
        self.sftp = None
        self.queue_mgr = relay_queue_mgr()

    def is_file_to_copy_valid(self, file_path):
        '''
        Function to validate if the file_path is a corrupted file or not.
        For now we assume if the file size is greater than 10MB its good to go,
        though its not an right assumption.
        '''
        file_size = self.os_context.get_filesize_in_bytes(file_path)
        if file_size < NV_CAM_VALID_FILE_SIZE:
            return False
        return True

    def enqeue_copy_file_list(self, cam_name, src, dst):
        '''
        NOTE ::: 
        The assumption here is copying of file must be faster than getting a file
        generated.
        Relay agent trigger a copy operation for every file created by middle
        box streaming thread. Copying a file immediately on creation causes data
        loss/corruption as the file generation is not complete.
        The enqueue mechanism take care of it by copying a file only after the
        creation is complete. On creation files are enqueued and real copying is
        happen only at the time of second file creation.
        '''
        [cp_src, cp_dst] = self.queue_mgr.dequeue_file_pair(cam_name)
        self.queue_mgr.enqueue_file_pair(cam_name, src, dst)
        if cp_src is None or cp_dst is None:
            return [None, None]
        if not self.is_file_to_copy_valid(cp_src):
            self.nv_log_handler.debug("%s file size less than %d,"
                                      "Not copying to webserver",
                                      cp_src, NV_CAM_VALID_FILE_SIZE)
            return [None, None]
        return [cp_src, cp_dst]

    def local_file_transfer(self, nv_cam_src, websrv):
        # Copy the file nv_cam_src to dst.
        if not self.is_media_file(nv_cam_src):
            self.nv_log_handler.debug("%s is not a media file, Do not copy" % \
                                      nv_cam_src)
            return
        if not self.websrv:
            self.websrv = websrv
        dst_path = websrv.video_path
        # Get the absolute path directory name of the file.
        cam_src_dir = self.os_context.get_dirname(nv_cam_src)
        # Find the camera folder name in the absolute path.
        cam_src_dir = self.os_context.get_last_filename(cam_src_dir)
        dst_dir = self.os_context.join_dir(dst_path, cam_src_dir)
        if not self.os_context.is_path_exists(dst_dir):
            self.nv_log_handler.debug("Create the directory %s" % dst_dir)
            self.os_context.make_dir(dst_dir)
        file_pair = self.enqeue_copy_file_list(cam_src_dir, nv_cam_src, dst_dir)
        cp_src = file_pair[0]
        cp_dst = file_pair[1]
        if cp_src is None or cp_dst is None:
            return
        self.nv_log_handler.debug("Copying file %s to %s"% \
                                  (cp_src, cp_dst))
        self.os_context.copy_file(cp_src, cp_dst)

    def remote_file_transfer(self, nv_cam_src, websrv):
        # Copy the file remotely using scp/sftp.
        if not self.is_media_file(nv_cam_src):
            self.nv_log_handler.debug("%s is not a media file, Do not copy" % \
                                      nv_cam_src)
            return
        if not self.websrv:
            self.websrv = websrv
            self.sftp = self.os_context.get_remote_sftp_connection(
                                            hostname = websrv.name,
                                            username = websrv.uname,
                                            pwd = websrv.pwd)
        dst_path = websrv.video_path
        # Get the absolute path directory name of the file.
        cam_src_dir = self.os_context.get_dirname(nv_cam_src)
        # Find the camera folder name in the absolute path.
        cam_src_dir = self.os_context.get_last_filename(cam_src_dir)
        dst_dir = self.os_context.join_dir(dst_path, cam_src_dir)
        if not self.os_context.is_remote_path_exists(self.sftp, dst_dir):
            self.nv_log_handler.debug("Create the remote directory %s" % dst_dir)
            self.os_context.remote_make_dir(self.sftp, dir_name = dst_dir)
        file_pair = self.enqeue_copy_file_list(cam_src_dir, nv_cam_src, dst_dir)
        cp_src = file_pair[0]
        cp_dst = file_pair[1]
        if cp_src is None or cp_dst is None:
            return
        self.nv_log_handler.debug("Copying file %s to %s remotely"% \
                                  (cp_src, cp_dst))
        self.os_context.remote_copy_file(self.sftp,cp_src, cp_dst)

    def is_webserver_local(self, webserver):
        '''
        Check if the webserver deployed on the same machine.
        Returns:
        True : Middlebox and webserver on the same machine
        False : Webserver deployed on a different machine
        '''
        if webserver.name == 'localhost':
            return True
        return False

    def is_media_file(self, file_path):
        '''
        Check if the file is media
        '''
        file_ext = '.mp4'
        return file_path.endswith(file_ext)

    def kill_ftp_session(self):
        self.os_context.close_remote_sftp_connection()
        self.os_context.close_remote_host_connection()
        self.nv_log_handler.debug("Closing the ftp session..")
        pass

RELAY_MUTEX_NAME = "relay_watcher_mutex"

class relay_watcher(FileSystemEventHandler):
    '''
    The watcher notified when a file change event happened. 
    '''
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.websrv = None
        self.ftp_obj = relay_ftp_handler()
        self.is_relay_thread_killed = False # flag for tracking user kill.

    def kill_relay_thread(self):
        '''
        Function to kill the relay thread gracefully. It waits until the thread
        completes the current execution before initiate the kill.
        '''
        self.nv_log_handler.debug("Stopping the relay thread..")
        self.is_relay_thread_killed = True
        GBL_NV_SYNC_OBJ.mutex_lock(RELAY_MUTEX_NAME)
            # Wait until current relay thread completes its processing.
        try:
            self.ftp_obj.kill_ftp_session()
        except:
            self.nv_log_handler.error("Failed to close the ftp session properly")
        finally:
            GBL_NV_SYNC_OBJ.mutex_unlock(RELAY_MUTEX_NAME)

    def is_relay_thread_active(self):
        '''
        XXX :: Any relay thread operation must check/call this function
        before doing any kind of operation. This function returns whether
        the control thread/user issues a kill signal. The check must avoids
        unnecessary long wait for the kill signal execution.
        '''
        return self.is_relay_thread_killed

    def process(self, event):
        """
        event.event_type 
            'modified' | 'created' | 'moved' | 'deleted'
        event.is_directory
            True | False
        event.src_path
            path/to/observed/file
        """
        pass
        # the file will be processed there
    #    print(event.src_path, event.event_type)  # print now only for degug

    #def on_modified(self, event):
    #    self.process(event)

    def on_created(self, event):
        '''
        On a file creation, change the thread state to busy to avoid premature
        thread close. Close the thread only when there is no event to be
        handled.
        '''
        if(self.is_relay_thread_active()):
            #Kill signal issued, nothing to do.
            self.nv_log_handler.debug("Kill signal issued, no file copy")
            return
        GBL_NV_SYNC_OBJ.mutex_lock(RELAY_MUTEX_NAME)
        try:
            # Check if the webserver local, copy the file to a specified location
            self.websrv = db_mgr_obj.get_webserver_record()
            if not self.websrv:
                self.nv_log_handler.debug("Webserver is not configured")
                return
            is_local_wbs = self.ftp_obj.is_webserver_local(self.websrv)
            if is_local_wbs:
                cam_src_path = event.src_path
                self.ftp_obj.local_file_transfer(cam_src_path, self.websrv)
            else:
                # The server is remote and need to do the scp over network
                self.ftp_obj.remote_file_transfer(event.src_path, self.websrv)
        except:
            raise
        finally:
            #    self.process(event)
            GBL_NV_SYNC_OBJ.mutex_unlock(RELAY_MUTEX_NAME)

    #def on_deleted(self,event):
    #    self.process(event)

    #def on_any_event(self,event):
    #    self.process(event)

class relay_main():
    '''
    The relay main thread class for the file event handling.
    NOTE :: THIS THREAD SHOULDNT HOLD ANY LOCK OR ENTER INTO CRITICAL SECTION
    BY BLOCKING OTHER THREADS. ITS POSSIBLE THIS THREAD GET KILLED BY MAIN
    THREAD ANYTIME. HOLDING A CRITICAL SECTION RESOURCE IN THIS MODULE LEADS
    A DEAD LOCK.
    '''
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.os_context = nv_os_lib()
        self.watcher_obj = relay_watcher()
        self.observer_obj = Observer()

    def process_relay(self):
        try:
            if not self.os_context.is_path_exists(NV_MID_BOX_CAM_STREAM_DIR):
                self.nv_log_handler.error("%s Directory not found",
                                          NV_MID_BOX_CAM_STREAM_DIR)
                raise FileNotFoundError
            self.observer_obj.schedule(self.watcher_obj, NV_MID_BOX_CAM_STREAM_DIR,
                                       recursive=True)
            self.observer_obj.start()
        except FileNotFoundError:
            raise
        except Exception as e:
            raise e

    def relay_stop(self):
        self.watcher_obj.kill_relay_thread()
        self.observer_obj.stop()

    def relay_join(self):
        if self.observer_obj.isAlive():
            self.observer_obj.join()
