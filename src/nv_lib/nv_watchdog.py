#! /usr/bin/python3
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import copy
from time import time
import threading
from threading import Event
from time import sleep
from src.nv_logger import nv_logger
from src.nv_logger_rl import nv_logger_rl
from src.nv_lib.nv_sync_lib import GBL_NV_SYNC_OBJ

class nv_watchdog(threading.Thread):
    '''
    A watchdog is a thread to monitor various middlebox worker threads. All the
    threads uses various locks to synchronize the resource usage in different
    places.
    Watchdog thread keep track of these locks with a timeout to see if any of
    threads holding the locks longer than it supposed to.
    NOTE :: DO NOT USE ANY LOCKS OR ANY SYNC PRIMITIVES in WATCHDOG.
    WATCHDOG IS NOT SUPPOSED TO BE BLOCKED IN THE SYSTEM.
    '''

    WATCHDOG_TIMEOUT = 5
    def __init__(self):
        self.nv_log_handler = \
            nv_logger(self.__class__.__name__).get_logger()
        self.nv_log_handler_rl = \
            nv_logger_rl(nv_log_obj = self.nv_log_handler, timeout = 15)
        self.cam_stream_stop_event = Event()
        threading.Thread.__init__(self, None, None, "nv_watchdog",
                                  args=(self.cam_stream_stop_event,))
        self.daemon = True

    def run(self):
        self.start_watchdog(self.cam_stream_stop_event)

    def check_mutex_locks(self):
        current_time = time()
        mutex_dic = GBL_NV_SYNC_OBJ.get_mutex_lock_dic().copy()
        for lock_name, lockobj_list in mutex_dic.items():
            if type(lockobj_list) is not list or len(lockobj_list) != 3 \
                or lockobj_list[2] == 0:
                # Do not check if time is not present in lock, or lock is not
                # in use.
                continue

            time_elapsed = current_time - lockobj_list[2]
            if time_elapsed > self.WATCHDOG_TIMEOUT:
                self.nv_log_handler_rl.info_rl("mutex %s is in use for more than %d"
                                         " sec, thread %s is coalesced..",
                                         lock_name, time_elapsed,
                                         lockobj_list[1])

    def check_rlocks(self):
        current_time = time()
        rlock_dic = GBL_NV_SYNC_OBJ.get_rlock_dic().copy()
        for lock_name, lockobj_list in rlock_dic.items():
            if type(lockobj_list) is not list or len(lockobj_list) != 3 \
               or lockobj_list[2] == 0:
                # Do not check if time is not present in lock, or lock is not
                # in use.
                continue
            time_elapsed = current_time - lockobj_list[2]
            if time_elapsed > self.WATCHDOG_TIMEOUT:
                self.nv_log_handler_rl.info_rl("rlock %s is in use for more than %d"
                                        "sec, thread %s is coalesced..",
                                        lock_name, time_elapsed,
                                        lockobj_list[1])

    def start_watchdog(self, stop_event):
        self.nv_log_handler.info("Starting the watchdog thread")
        while not stop_event.is_set():
            sleep(1)
            self.check_mutex_locks()
            self.check_rlocks()

    def stop_watchdog(self):
        self.cam_stream_stop_event.set()
        self.nv_log_handler.info("Stopping the watchdog thread.")
