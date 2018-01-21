#! /usr/bin/python3
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import uuid
from time import sleep
import sys
import ipaddress
from src.nvcamera.thread_manager import thread_manager
from src.nv_logger import nv_logger
from src.nvdb.nvdb_manager import db_mgr_obj, enum_camStatus, nv_webserver_system
from src.nvdb.nvdb_manager import nv_camera
from src.nvrelay.relay_handler import relay_main
from src.nv_lib.ipc_data_obj import enum_ipcType, enum_ipcOpCode, camera_data
from src.nv_lib.nv_sync_lib import GBL_CONF_QUEUE
from src.nv_middlebox_cli import nv_middlebox_cli
from src.nv_midbox_websock.nv_midbox_wsClient import GBL_WSCLIENT

class nv_midbox_conf():
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
            self.midbox_camera_init()
            self.nv_midbox_cli = nv_middlebox_cli()
            self.nv_midbox_cli.start()
        except Exception as e:
            self.nv_log_handler.error("Unknown exception while starting"
                                      " the middlebox : %s", e)
            self.exit_all_threads()

    def midbox_camera_init(self):
        '''
        When starting middlebox at first time, validate all camera states,
        set them to OFF state unconditionally. start the live stream for each
         ** DO NOT INVOKE THE FUNCTION OTHER THAN AT THE TIME OF INIT **
        '''
        try:
            db_mgr_obj.db_start_transaction()
            cam_records = db_mgr_obj.get_tbl_records(nv_camera)
            for camera in cam_records:
                camera.status = enum_camStatus.CONST_CAMERA_READY
                camera.live_url = None
            db_mgr_obj.db_commit()

            # Populate the webserver if configured.
            db_mgr_obj.get_webserver_record()
        except Exception as e:
            self.nv_log_handler.info("Failed in midbox init : %s", e)
        finally:
            db_mgr_obj.db_end_transaction()

        # start the live stream for all the configured cameras
        for camera in cam_records:
            if not camera.name:
                self.nv_log_handler.error("Cannot start live stream for"
                                          " non-existent camera")
                continue
            try:
                live_obj = camera_data(
                            op = enum_ipcOpCode.CONST_START_CAMERA_STREAM_OP,
                            name = camera.name,
                            # Everything else can be None
                            status = None,
                            ip = None,
                            macAddr = None,
                            port = None,
                            time_len = None,
                            uname = None,
                            pwd = None,
                            desc = None
                            )
                self.nv_midbox_start_livestream(live_obj)
            except:
                self.nv_log_handler.error("Failed to start live stream of %s",
                                      camera.name)

    def __nv_midbox_allCam_status_update(self, status):
        '''
        Update all the camera status to 'status'
        '''
        # Update all the camera status to deferred before exiting.
        if not db_mgr_obj.get_tbl_record_cnt(nv_camera):
            self.nv_log_handler.debug("Camera table empty in the system "\
                                      "not modifying the camera status")
            return
        cam_records = db_mgr_obj.get_tbl_records(nv_camera)
        for camera in cam_records:
            valid_camera_status = self._is_nv_midbox_cam_status_update_valid(
                                        camera.status, status)
            if not valid_camera_status:
                self.nv_log_handler.error("Cannot change state %s to %s for "
                                          "camera: %s",
                                          enum_camStatus.CAM_STATUS_STR[camera.status],
                                          enum_camStatus.CAM_STATUS_STR[status],
                                          camera.name)
                continue
            camera.status = status
        db_mgr_obj.db_commit()
        GBL_WSCLIENT.send_notify()

    def nv_midbox_allCam_status_update(self, status):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_allCam_status_update(status)
        except Exception as e:
            self.nv_log_handler.info("%s exception occured while updating "
                                     "camera status", e)
        finally:
            db_mgr_obj.db_end_transaction()

    def exit_all_threads(self):
        '''
        Function to stop all the threads that are started by the midbox conf.
        cli, relay manager live and all camera threads are stopped.
        '''
        self.nv_midbox_cli.stop()
        self.nv_relay_mgr.relay_stop()
        # Set cameras to deferred while stopping all the threads.
        self.nv_midbox_allCam_status_update(enum_camStatus.CONST_CAMERA_DEFERRED)
        # Stop all the live streaming threads.
        self.cam_thread_mgr.stop_all_camlive()
        self.cam_thread_mgr.kill_all_camera_threads()
        self.nv_relay_mgr.relay_join()
        self.cam_thread_mgr.join_all_camera_threads()
        #Set camera thread to ready before exiting..
        self.nv_midbox_allCam_status_update(enum_camStatus.CONST_CAMERA_READY)
        db_mgr_obj.teardown_session()

    def do_midbox_conf(self):
        '''
        Read the conf queue in fixed time interval to configure the middlebox.
        '''
        while(1):
            try:
                conf_obj = GBL_CONF_QUEUE.dequeue_data()
                if conf_obj is None:
                    # The queue is empty, nothing to configure.
                    sleep(1)
                    continue
                obj_list = conf_obj["value"]
                for obj in obj_list:
                    choice = obj.get_ipc_datatype()
                    if choice not in nv_midbox_conf.NV_MIDBOX_CONF_FNS:
                        self.nv_log_handler.error("Cannot execute the %d conf"
                                " type", choice)
                        continue
                    if not obj.is_ipc_op_valid():
                        self.nv_log_handler.error("Cannot execute an invalid"
                                                  "operation")
                        continue
                    fn = nv_midbox_conf.NV_MIDBOX_CONF_FNS[choice]
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
                                    video_path = srv_path,
                                    uname = conf_obj.uname,
                                    pwd = conf_obj.pwd)
        db_mgr_obj.init_webserver_params(wbsrv_entry)

    def del_nv_webserver(self, conf_obj):
        # TODO :: The relay thread must be stopped when a webserver data is
        # changed.
        db_mgr_obj.del_webserver()

    def do_camera_op(self, conf_obj):
        CAM_OP_FNS = {
                enum_ipcOpCode.CONST_ADD_CAMERA_OP : "nv_midbox_add_camera",
                enum_ipcOpCode.CONST_DEL_CAMERA_OP : "nv_midbox_del_camera",
                enum_ipcOpCode.CONST_START_CAMERA_STREAM_OP : "nv_midbox_start_stream",
                enum_ipcOpCode.CONST_STOP_CAMERA_STREAM_OP : "nv_midbox_stop_stream",
                enum_ipcOpCode.CONST_UPDATE_CAMERA_STATUS : "nv_midbox_cam_status_update",
                enum_ipcOpCode.CONST_START_CAMERA_LIVESTREAM : "nv_midbox_start_livestream",
                enum_ipcOpCode.CONST_STOP_CAMERA_LIVESTREAM : "nv_midbox_stop_livestream",
                enum_ipcOpCode.CONST_UPDATE_CAMERA_LIVESTREAM_URL : "nv_midbox_update_live_url"
                      }
        op = conf_obj.get_ipc_op()
        self.do_conf_op(op, CAM_OP_FNS, conf_obj)

    def __nv_midbox_add_camera(self, cam_obj):
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
                                      "Current state is %s",
                                      enum_camStatus.CAM_STATUS_STR[cam_status])
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
        except Exception as e:
            self.nv_log_handler.error("Unknown error, failed to add camera %s",
                                      e)
            GBL_WSCLIENT.send_notify()
            return

        # While adding the camera, need to start the live streaming as well
        try:
            live_obj = camera_data(op = enum_ipcOpCode.CONST_START_CAMERA_STREAM_OP,
                               name = cam_name,
                               # Everything else can be None
                               status = None,
                               ip = None,
                               macAddr = None,
                               port = None,
                               time_len = None,
                               uname = None,
                               pwd = None,
                               desc = None
                               )
            self.__nv_midbox_start_livestream(live_obj)
        except:
            self.nv_log_handler.error("Failed to start live stream of %s",
                                      cam_name)
        finally:
            GBL_WSCLIENT.send_notify()

    def nv_midbox_add_camera(self, cam_obj):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_add_camera(cam_obj)
        except Exception as e:
            self.nv_log_handler.info("Failed to add camera : %s", e)
        finally:
            db_mgr_obj.db_end_transaction()

    def __nv_midbox_del_camera(self, cam_obj):
        self.__nv_midbox_kill_stream(cam_obj)
        cam_name = cam_obj.name
        filter_arg = {'name' : cam_name}

        # While deleting the camera, make sure the live streaming is stopped.
        try:
            live_obj = camera_data(op = enum_ipcOpCode.CONST_STOP_CAMERA_LIVESTREAM,
                               name = cam_name,
                               # Everything else can be None
                               status = None,
                               ip = None,
                               macAddr = None,
                               port = None,
                               time_len = None,
                               uname = None,
                               pwd = None,
                               desc = None
                               )
            self.__nv_midbox_stop_livestream(live_obj)
        except:
            self.nv_log_handler.error("Failed to stop live stream of %s",
                                      cam_name)
            GBL_WSCLIENT.send_notify()
            return

        try:
            cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera,
                                                                   filter_arg)
            db_mgr_obj.delete_record(cam_record)
            db_mgr_obj.db_commit()
        except:
            self.nv_log_handler.error("Failed to delete the camera %s",
                                      cam_obj.name)
        finally:
            GBL_WSCLIENT.send_notify()

    def nv_midbox_del_camera(self, cam_obj):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_del_camera(cam_obj)
        except Exception as e:
            self.nv_log_handler.info("Exception occured while"
                                     " deleting the camera : %s", e)
        finally:
            db_mgr_obj.db_end_transaction()

    def __nv_midbox_start_stream(self, cam_obj):
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
                                      " camera is ready, current state is %s",
                                      enum_camStatus.CAM_STATUS_STR[cam_record.status])
            GBL_WSCLIENT.send_notify()
            return
        self.cam_thread_mgr.start_camera_thread(cam_record)
        self.nv_log_handler.debug("staring the stream recording on camera %s"
                                  % cam_name)
        cam_record.status = enum_camStatus.CONST_CAMERA_RECORDING
        db_mgr_obj.db_commit()
        GBL_WSCLIENT.send_notify()

    def nv_midbox_start_stream(self, cam_obj):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_start_stream(cam_obj)
        except Exception as e:
            self.nv_log_handler.info("Failed to start camera stream : %s",
                                     e)
        finally:
            db_mgr_obj.db_end_transaction()

    def __nv_midbox_stop_stream(self, cam_obj):
        cam_name = cam_obj.name
        filter_arg = {'name' : cam_name}
        cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera, filter_arg)
        if cam_record is None:
            self.nv_log_handler.error("No camera record found for %s", cam_name)
            return
        if cam_record.status is not enum_camStatus.CONST_CAMERA_RECORDING:
            self.nv_log_handler.error("Cannot stop the streaming as the"
                                     " camera is not recording,"
                                     " current state is %s",
                                     enum_camStatus.CAM_STATUS_STR[cam_record.status])
            GBL_WSCLIENT.send_notify()
            return
        cam_record.status = enum_camStatus.CONST_CAMERA_DEFERRED
        self.cam_thread_mgr.stop_camera_thread(cam_record.cam_id, None)
        db_mgr_obj.db_commit()
        self.nv_log_handler.debug("Stop streaming on camera %s" %cam_name)
        GBL_WSCLIENT.send_notify()

    def nv_midbox_stop_stream(self, cam_obj):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_stop_stream(cam_obj)
        except Exception as e:
            self.nv_log_handler.info("Failed to stop camera stream %s", e)
        finally:
            db_mgr_obj.db_end_transaction()

    def __nv_midbox_kill_stream(self, cam_obj):
        '''
        Kill the camera streaming forcefully. Can be used while closing
        middlebox and deleting the camera from the middlebox
        '''
        cam_name = cam_obj.name
        filter_arg = {'name' : cam_name}
        cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera, filter_arg)
        if cam_record is None:
            self.nv_log_handler.error("No camera record found for %s"
                                      " to kill", cam_name)
            return
        try:
            self.cam_thread_mgr.kill_camera_thread(cam_id = cam_record.cam_id,
                                                   cam_obj = None)
            cam_record.status = enum_camStatus.CONST_CAMERA_READY
            db_mgr_obj.db_commit()
            self.nv_log_handler.debug("Killed streaming thread for camera %s",
                                      cam_name)
            GBL_WSCLIENT.send_notify()
        except Exception as e:
            self.nv_log_handler.error("Failed to kill the camera streaming %s",
                                      e)

    def nv_midbox_kill_stream(self, cam_obj):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_kill_stream(cam_obj)
        except Exception as e:
            self.nv_log_handler.info("Killing the camera failed : %s", e)
        finally:
            db_mgr_obj.db_end_transaction()

    def _is_nv_midbox_cam_status_update_valid(self, old_state, new_state):
        '''
        It is necessary to validate the camera status before updating the status
        blindly.
        The possible status updates are given below. The 'status_upadte_mtx'
        holds the same information. Any update on enum_camStatus should update
        this function as well.

        CAMERA_READY --> CAMERA_DEFERRED
        CAMERA_READY --> CAMERA_DISCONNECTED

        CAMERA_RECORDING --> CAMERA_DEFERED
        CAMERA_RECORDING -->CAMERA_DISCONNECTED

        CAMERA_DEFERRED --> CAMERA_READY
        CAMERA_DEFERRED --> CAMERA_RECORDING
        CAMERA_DISCONNECTED --> none

        CAMERA_NEW --> none
        '''
        status_upadte_mtx = {
            enum_camStatus.CONST_CAMERA_NEW :
                [enum_camStatus.CONST_CAMERA_DISCONNECTED],
            enum_camStatus.CONST_CAMERA_READY :
                [enum_camStatus.CONST_CAMERA_DEFERRED,
                 enum_camStatus.CONST_CAMERA_DISCONNECTED],
            enum_camStatus.CONST_CAMERA_RECORDING :
                [enum_camStatus.CONST_CAMERA_DEFERRED,
                 enum_camStatus.CONST_CAMERA_DISCONNECTED],
            enum_camStatus.CONST_CAMERA_DISCONNECTED : [],
            enum_camStatus.CONST_CAMERA_DEFERRED :
                [enum_camStatus.CONST_CAMERA_DISCONNECTED,
                 enum_camStatus.CONST_CAMERA_READY,
                 enum_camStatus.CONST_CAMERA_RECORDING]
        }
        if not old_state in status_upadte_mtx:
            self.nv_log_handler.error("Camera is in unexpected state %d",
                                      old_state)
            return False
        if not new_state in status_upadte_mtx:
            self.nv_log_handler.error("Camera cannot set to an unexpected state"
                                      "%d", new_state)
            return False
        valid_states = status_upadte_mtx[old_state]
        if new_state not in valid_states:
            self.nv_log_handler.error("Camera cannot move from state %s to %s",
                                      enum_camStatus.CAM_STATUS_STR[old_state],
                                      enum_camStatus.CAM_STATUS_STR[new_state])
            return False
        return True

    def __nv_midbox_cam_status_update(self, cam_obj):
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
        valid_state_change = self._is_nv_midbox_cam_status_update_valid(
                                    cam_record.status, cam_obj.status)
        if not valid_state_change:
            return
        cam_record.status = cam_obj.status
        db_mgr_obj.db_commit()
        GBL_WSCLIENT.send_notify()
        self.nv_log_handler.debug("%s camera has new status %s", cam_name,
                                  enum_camStatus.CAM_STATUS_STR[cam_obj.status])

    def nv_midbox_cam_status_update(self, cam_obj):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_cam_status_update(cam_obj)
        except Exception as e:
            self.nv_log_handler.info("Failed to update the camera status %s", e)
        finally:
            db_mgr_obj.db_end_transaction()

    def nv_midbox_stop(self, obj):
        try:
            self.nv_log_handler.info("Quit the middlebox, "
                                  "Waiting for all threads to coalesce...")
            self.exit_all_threads()
            sys.exit()
        except SystemExit as e:
            raise e
        except Exception as e:
            self.nv_log_handler.error("Unknown error while exiting the middlebox"
                                      " : %s" % e)

    def __nv_midbox_start_livestream(self, cam_obj):
        # No DB locks are acquired for starting the live-stream. The expectation
        # is the caller must have taken necessary DB lock before calling this
        # function.
        cam_name =  cam_obj.name
        filter_arg = {'name' : cam_name}
        cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera, filter_arg)
        if cam_record is None:
            self.nv_log_handler.error("No camera record found to start "
                                      "livestream %s", cam_name)
            return
        if cam_record.live_url:
            self.nv_log_handler.info("Cannot start livestream again, "\
                                     "livestream is running at %s",
                                     cam_record.live_url)
            return
        try:
            url = self.cam_thread_mgr.start_cam_live(cam_record)
        except Exception as e:
            self.nv_log_handler.error("Failed to start live stream for %s"
                                      " Exception %s", cam_name, e)
            return
        #Update the database when the live streaming is started successfully
        cam_record.live_url = url
        db_mgr_obj.db_commit()
        # It is necessary to do the web client notification when the live
        # streaming is started. However this function get called as part of
        # add_camera and the notification will be called by that function.

    def nv_midbox_start_livestream(self, cam_obj):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_start_livestream(cam_obj)
        except Exception as e:
            self.nv_log_handler.info("Failed to start live stream : %s", e)
        finally:
            db_mgr_obj.db_end_transaction()

    def __nv_midbox_stop_livestream(self, cam_obj):
        # No DB locks are acquired in this function. Caller must acquire the
        # locks before stopping the live stream.
        cam_name =  cam_obj.name
        filter_arg = {'name' : cam_name}
        cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera, filter_arg)
        if cam_record is None:
            self.nv_log_handler.error("No camera record found to stop "
                                      "livestream %s", cam_name)
            return
        if cam_record.live_url is None:
            self.nv_log_handler.info("Cannot stop livestream again, "
                                     "livestream is already stopped for %s",
                                     cam_record.name)
            return
        try:
            self.cam_thread_mgr.stop_cam_live(cam_record.cam_id)
        except Exception as e:
            self.nv_log_handler.info("Cannot stop live streaming on %s"
                                     " Exception %s", cam_name, e)
            return
        cam_record.live_url = None
        db_mgr_obj.db_commit()
        # Call the webclient notification after the live stream stopped.
        # It is the responsibility of caller to do so.
        # livestream is stopped as part of camera delete. So the webclient
        # update is called in that function.

    def nv_midbox_stop_livestream(self, cam_obj):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_stop_livestream(cam_obj)
        except Exception as e:
            self.nv_log_handler.info("Failed to stop the livestream : %s", e)
        finally:
            db_mgr_obj.db_end_transaction()

    def __nv_midbox_update_live_url(self, cam_obj):
        cam_name = cam_obj.name
        filter_arg = {'name' : cam_name}
        cam_record = db_mgr_obj.get_tbl_records_filterby_first(nv_camera, filter_arg)
        if cam_record is None:
            self.nv_log_handler.error("No camera record found to update "
                                      "liveurl %s", cam_name)
            return
        try:
            cam_record.live_url = cam_obj.live_url
            db_mgr_obj.db_commit()
        except:
            self.nv_log_handler.info("Failed to update the liveurl to %s"
                                     " for the camera %s", cam_obj.live_url,
                                     cam_name)
        GBL_WSCLIENT.send_notify()

    def nv_midbox_update_live_url(self, cam_obj):
        try:
            db_mgr_obj.db_start_transaction()
            self.__nv_midbox_update_live_url(cam_obj)
        except Exception as e:
            self.nv_log_handler.info("Failed to update live url :%s", e)
        finally:
            db_mgr_obj.db_end_transaction()
