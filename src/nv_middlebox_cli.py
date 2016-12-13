#! /usr/bin/python3
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import threading
import uuid
from time import sleep
import sys
import ipaddress
from src.nvcamera.thread_manager import thread_manager
from src.nv_logger import nv_logger
from src.nvdb.nvdb_manager import db_mgr_obj, nv_midbox_system, enum_camStatus, nv_webserver_system
from src.nvdb.nvdb_manager import nv_camera
from src.nvrelay.relay_handler import relay_main
from src.nv_lib.ipc_data_obj import webserver_data, enum_ipcType, exitSys_data,camera_data, enum_ipcOpCode
from src.nv_lib.nv_sync_lib import GBL_CONF_QUEUE

try:
    from termcolor import colored
except ImportError:
    raise ImportError('Install colored by \"sudo pip3 install termcolor\"')

NV_MIDBOX_CLI_FNS = {
                "ADD-CAMERA" : "nv_midbox_add_camera",
                "DELETE-CAMERA" : "nv_midbox_del_camera",
                "START-CAMERA-STREAM" : "nv_midbox_start_stream",
                "STOP-CAMERA-STREAM" : "nv_midbox_stop_stream",
                "LIST-ALL-CAMERAS" : "nv_midbox_list_cameras",
                "LIST-SYSTEM" : "list_midbox_system",
                "ADD-WEBSERVER" : "add_nv_webserver",
                "QUIT-MIDBOX" : "nv_midbox_stop"
                    }

def print_color_string(s, color='white'):
    print("%s" %(colored(s, color, attrs = ['bold'])))

