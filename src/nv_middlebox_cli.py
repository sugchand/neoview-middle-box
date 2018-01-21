#! /usr/bin/python3
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import threading
import ipaddress
import socket
import struct
from getpass import getpass

from src.nv_logger import nv_logger
from src.nvdb.nvdb_manager import db_mgr_obj, nv_midbox_system, enum_camStatus,\
    nv_webserver_system
from src.nvdb.nvdb_manager import nv_camera
from src.nv_lib.ipc_data_obj import webserver_data, exitSys_data,camera_data, enum_ipcOpCode
from src.nv_lib.nv_sync_lib import GBL_CONF_QUEUE
from src.nv_exception import midboxExitException

try:
    from termcolor import colored
except ImportError:
    raise ImportError('Install colored by \"sudo pip3 install termcolor\"')

NV_MIDBOX_CLI_FNS = {
                "ADD-CAMERA" : "nv_midbox_add_camera",
                "DELETE-CAMERA" : "nv_midbox_del_camera",
                "START-CAMERA-STREAM" : "nv_midbox_start_stream",
                "START-ALL-CAMERA-STREAMS" : "nv_midbox_start_all_stream",
                "STOP-CAMERA-STREAM" : "nv_midbox_stop_stream",
                "STOP-ALL-CAMERA-STREAMS" : "nv_midbox_stop_all_stream",
                "LIST-ALL-CAMERAS" : "nv_midbox_list_cameras",
                "LIST-SYSTEM" : "list_midbox_system",
                "ADD-WEBSERVER" : "add_nv_webserver",
                "DEL-WEBSERVER" : "del_nv_webserver",
                "QUIT-MIDBOX" : "nv_midbox_stop"
                    }

