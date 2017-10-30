#! /usr/bin/python3
# -*- coding: utf8 -*-
# The logger module for nv-middlebox. 
#
# Every file must use logger module to log the information.
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import logging
from src.settings import NV_DEFAULT_LOG_LEVEL, NV_LOG_FILE, NV_LOG_FORMAT, \
                    NVDB_LOG_FORMAT, NVDB_DEFAULT_LOG_LEVEL, NVDB_LOG_FILE, \
                    NV_CONSOLE_LOG

class nv_logger():
    '''
    Wrapper class for the neoview middle box logging. Make use the wrapper
    class than calling the logger directly
    '''
    nv_log_obj = None

    def __init__(self, class_name = ""):
        self.nv_log_obj = logging.getLogger(class_name)
        self.nv_log_obj.setLevel(NV_DEFAULT_LOG_LEVEL)
        log_format = logging.Formatter(NV_LOG_FORMAT)
        log_fh = logging.FileHandler(NV_LOG_FILE)
        log_fh.setLevel(NV_DEFAULT_LOG_LEVEL)
        log_fh.setFormatter(log_format)
        self.nv_log_obj.addHandler(log_fh)
        # Propogate the log to the upper layer , i.e stdout
        self.nv_log_obj.propagate = NV_CONSOLE_LOG



    def get_logger(self):
        return self.nv_log_obj

class nvdb_logger():
    nvdb_log_obj = None

    def __init__(self):
        logging.basicConfig()
        self.nvdb_log_obj = logging.getLogger('sqlalchemy')
        nvdb_log_format = logging.Formatter(NVDB_LOG_FORMAT)
        nvdb_log_fh = logging.FileHandler(NVDB_LOG_FILE)
        nvdb_log_fh.setLevel(NVDB_DEFAULT_LOG_LEVEL)
        nvdb_log_fh.setFormatter(nvdb_log_format)
        self.nvdb_log_obj.addHandler(nvdb_log_fh)

    def get_logger(self):
        return self.nvdb_log_obj

nvdb_log_handler = nvdb_logger().get_logger()
default_nv_log_handler = nv_logger(__name__).get_logger()