class nv_middlebox_cli(threading.Thread):
    '''
    Thread to run the cli option functions. All CLI user interaction handled
    by this thread
    '''
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        threading.Thread.__init__(self, None, None, "nv_midbox_cli")
        self.daemon = True # Kill the cli thread when main thread exits.

    def run(self):
        self.nv_middlebox_cli_main()

    def stop(self):
        # Do nothing to stop the thread as its a daemon, get closed by itself
        # when main thread stops.
        self.nv_log_handler.debug("Exiting the nv_midbox cli thread.")

    def do_execute_nv_midbox_cli(self):
        for i, (key, value) in enumerate(NV_MIDBOX_CLI_FNS.items()):
            print_color_string(str(i) + " : " + key, color="cyan")
        choice = (input("Enter your choice[0-%d] : " %i))

        if choice == "":
            print_color_string("Invalid Choice, Exiting...", color = "red")
            return 0

        choice = int(choice)
        if choice < 0 or choice > i:
            print_color_string("Invalid Choice, Exiting...", color = "red")
            return 0

        fn = list(NV_MIDBOX_CLI_FNS.values())[choice]
        fn = "self." + fn
        eval(fn)()
        return 0

    def nv_middlebox_cli_main(self):
        print_color_string("** NOTE :: THE MIDDLE BOX MACHINE SETTING MUST BE SET "
                           "BEFORE RUNNING ANY COMMAND BELOW **", color = "red")
        while(1):
            try:
                self.do_execute_nv_midbox_cli()
            except KeyboardInterrupt:
                self.nv_midbox_stop()
                break

    def add_nv_webserver(self):
        srv_name = input("Enter webserver Name: ")
        if not srv_name:
            srv_name = 'localhost'
        srv_path = input("Enter webserver video path(default = /tmp): ")
        if not srv_path:
            srv_path = '/tmp/'
        try:
            ws_data = webserver_data(op = enum_ipcOpCode.CONST_ADD_WEBSERVER_OP,
                                     name=srv_name, videopath=srv_path)
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1,
                                    obj_value = [ws_data])
        except:
            self.nv_log_handler.error("Failed to configure the webserver")

    def nv_midbox_stop(self):
        exit_data = exitSys_data()
        try:
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1, obj_value = [exit_data])
        except Exception as e:
            self.nv_log_handler.error("Failed to send stop signal..%s", e)

    def nv_midbox_add_camera(self):
        # TODO :: Validate user inputs for right input data,
        #cam_name = (input("Enter Camera Name: "))
        #cam_ip = (input("Enter Camera IP Address: "))
        #cam_mac = (input("Enter Camera MAC Address: "))
        #cam_listen_port = (input("Enter Camera Listen port: "))
        #cam_uname = (input("Enter Camera User name: "))
        #cam_pwd = (input("Enter Camera password: "))
        ### TODO ::: STATIV values , remove it #####
        cam_name = 'camera-1'
        cam_ip = int(ipaddress.IPv4Address('192.168.192.32'))
        cam_mac = "00:00:00:00:00:01"
        cam_listen_port = 554
        time_len = 60
        cam_uname = 'admin'
        cam_pwd = 'sugu&deepu'
        desc = "Camera 1 at test"
        #########################
        cam_data = camera_data(op = enum_ipcOpCode.CONST_ADD_CAMERA_OP,
                               name = cam_name,
                               status = enum_camStatus.CONST_CAMERA_NEW,
                               ip = cam_ip,
                               macAddr = cam_mac,
                               port = cam_listen_port,
                               time_len = time_len,
                               uname = cam_uname,
                               pwd = cam_pwd,
                               desc = desc 
                               )
        try:
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1, obj_value = [cam_data])
        except Exception as e:
            self.nv_log_handler.error("Failed to add the camera at cli, %s", e)

    def nv_midbox_start_stream(self):
        # TODO :: Validate the camera name
        cam_name = (input("Enter Camera Name: "))
        filter_arg = {'name' : cam_name}
        cam_cnt = db_mgr_obj.get_tbl_records_filterby_cnt(nv_camera, filter_arg)
        if cam_cnt == 0:
            self.nv_log_handler.error("No record found with given name %s"
                                      % cam_name)
            return
        if cam_cnt > 1:
            self.nv_log_handler.error("Exiting, More than one record found"
                                      " with same name %s" % cam_name)
            return
        cam_record = db_mgr_obj.get_tbl_records_filterby(nv_camera, filter_arg)[0]
        # XXX :: No need to send out all the camera details to start stream,only
        # name will be enough. But nothing harm to send everything. so sending
        # out for integrity.
        cam_ipcData = camera_data(op = enum_ipcOpCode.CONST_START_CAMERA_STREAM_OP,
                                name = cam_record.name,
                                status = cam_record.status,
                                ip = cam_record.ip_addr,
                                macAddr = cam_record.mac_addr,
                                port = cam_record.listen_port,
                                time_len = cam_record.stream_file_time_sec,
                                uname = cam_record.username,
                                pwd = cam_record.password,
                                desc = cam_record.desc
                                )
        try:
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1, obj_value = [cam_ipcData])
        except Exception as e:
            self.nv_log_handler.error("Failed to add the camera at cli, %s", e)

    def nv_midbox_stop_stream(self):
        cam_name = input("Enter camera Name: ")
        if cam_name is None:
            return
        filter_arg = {'name' : cam_name}
        cam_cnt = db_mgr_obj.get_tbl_records_filterby_cnt(nv_camera, filter_arg)
        if cam_cnt == 0:
            self.nv_log_handler.error("No record found with given name %s"
                                      % cam_name)
            return
        if cam_cnt > 1:
            self.nv_log_handler.error("Exiting, More than one record found"
                                      " with same name %s" % cam_name)
            return
        cam_ipcData = camera_data(op = enum_ipcOpCode.CONST_STOP_CAMERA_STREAM_OP,
                                  name = cam_name,
                                  # Everything else is None
                                  status = None,
                                  ip = None,
                                  macAddr = None,
                                  port = None,
                                  time_len = None,
                                  uname = None,
                                  pwd =  None,
                                  desc = None
                                  )
        try:
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1, obj_value = [cam_ipcData])
        except Exception as e:
            self.nv_log_handler.error("Failed to stop the camera at cli, %s", e)

