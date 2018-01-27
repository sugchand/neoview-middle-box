#! /usr/bin/python3
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from src.nv_lib.nv_time_lib import nv_time
from src.nv_logger import default_nv_log_handler

class nv_logger_rl():

    def __init__(self, nv_log_obj = None, timeout = 60):
        '''
            logger module with rate limit support. the timout value decide
            the frequency of logs from a module. By default the rate is set to
            1 log message for every 60 sec
        ''' 
        if not nv_log_obj:
            nv_log_obj = default_nv_log_handler
        self.nv_log_obj = nv_log_obj
        self.rate_timer = nv_time(timeout)
        self.ratelimit_drop_cnt = 0

    def debug_rl(self, msg, *args, **kwargs):
        if self.rate_timer.is_time_elpased():
            if self.ratelimit_drop_cnt:
                self.nv_log_obj.debug("%d messages are dropped due to "
                                        "high rate"% self.ratelimit_drop_cnt)
                self.ratelimit_drop_cnt = 0
            self.nv_log_obj.debug(msg, *args, **kwargs)
            self.rate_timer.update_time()
            
        else:
            #High message rate. Just drop and increase the counter.
            self.ratelimit_drop_cnt += 1

    def info_rl(self, msg, *args, **kwargs):
        if self.rate_timer.is_time_elpased():
            if self.ratelimit_drop_cnt:
                self.nv_log_obj.info("%d messages are dropped due to "
                                        "high rate"% self.ratelimit_drop_cnt)
                self.ratelimit_drop_cnt = 0
            self.nv_log_obj.info(msg, *args, **kwargs)
            self.rate_timer.update_time()
        else:
            self.ratelimit_drop_cnt += 1

    def error_rl(self, msg, *args, **kwargs):
        if self.rate_timer.is_time_elpased():
            if self.ratelimit_drop_cnt:
                self.nv_log_obj.info("%d messages are dropped due to "
                                        "high rate"% self.ratelimit_drop_cnt)
                self.ratelimit_drop_cnt = 0
            self.nv_log_obj.error(msg, *args, **kwargs)
            self.rate_timer.update_time()
        else:
            self.ratelimit_drop_cnt += 1