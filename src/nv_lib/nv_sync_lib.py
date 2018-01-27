#! /usr/bin/python3
# -*- coding: utf8 -*-
# The thread synchronization library.
#
from multiprocessing import RLock
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from time import time
from threading import current_thread
from threading import Lock
from src.nv_logger import nv_logger
from queue import Queue, Full, Empty


class nv_sync_queue():
    '''
    Class for interprocess queue. This queue used to communicated between
    threads.
    The values are in a LV format,
    L = the lenght of the value, it can be number of elements in the list.
    V = the value/object for the element. this must be a list.
    Eg:
        {
            "length" : 1
            "value" : [
                        cam_status_obj
                      ]
        }

    # cam_status_obj is object of ipc_data subclass.
    '''
    ipc_queue = None

    def __init__(self, q_name = "default_queue", max_size = 10000):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.ipc_queue = Queue(maxsize = max_size)
        self.q_name = q_name
        self.CONST_IPCQ_MUTEX = q_name

    def enqueue_data(self, obj_len, obj_value):
        '''
        obj_value is a list of objects depends on the obj_len
        '''
        if not isinstance(obj_value, list):
            self.nv_log_handler.error("Cannot enqueue non-list object")
            return
        for obj in obj_value:
            if not obj.is_ipc_datatype_valid():
                self.nv_log_handler.error("Cannot enqueue an invalid object.")
                return
            #self.nv_log_handler.debug("Received valid obj type %d to enqueue",
            #                          obj.get_ipc_datatype())
        tlv_obj = {
                   "length" : obj_len,
                   "value" : obj_value
                   }
        GBL_NV_SYNC_OBJ.mutex_lock(self.CONST_IPCQ_MUTEX)
        try:
            self.ipc_queue.put(tlv_obj, timeout = 1)
        except Full:
            self.nv_log_handler.error("Faile to put data, queue %s is full",
                                      self.q_name)
        except:
            self.nv_log_handler.error("Unknown error, Failed to put data in queue %s",
                                      self.q_name)
        finally:
            GBL_NV_SYNC_OBJ.mutex_unlock(self.CONST_IPCQ_MUTEX)

    def dequeue_data(self):
        tlv_obj = None
        GBL_NV_SYNC_OBJ.mutex_lock(self.CONST_IPCQ_MUTEX)
        try:
            tlv_obj = self.ipc_queue.get(timeout = 1)
        except Empty:
            #self.nv_log_handler.debug("Failed to read data from empty queue %s",
            #                          self.q_name)
            pass
        except:
            self.nv_log_handler.error("Unknown error, Failed to read data from queue %s",
                                      self.q_name)
        else:
            # Santiy check on stored object.
            obj_list = tlv_obj['value']
            if len(obj_list) != tlv_obj['length']:
                self.nv_log_handler.error("Error while dequeue,"
                                          "Length is not matching")
                tlv_obj = None
        finally:
            GBL_NV_SYNC_OBJ.mutex_unlock(self.CONST_IPCQ_MUTEX)
            return tlv_obj

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
        or dictionary can be like
        {
            'name1' : ['lock-obj1', thread-name, lock-time],
            'name2' : ['lock-obj2', thread-name, lock-time]
        }
        '''
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        # Mutex dictionary has a list of elements,
        self.mutex_dic = {}
        self.rlock_dic = {}
        pass

    def mutex_lock(self, name):
        '''
        Acquire a mutex lock with the given name. Same thread can acquire the
        lock only once. Its necessary to release the lock after
        the use
        '''
        if not name in self.mutex_dic:
            # The mutex lock is not created , lets create one.
            try:
                self.mutex_dic[name] = [Lock()]
            except Exception as e:
                self.nv_log_handler.error("Failed to acquire lock %s"
                                          % name)
                raise e
        self.mutex_dic[name][0].acquire()
        #Update the lock with thread and time details.
        # Now the mutex dictionary element will be
        #  {'lock_name' : [lock_obj, thread_name, lock_time}
        thread_name = current_thread().getName()
        lock_time = time()
        self.mutex_dic[name] = [self.mutex_dic[name][0],thread_name, lock_time]

    def mutex_unlock(self, name):
        if not name in self.mutex_dic:
            self.nv_log_handler.error("Cannot unlock non-existent lock %s"
                                      % name)
            return
        if len(self.mutex_dic[name]) == 3:
            self.mutex_dic[name][1] = self.mutex_dic[name][2] = 0
        self.mutex_dic[name][0].release()

    def is_mutex_locked(self, name):
        if not name in self.mutex_dic:
            self.nv_log_handler.error("Cannot check status of non-existent lock"
                                      % name)
            return
        self.mutex_dic[name][0].locked()

    def get_mutex_lock_dic(self):
        '''
        Function that return all the created mutex locks. The dictionary is
        very dynamic and can change at run time. This function doesnt gurantee
        the return value is valid for all the time.
        '''
        return self.mutex_dic

    def rlock_acquire(self, name):
        '''
        Acquire a rlock, caller can acquire this lock as many times it wanted to.
        Need to release equal to number of locks.
        '''
        if not name in self.rlock_dic:
            try:
                self.rlock_dic[name] = [RLock()]
            except Exception as e:
                self.nv_log_handler.error("Failed to acquire Rlock : %s" % name)
                del self.rlock_dic[name]
                raise e
        #Update the rlock with thread and time details.
        # Now the mutex dictionary element will be
        #  {'lock_name' : [lock_obj, thread_name, lock_time}
        self.rlock_dic[name][0].acquire()
        thread_name = current_thread().getName()
        lock_time = time()
        self.rlock_dic[name] = [self.rlock_dic[name][0], thread_name, lock_time]

    def rlock_release(self, name):
        '''
        Release the acquired rlock after use. If caller acquired the lock more
        than once, it necessary to release it that many times.
        '''
        if not name in self.rlock_dic:
            self.nv_log_handler.error("Cannot release a non-existent lock %s"
                                      % name)
            return
        if len(self.rlock_dic[name]) == 3:
            self.rlock_dic[name][1] = self.rlock_dic[name][2] = 0
        self.rlock_dic[name][0].release()

    def get_rlock_dic(self):
        '''
        Function to return all the created rlock objects in a dictionary format.
        This dictionary is valid only at the time of function execution. Other
        threads might change it when using the values in dictionary
        '''
        return self.rlock_dic

GBL_NV_SYNC_OBJ = nv_sync_lib()

# The cmd execution queue used to run the commands to middlebox.
# Main thread polls this queue all the time to execute operation in middlebox.
GBL_CONF_QUEUE = nv_sync_queue(q_name="cmd_queue")

