#! /usr/bin/python3
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import platform
from daemonize import Daemonize
import sys
import os


curr_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.abspath(os.path.join(curr_dir, os.pardir)))

from src.nv_logger import nv_logger,default_nv_log_handler
from src.nvdb.nvdb_manager import db_mgr_obj
# Import all the configuration values
from src.settings import NV_MID_BOX_APP_NAME, NV_MID_BOX_PID
from src.nvrelay.relay_handler import relay_main
from src.nv_middlebox_cli import nv_middlebox_cli
from src.nv_lib.nv_os_lib import nv_os_lib

class nv_middlebox():
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.nv_relay_mgr =  None # Thread to copy files to dst webserver
        self.nv_cli_mgr = None # Cli thread to read user inputs.
        self.os_context = nv_os_lib()
        pid_dir = os.path.dirname(os.path.realpath(NV_MID_BOX_PID))
        self.os_context.make_dir(pid_dir)

    def init_db(self):
        self.nv_log_handler.info("Initilizing the middlebox DB")
        db_mgr_obj.setup_session()

    def run(self):
        try:
            self.nv_log_handler.info("starting the middlebox")
            self.init_db()
            self.nv_relay_mgr = relay_main()
            self.nv_relay_mgr.process_relay()
            self.nv_cli_mgr = nv_middlebox_cli()
            self.nv_cli_mgr.start()
        except KeyboardInterrupt:
            self.nv_cli_mgr.stop()
            self.nv_relay_mgr.stop()
        else:
            self.nv_cli_mgr.join()
            self.nv_relay_mgr.relay_join()

if __name__ == "__main__":
    if platform.system() != 'Linux':
        default_nv_log_handler.error("Neoview Middlebox works only on Linux " +
                                     "platform")
        exit(1)
    nv_mid_obj = nv_middlebox()
    nv_daemon = Daemonize(app = NV_MID_BOX_APP_NAME, pid = NV_MID_BOX_PID,
                         action = nv_mid_obj.run,
                         logger = nv_mid_obj.nv_log_handler,
                         foreground = True)
    try:
        nv_daemon.start()
    except KeyboardInterrupt:
        nv_daemon.stop()
    else:
        nv_daemon.join()