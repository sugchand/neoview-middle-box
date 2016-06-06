#! /usr/bin/python
# -*- coding: utf8 -*-
# The logger module for nv-middlebox. 
#
# Every file must use logger module to log the information.
import logging
log_level = logging.INFO
nv_log_file = '/usr/local/var/log/nv-middlebox/nv_logger.log'

class nv_logger():
    '''
    Wrapper class for the neoview middle box software. Make use the wrapper
    class than calling the logger directly
    '''
    nv_log_obj = None

    def __init__(self):
        self.nv_log_obj = logging.getLogger()
        self.nv_log_obj.setLevel(log_level)
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - '
                                       '%(funcName)s - %(message)s')
        log_fh = logging.FileHandler(nv_log_file)
        log_fh.setLevel(log_level)
        log_fh.setFormatter(log_format)
        self.nv_log_obj.addHandler(log_fh)

        log_ch = logging.StreamHandler()
        log_ch.setLevel(log_level)
        log_ch.setFormatter(log_format)
        self.nv_log_obj.addHandler(log_ch)

    def get_logger(self):
        return self.nv_log_obj

nv_log_handler = nv_logger().get_logger()
