#! /usr/bin/python
# -*- coding: utf8 -*-
# The global setting file for nv-middlebox.

__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import logging

#nv-middle-box common settings
NV_MID_BOX_APP_NAME = "nv-middle-box"
NV_MID_BOX_RUN_DIR = "/usr/local/var/run/nv-middlebox/"
# Middlebox PID for the daemon.
NV_MID_BOX_PID = "/usr/local/var/run/nv-middlebox/nv_middlebox.pid"


# nv-middle-box logging Settings
NV_DEFAULT_LOG_LEVEL = logging.INFO
NV_LOG_FILE = "/usr/local/var/log/nv-middlebox/nv_logger.log"
NV_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(funcName)s - %(message)s"