def print_color_string(s, color='white'):
    print("\n%s" %(colored(s, color, attrs = ['bold'])))

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
        for i, (key, _) in enumerate(NV_MIDBOX_CLI_FNS.items()):
            print_color_string(str(i) + " : " + key, color="cyan")
        choice = (input("Enter your choice[0-%d] : " %i))

        if choice == "":
            print_color_string("Invalid Choice, Exiting...", color = "red")
            return 0

        try:
            choice = int(choice)
        except ValueError:
            print_color_string("Invalid Choice, Exiting", color = "red")
            return 0
        if choice < 0 or choice > i:
            print_color_string("Invalid Choice, Exiting...", color = "red")
            return 0

        try:
            fn = list(NV_MIDBOX_CLI_FNS.values())[choice]
            fn = "self." + fn
            eval(fn)()
        except midboxExitException:
            raise
        except Exception as e:
            self.nv_log_handler.error("Exception in CLI while running command"
                                      "%s", e)
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
            except midboxExitException:
                break
            except:
                raise

    def add_nv_webserver(self):
        srv_name = input("Enter webserver Name/IP(dafult = localhost) : ")
        uname = 'root'
        pwd = 'root'
        if not srv_name or srv_name is 'localhost' or srv_name is '127.0.0.1':
            srv_name = 'localhost'
        else:
            # The username and password needed only when webserver is remote.
            uname = input("User Name(default = root) : ")
            if not uname:
                uname = 'root'
            pwd = getpass(prompt = "Password(default = root) : ")
            if not pwd:
                pwd = 'root'
        srv_path = input("Enter webserver video path(default = /tmp): ")
        if not srv_path:
            srv_path = '/tmp/'
        try:
            ws_data = webserver_data(op = enum_ipcOpCode.CONST_ADD_WEBSERVER_OP,
                                     name=srv_name, videopath=srv_path,
                                     uname = uname, pwd = pwd)
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1,
                                    obj_value = [ws_data])
        except:
            self.nv_log_handler.error("Failed to configure the webserver")

    def del_nv_webserver(self):
        try:
            ws_data = webserver_data(op = enum_ipcOpCode.CONST_DEL_WEBSERVER_OP,
                                     name = None,
                                     videopath = None,
                                     uname = None,
                                     pwd = None)
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1,
                                    obj_value = [ws_data])
        except:
            self.nv_log_handler.error("Failed to delete the webserver")

    def nv_midbox_stop(self):
        exit_data = exitSys_data()
        try:
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1, obj_value = [exit_data])
        except Exception as e:
            self.nv_log_handler.error("Failed to send stop signal..%s", e)
        finally:
            raise midboxExitException

    def is_camera_rtsp_stream_valid(self, ip_addr, port, uname, pwd):
        '''
        Check to see if camera can respond for RTSP request. Returns True if
        camera can support RTSP, False otherwise.
        All the function parameters are string type.
        '''
        req = "DESCRIBE rtsp//" + uname + ":" + pwd + "@" +\
              ip_addr + ":" + port +\
              " RTSP/1.0\r\nCSeq: 2\r\nAuthorization: Basic YWRtaW46c3VndSZkZWVwdQ==\r\n\r\n"
        byte_req = req.encode()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((ip_addr, int(port)))
            s.sendall(byte_req)
            data = s.recv(200)
            s.close()
            data = data.decode("utf-8")
            if "200 OK" in data:
                return True
        except Exception as e:
            self.nv_log_handler.error("Failed to make rtsp connection to camera"
                                      " : %s" % e)
        self.nv_log_handler.info("RTSP is not supported by the camera"
                                        "camera response : %s", data)
        return False

    def validate_cam_details(self, name, ip_addr, mac_addr, port, uname, pwd):
        '''
        Validate the camera details are right before configuring it.
        Return true if all the details are right. False otherwise.
        All the function parameters are string type.
        '''
        db_mgr_obj.db_start_transaction()
        cam_records = db_mgr_obj.get_tbl_records(nv_camera)
        db_mgr_obj.db_end_transaction()
        for cam_record in cam_records:
            if cam_record.name == name:
                self.nv_log_handler.error("Cannot add camera, Duplicate name :%s"
                                          ,name)
                return False
            db_ip_addr_str = socket.inet_ntoa(struct.pack('!L',
                                              cam_record.ip_addr))
            if db_ip_addr_str == ip_addr:
                self.nv_log_handler.error("Cannot add camera, Duplicate IP :%s",
                                          ip_addr)
                return False
            if cam_record.mac_addr == mac_addr:
                self.nv_log_handler.error("Cannot add camera '%s' "
                                          "duplicate mac-addr %s",
                                          cam_record.name, mac_addr)
                return False

        if not self.is_camera_rtsp_stream_valid(ip_addr, port, uname, pwd):
            return False
        # Check the camera is serving the rtsp stream or not.
        return True

    def nv_midbox_add_camera(self):
        cam_name = input("Camera Name(default : bed-cam) : ")
        if not cam_name:
            cam_name = 'bed-cam'
        try:
            #ipaddress will throw exception if the input ip is invalid.
            cam_ip_str = input("IP Address : ")
            cam_ip = int(ipaddress.IPv4Address(cam_ip_str))
        except:
            self.nv_log_handler.error("Invalid ip address, cannot add camera,"
                                      " try again with proper ip address")
            return
        cam_mac = input("MAC Address(default : FF:FF:FF:FF:FF:FF) : ")
        if not cam_mac:
            cam_mac = "FF:FF:FF:FF:FF:FF"
        cam_listen_port_str = input("RTSP port(default : 554) : ")
        if not cam_listen_port_str:
            cam_listen_port_str = '554'
            cam_listen_port = 554
        else:
            cam_listen_port = int(cam_listen_port_str)
        cam_uname = input("User name(default : root) : ")
        if not cam_uname:
            cam_uname = 'root'
        cam_pwd = getpass(prompt = "Password(default : root) : ")
        if not cam_pwd:
            cam_pwd = 'root'
        time_len = 60 # Default is 60 seconds.
        desc = input("Description : ")

        if not self.validate_cam_details(cam_name, cam_ip_str, cam_mac,
                                    cam_listen_port_str, cam_uname, cam_pwd):
            self.nv_log_handler.error("Camera credentails are wrong, Please"
                                      " make sure to provide proper camera details")
            return
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

    def nv_midbox_del_camera(self):
        # Pass only the camera name for deleting the camera.
        cam_name = (input("Enter Camera Name: "))
        cam_data = camera_data(op = enum_ipcOpCode.CONST_DEL_CAMERA_OP,
                               name = cam_name,
                               status= None,
                               ip = None,
                               macAddr = None,
                               port = None,
                               time_len = None,
                               uname = None,
                               pwd = None,
                               desc = None
                               )
        try:
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1, obj_value = [cam_data])
        except Exception as e:
            self.nv_log_handler.error("Failed to delete the camera at cli %s",
                                      e)

    def nv_midbox_start_stream(self):
        cam_name = (input("Enter Camera Name: "))
        filter_arg = {'name' : cam_name}
        db_mgr_obj.db_start_transaction()
        cam_cnt = db_mgr_obj.get_tbl_records_filterby_cnt(nv_camera, filter_arg)
        db_mgr_obj.db_end_transaction()
        if cam_cnt == 0:
            self.nv_log_handler.error("No record found with given name %s"
                                      % cam_name)
            return
        if cam_cnt > 1:
            self.nv_log_handler.error("Exiting, More than one record found"
                                      " with same name %s" % cam_name)
            return
        db_mgr_obj.db_start_transaction()
        cam_record = db_mgr_obj.get_tbl_records_filterby(nv_camera, filter_arg)[0]
        db_mgr_obj.db_end_transaction()
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
            self.nv_log_handler.error("Failed to start the camera at cli, %s", e)

    def nv_midbox_start_all_stream(self):
        '''
        Start all the available cameras in the system
        '''
        db_mgr_obj.db_start_transaction()
        cam_records = db_mgr_obj.get_tbl_records(nv_camera)
        db_mgr_obj.db_end_transaction()
        for cam_record in cam_records:
            cam_ipcData = camera_data(
                                op = enum_ipcOpCode.CONST_START_CAMERA_STREAM_OP,
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
                GBL_CONF_QUEUE.enqueue_data(obj_len = 1,
                                            obj_value = [cam_ipcData])
            except Exception as e:
                self.nv_log_handler.error("Failed to start the camera at "
                                          "cli, %s", e)

    def nv_midbox_stop_stream(self):
        cam_name = input("Enter camera Name: ")
        if cam_name is None:
            return
        filter_arg = {'name' : cam_name}
        db_mgr_obj.db_start_transaction()
        cam_cnt = db_mgr_obj.get_tbl_records_filterby_cnt(nv_camera, filter_arg)
        db_mgr_obj.db_end_transaction()
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

    def nv_midbox_stop_all_stream(self):
        db_mgr_obj.db_start_transaction()
        cam_records = db_mgr_obj.get_tbl_records(nv_camera)
        db_mgr_obj.db_end_transaction()
        for cam_record in cam_records:
            cam_name = cam_record.name
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
                GBL_CONF_QUEUE.enqueue_data(obj_len = 1,
                                            obj_value = [cam_ipcData])
            except Exception as e:
                self.nv_log_handler.error("Failed to stop the camera at cli,"
                                          " %s", e)

    def list_midbox_system(self):
        try:
            db_mgr_obj.db_start_transaction()
            self.nv_log_handler.debug("Listing system & webserver details "
                                      "from DB")
            if not db_mgr_obj.get_tbl_record_cnt(nv_midbox_system):
                print_color_string("No record found in system table",
                                   color='red')
                self.nv_log_handler.debug("Empty system table in the DB")
                return
            sys_record = db_mgr_obj.get_tbl_records(nv_midbox_system)
            print_color_string(sys_record, color = "green")
            if not db_mgr_obj.get_tbl_record_cnt(nv_webserver_system):
                self.nv_log_handler.debug("Empty webserver table in the system")
                return
            web_records = db_mgr_obj.get_tbl_records(nv_webserver_system)
            print_color_string(web_records, color = "blue")
        except Exception as e:
            self.nv_log_handler.info("Failed to list the midbox system :%s", e)
        finally:
            db_mgr_obj.db_end_transaction()

    def nv_midbox_list_cameras(self):
        try:
            db_mgr_obj.db_start_transaction()
            if not db_mgr_obj.get_tbl_record_cnt(nv_camera):
                print_color_string("No camera record found in the system",
                                   color='red')
                self.nv_log_handler.debug("Camera table empty in the system")
                return
            cam_records = db_mgr_obj.get_tbl_records(nv_camera)
            print_color_string(cam_records, color = "green")
            self.nv_log_handler.debug("Listing all the cameras in the DB")
        except Exception as e:
            self.nv_log_handler.info("Failed to list cameras : %s", e)
        finally:
            db_mgr_obj.db_end_transaction()
