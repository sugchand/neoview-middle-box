#! /usr/bin/python3
# -*- coding: utf8 -*-
# The time module for the middlebox.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"
import time
import random
import string
from src.nv_lib.nv_sync_lib import GBL_NV_SYNC_OBJ

class nv_time():
    def __init__(self, timeout=None):
        '''
        Initilize the time obj to use in modules.
        The time module is thread safe. can use in multi threaded model.
        @param timeout : the timeout period of this object.
        ''' 
        self.start_time = time.time()
        self.timeout = timeout
        self.name = ''.join(random.choice(string.ascii_uppercase ) \
                            for _ in range(25))
        self.CONST_MUTEX_NAME = self.name
        pass

    def get_time(self):
        return self.start_time

    def get_objName(self):
        return self.name

    def update_time(self, new_time=None):
        '''
        Update the time stored in the object.
        @param new_time: the time value to update with
        '''
        GBL_NV_SYNC_OBJ.mutex_lock(self.CONST_MUTEX_NAME) 
        if new_time:
            self.start_time = new_time
        else:
            self.start_time = time.time()
        GBL_NV_SYNC_OBJ.mutex_unlock(self.CONST_MUTEX_NAME)

    def is_time_elpased(self):
        '''
        Validate for the timeout of the obj.
        @return True: if obj is already timedout.
                False : if not timedout.
        '''
        elpsed_time = time.time() - self.start_time
        if elpsed_time > self.timeout:
            return True
        return False

    def update_on_valid_time(self, new_time=None):
        '''
        Validate for the timeout first and update the time obj only if time is
        not elapsed
        @param: new_time : the time value to update with.
        @return: True : if time is valid/time is not elapsed
                 False: Time is elapsed and didnt update the time object.
        '''
        if self.is_time_elpased():
            return False
        self.update_time(new_time=new_time)
        return True