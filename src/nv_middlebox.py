#! /usr/bin/python
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import platform
from nv_logger import nv_log_handler
from daemonize import Daemonize
from time import sleep

nv_middlebox_pid = "/usr/local/var/run/nv-middlebox/nv_middlebox.pid"

class nv_middlebox():
        def __init__(self):
            pass

        def run(self):
            nv_log_handler.info("starting the middlebox")
            while True:
                nv_log_handler.info("In loop")
                sleep(10)

if __name__ == "__main__":
    if platform.system() != 'Linux':
        nv_log_handler.error("Neoview Middlebox works only on Linux platform")
        exit(1)
    nv_mid_obj = nv_middlebox()
    nv_daemon = Daemonize(app="nv-middle-box", pid=nv_middlebox_pid,
                          action=nv_mid_obj.run, logger=nv_log_handler,
                          foreground=True)
    nv_daemon.start()