class nv_middlebox_conf():
    NV_MIDBOX_CONF_FNS = {
                        enum_ipcType.CONST_WEBSERVER_OBJ : "do_webserver_op",
                        enum_ipcType.CONST_CAMERA_OBJ : "do_camera_op",
                        enum_ipcType.CONST_QUIT_MIDBOX : "nv_midbox_stop"
                          }

    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.cam_thread_mgr = thread_manager()
        try:
            self.nv_relay_mgr = relay_main()
            self.nv_relay_mgr.process_relay()
            self.nv_midbox_cli = nv_middlebox_cli()
            self.nv_midbox_cli.start()
        except:
            self.nv_log_handler.error("Unknown exception while starting"
                                      " the middlebox")
            self.exit_all_threads()


    def exit_all_threads(self):
        '''
        Function to stop all the threads that are started by the midbox conf.
        cli, relay manager and all camera threads are stopped.
        '''
        self.nv_midbox_cli.stop()
        self.nv_relay_mgr.relay_stop()
        self.nv_relay_mgr.relay_join()
        self.cam_thread_mgr.stop_all_camera_threads()
        self.cam_thread_mgr.join_all_camera_threads()

    def do_midbox_conf(self):
        '''
        Read the conf queue in fixed time interval to configure the middlebox.
        '''
        while(1):
            try:
                conf_obj = GBL_CONF_QUEUE.dequeue_data()
                if conf_obj is None:
                    # The queue is empty, nothing to configure.
                    sleep(5)
                    continue
                obj_list = conf_obj["value"]
                for obj in obj_list:
                    choice = obj.get_ipc_datatype()
                    if choice not in nv_middlebox_conf.NV_MIDBOX_CONF_FNS:
                        self.nv_log_handler.error("Cannot execute the %d conf"
                                " type", choice)
                        continue
                    if not obj.is_ipc_op_valid():
                        self.nv_log_handler.error("Cannot execute an invalid"
                                                  "operation")
                        continue
                    fn = nv_middlebox_conf.NV_MIDBOX_CONF_FNS[choice]
                    fn = "self." + fn
                    eval(fn)(obj)
            except SystemExit:
                sys.exit()
            except Exception as e:
                self.nv_log_handler.error("Exception in main thread %s", e)
                sys.exit()

    def do_conf_op(self, op, op_fn_dic, conf_obj):
        if op not in op_fn_dic:
            self.nv_log_handler.error("Invalid op %d, cannot execute", op)
            return
        fn = "self." + op_fn_dic[op]
        eval(fn)(conf_obj)

    def do_webserver_op(self, conf_obj):
        WS_OP_FNS = {
                    enum_ipcOpCode.CONST_ADD_WEBSERVER_OP : "add_nv_webserver",
                    enum_ipcOpCode.CONST_DEL_WEBSERVER_OP : "del_nv_webserver"
                     }
        op = conf_obj.get_ipc_op()
        self.do_conf_op(op, WS_OP_FNS, conf_obj)

    def add_nv_webserver(self, conf_obj):
        srv_name = conf_obj.name
        if not srv_name:
            srv_name = 'localhost'
        srv_path = conf_obj.videopath
        if not srv_path:
            srv_path = '/tmp/'
        wbsrv_entry = nv_webserver_system(name = srv_name,
                                    server_id = (uuid.uuid4().int>>64)
                                                & 0xFFFFFFFF,
                                    video_path = srv_path)
        db_mgr_obj.init_webserver_params(wbsrv_entry)

    def del_nv_webserver(self, conf_obj):
        db_mgr_obj.del_webserver()

    def do_camera_op(self, conf_obj):
        CAM_OP_FNS = {
                enum_ipcOpCode.CONST_ADD_CAMERA_OP : "nv_midbox_add_camera",
                enum_ipcOpCode.CONST_DEL_CAMERA_OP : "nv_midbox_del_camera",
                enum_ipcOpCode.CONST_START_CAMERA_STREAM_OP : "nv_midbox_start_stream",
                enum_ipcOpCode.CONST_STOP_CAMERA_STREAM_OP : "nv_midbox_stop_stream",
                enum_ipcOpCode.CONST_UPDATE_CAMERA_STATUS : "nv_midbox_cam_status_update"
                      }
        op = conf_obj.get_ipc_op()
        self.do_conf_op(op, CAM_OP_FNS, conf_obj)

    def nv_midbox_add_camera(self, cam_obj):
        nv_midbox_db_entry = db_mgr_obj.get_own_system_record()
        if nv_midbox_db_entry is None:
            self.nv_log_handler.error("System table is not available, "
                                      "Cannot add a Camera")
            return
        cam_name = cam_obj.name
        cam_ip = cam_obj.ip
        cam_mac = cam_obj.macAddr
        cam_listen_port = cam_obj.port
        time_len = cam_obj.time_len
        cam_uname = cam_obj.uname
        cam_pwd = cam_obj.pwd
        cam_status = cam_obj.status
        cam_desc = cam_obj.desc

        filter_arg = {'name' : cam_name}
        cam_cnt = db_mgr_obj.get_tbl_records_filterby_cnt(nv_camera, filter_arg)
        if cam_cnt != 0:
            self.nv_log_handler.error("%d camera records are already present"
                                      " Cannot add camera %s", cam_cnt, cam_name)
            return
        if cam_status is not enum_camStatus.CONST_CAMERA_NEW:
            self.nv_log_handler.error("Camera is not in valid state to add"
                                      "Current state is %d",
                                      cam_status)
            return
        # Change the camera status while adding it to the DB.
        try:
            cam_status = enum_camStatus.CONST_CAMERA_READY
            cam_entry = nv_camera(cam_id = (uuid.uuid4().int>>64) & 0xFFFFFFFF,
                               name = cam_name,
                               ip_addr = int(ipaddress.IPv4Address(cam_ip)),
                               mac_addr = cam_mac,
                               listen_port = cam_listen_port,
                               stream_file_time_sec = time_len,
                               username = cam_uname,
                               password = cam_pwd,
                               nv_midbox = nv_midbox_db_entry,
                               status = cam_status,
                               desc = cam_desc
                               )
            db_mgr_obj.add_record(cam_entry)
            db_mgr_obj.db_commit()
            self.nv_log_handler.debug("Added a new camera %s to DB" % cam_name)
        except:
            self.nv_log_handler.error("Unknown error, failed to add camera")

    def nv_midbox_del_camera(self):
        cam_name = "None"
        self.nv_log_handler.debug("Deleted the camera %s from the DB" % cam_name)
        pass

    def nv_midbox_start_stream(self, cam_obj):
        # TODO :: Validate the camera name
        cam_name = cam_obj.name
        filter_arg = {'name' : cam_name}
        cam_cnt = db_mgr_obj.get_tbl_records_filterby_cnt(nv_camera, filter_arg)
        if cam_cnt == 0:
            self.nv_log_handler.error("No record found with given name %s"
                                      % cam_name)
            return
        if cam_cnt > 1:
            self.nv_log_handler.error("Exiting, More than one record found"
                                      " with same name %s" % cam_name)
            return
        cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera, filter_arg)
        if cam_record.status is not enum_camStatus.CONST_CAMERA_READY:
            self.nv_log_handler.error("Cannot start the streaming until the"
                                      " camera is ready, current state is %d",
                                      cam_record.status)
            return
        self.cam_thread_mgr.start_camera_thread(cam_record)
        self.nv_log_handler.debug("staring the stream recording on camera %s"
                                  % cam_name)
        cam_record.status = enum_camStatus.CONST_CAMERA_RECORDING
        db_mgr_obj.db_commit()

    def nv_midbox_stop_stream(self, cam_obj):
        cam_name = cam_obj.name
        filter_arg = {'name' : cam_name}
        cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera, filter_arg)
        if cam_record is None:
            self.nv_log_handler.error("No camera record found for %s", cam_name)
            return
        if cam_record.status is not enum_camStatus.CONST_CAMERA_RECORDING:
            self.nv_log_handler.error("Cannot stop the streaming until the"
                                     " camera is ready, current state is %d",
                                     cam_record.status)
            return
        cam_record.status = enum_camStatus.CONST_CAMERA_DEFERRED
        self.cam_thread_mgr.stop_camera_thread(cam_record.cam_id, None)
        db_mgr_obj.db_commit()
        self.nv_log_handler.debug("Stop streaming on camera %s" %cam_name)

    def nv_midbox_cam_status_update(self, cam_obj):
        '''
        Update the camera status flag in db on request. Possible use cases are
        1) streaming thread killed and ready to start streaming again.
        2) Update from the web interface to update the status
        '''
        cam_name = cam_obj.name
        filter_arg = {'name' : cam_name}
        cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera, filter_arg)
        if cam_record is None:
            self.nv_log_handler.error("No camera record found to change status %s",
                                      cam_name)
            return
        cam_record.status = cam_obj.status
        db_mgr_obj.db_commit()
        self.nv_log_handler.debug("%s camera has new status %d", cam_name,
                                  cam_obj.status)

    def list_midbox_system(self):
        if not db_mgr_obj.get_tbl_record_cnt(nv_midbox_system):
            print_color_string("No record found in system table", color='red')
            self.nv_log_handler.debug("Empty system table in the DB")
            return
        sys_record = db_mgr_obj.get_tbl_records(nv_midbox_system)
        print_color_string(sys_record, color = "green")
        self.nv_log_handler.debug("Listing system details the DB")

    def nv_midbox_list_cameras(self):
        if not db_mgr_obj.get_tbl_record_cnt(nv_camera):
            print_color_string("No camera record found in the system", color='red')
            self.nv_log_handler.debug("Camera table empty in the system")
            return
        cam_records = db_mgr_obj.get_tbl_records(nv_camera)
        print_color_string(cam_records, color = "green")
        self.nv_log_handler.debug("Listing all the cameras in the DB")

    def nv_midbox_stop(self, obj):
        try:
            self.nv_log_handler.info("Quit the middlebox, "
                                  "Waiting for all threads to coalesce...")
            self.exit_all_threads()
            sys.exit()
        except SystemExit as e:
            raise e
        except:
            self.nv_log_handler.error("Unknown error while exiting the middlebox")