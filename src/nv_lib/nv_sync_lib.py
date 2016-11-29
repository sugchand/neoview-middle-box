#! /usr/bin/python3
# -*- coding: utf8 -*-
# The thread synchronization library.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from threading import Lock
from src.nv_logger import nv_logger

class nv_sync_lib():
    '''
    Class for synchronization between threads. The synchronization objects are
    stored in a dictionary to use them in need.
    XXX :: DO NOT CREATE OBJECTS FOR THIS CLASS. INSTEAD USE THE GLOBAL OBJECT
    'GBL_NV_SYNC_OBJ' FOR EVERY OPERATION. THIS WILL MAKE SURE EVERY THREAD
    ACCESS THE SAME SYNC DATA. DEADLOCKS ARE NOT HANDLED, MAKE SURE THE CALLER
    WILL TAKE CARE OF IT.
    '''
    def __init__(self):
        '''
        *_dic contain list of syncronization primitives as below.
        {
            'name1' : 'obj1',
            'name2' : 'obj2'
        }
        '''
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.mutex_dic = {}
        self.semaphone_dic = {}
        pass

    def mutex_lock(self, name):
        if not name in self.mutex_dic:
            # The mutex lock is not created , lets create one.
            try:
                self.mutex_dic[name] = Lock()
            except Exception as e:
                self.nv_log_handler.error("Failed to acquire lock %s"
                                          % name)
                raise e
        self.mutex_dic[name].acquire()

    def mutex_unlock(self, name):
        if not name in self.mutex_dic:
            self.nv_log_handler.error("Cannot unlock non-existent lock %s"
                                      % name)
            return
        self.mutex_dic[name].release()

    def is_mutex_locked(self, name):
        if not name in self.mutex_dic:
            self.nv_log_handler.error("Cannot check status of non-existent lock"
                                      % name)
            return
        self.mutex_dic[name].locked()

    def list_mutex_locks(self):
        '''
        debug function to display all the created mutex locks at the moment
        '''
        pass


GBL_NV_SYNC_OBJ = nv_sync_lib()