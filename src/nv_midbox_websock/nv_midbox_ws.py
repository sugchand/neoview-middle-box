#! /usr/bin/python3
# -*- coding: utf8 -*-
# The web-socket module for nv-middlebox.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import threading
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
from src.nv_logger import nv_logger
from src.nvdb.nvdb_manager import db_mgr_obj, nv_camera
from src.nv_logger import default_nv_log_handler
from src.nv_lib.nv_sync_lib import GBL_NV_SYNC_OBJ
from src.nv_midbox_websock.nv_midbox_wsClient import GBL_WSCLIENT
import json
from src.nv_lib.ipc_data_obj import camera_data,enum_ipcOpCode
from src.nv_lib.nv_sync_lib import GBL_CONF_QUEUE
from src.nvdb.nvdb_manager import enum_camStatus
from src.nv_lib.nv_os_lib import nv_os_lib
import ssl
import os

class websock_connectionPool():
    '''
    Class to keep track of every websocket connections.
    The websocket handling is thread safe in this connection pool.
    '''
    WS_CONN_MUTEX = "ws_conn_lock"
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.connections = set()

    def add_connection(self, conn):
        GBL_NV_SYNC_OBJ.mutex_lock(self.WS_CONN_MUTEX)
        self.connections.add(conn)
        GBL_NV_SYNC_OBJ.mutex_unlock(self.WS_CONN_MUTEX)

    def remove_connection(self, conn):
        GBL_NV_SYNC_OBJ.mutex_lock(self.WS_CONN_MUTEX)
        self.connections.remove(conn)
        GBL_NV_SYNC_OBJ.mutex_unlock(self.WS_CONN_MUTEX)

    def write_to_all_connections(self, msg):
        GBL_NV_SYNC_OBJ.mutex_lock(self.WS_CONN_MUTEX)
        for conn in self.connections:
            try:
                conn.write_message(msg)
            except:
                self.nv_log_handler.error("Failed to write to a ws connection.")
                # Cannot write to specific connection, continue to next.
                continue
        GBL_NV_SYNC_OBJ.mutex_unlock(self.WS_CONN_MUTEX)

    def write_to_connection(self, conn, msg):
        GBL_NV_SYNC_OBJ.mutex_lock(self.WS_CONN_MUTEX)
        conn.write_message(msg)
        GBL_NV_SYNC_OBJ.mutex_unlock(self.WS_CONN_MUTEX)

    def write_camera_to_all_connection(self, camera):
        '''
        Function will write out camera db record to all the active
        connections
        '''
        GBL_NV_SYNC_OBJ.mutex_lock(self.WS_CONN_MUTEX)
        for conn in self.connections:
            try:
                cam_json = []
                cam_json.append(conn.get_camera_json(camera))
                self.write_to_connection(conn, json.dumps(cam_json))
            except:
                self.nv_log_handler.error("Failed to write camera json to conn")
                continue
        GBL_NV_SYNC_OBJ.mutex_unlock(self.WS_CONN_MUTEX)

class UserWebSocketHandler(tornado.websocket.WebSocketHandler):
    '''
    Web socket handler to manage the user interface. Providing hard switch
    functionality with this web socket
    '''
    def open(self):
        # Read the DB for all the camera and system details
        # Format it into json
        # send out it as a message
        cam_json = []
        GBL_WEBSOCK_POOL.add_connection(self)
        try:
            cameras = db_mgr_obj.get_tbl_records(nv_camera)
            if not cameras:
                return
            for camera in cameras:
                cam_json.append(self.get_camera_json(camera))
            if not cam_json:
                return
            GBL_WEBSOCK_POOL.write_to_connection(self, json.dumps(cam_json))
        except Exception as e:
            default_nv_log_handler.error("Exception while opening user websocket"
                                         " %s", e)

    def get_camera_json(self, camera):
        '''
        camera is a object of db class nv_camera.
        Populate only the relevant fields.
        '''
        cam_dic = {
                   "name" : camera.name,
                   "status" : camera.status,
                   "description" : camera.desc,
                   "liveUrl" : camera.live_url,
                   "token" : None # A unique token to idenfity source of ws
                   }
        return cam_dic

    def send_all_camera_to_all_ws(self):
        cam_json = []
        try:
            cameras = db_mgr_obj.get_tbl_records(nv_camera)
            if not cameras:
                # No cameras configured, return empty json.
                cam_json.append({})
                GBL_WEBSOCK_POOL.write_to_all_connections(json.dumps(cam_json))
                return
            for camera in cameras:
                cam_json.append(self.get_camera_json(camera))
            if not cam_json:
                return
            GBL_WEBSOCK_POOL.write_to_all_connections(json.dumps(cam_json))
        except Exception as e:
            default_nv_log_handler.error("Exception while opening user websocket"
                                         " %s", e)

    def update_camera_status(self, name, status):
        # Function to update the camera status.
        if status is enum_camStatus.CONST_CAMERA_RECORDING:
            cam_ipcData = camera_data(
                                op = enum_ipcOpCode.CONST_START_CAMERA_STREAM_OP,
                                name = name,
                                status = status,
                                ip = None,
                                macAddr = None,
                                port = None,
                                time_len = None,
                                uname = None,
                                pwd = None,
                                desc = None
                                )
        elif status is enum_camStatus.CONST_CAMERA_READY:
            cam_ipcData = camera_data(
                                op = enum_ipcOpCode.CONST_STOP_CAMERA_STREAM_OP,
                                name = name,
                                status = status,
                                ip = None,
                                macAddr = None,
                                port = None,
                                time_len = None,
                                uname = None,
                                pwd = None,
                                desc = None
                                )
        try:
            GBL_CONF_QUEUE.enqueue_data(obj_len = 1,
                                obj_value = [cam_ipcData])
        except Exception as e:
            default_nv_log_handler.error("Exception in ws, cannot send status"
                                         "update, %s", e)

    def on_message(self, message):
        # TODO : Send out message to the midbox conf to change the camera
        # settings.
        try:
            ws_json = json.loads(message)
        except ValueError:
            default_nv_log_handler.debug("Received non json data, do nothing..")
            return
        if len(ws_json) > 1:
            default_nv_log_handler.debug("More fields in json, exiting..")
            return
        data = ws_json[0] #Only one element present in the list.
        if not 'token' in data:
            default_nv_log_handler.debug("token field is missing, do nothing")
            return
        token_id = data['token']
        if GBL_WSCLIENT.validate_token(token_id = token_id):
            GBL_WSCLIENT.delete_token(token_id = token_id)
            # Message from the system itself.
            # Notification to the server about the system update.
            self.send_all_camera_to_all_ws()
            return
        elif len(data) != 5:
            default_nv_log_handler.error("Cannot Parse json in ws, length "\
                                        "is invalid in %s.", data)
            return
        # Request from the client to change the state of camera.
        if not 'name' in data and \
            not 'status' in data:
            default_nv_log_handler.error("Invalid JSON format, ws cannot "\
                                         "process json %s", data)
            return
        self.update_camera_status(name = data['name'], status = data['status'])

    def on_close(self):
        GBL_WEBSOCK_POOL.remove_connection(self)

    def onerror(self):
        GBL_WEBSOCK_POOL.remove_connection(self)

    def check_origin(self, origin):
        return True

class IndexPageHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            self.render("index.html")
        except Exception as e:
            default_nv_log_handler.debug("Cannot render the page correctly..%s",
                                         e)

class ServerIndexPageHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("serv_index.html")

class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r'/', IndexPageHandler),
            (r'/server', ServerIndexPageHandler),
            (r'/userwebsocket', UserWebSocketHandler),
            (r"/static/(.*)",tornado.web.StaticFileHandler, {"path": "./static"},)
        ]
        settings = {
            'debug' : True,
            "static_path": "src/nv_midbox_websock/templates/static",
            'template_path': 'src/nv_midbox_websock/templates'
        }
        tornado.web.Application.__init__(self, handlers, **settings)

class nv_midbox_ws(threading.Thread):

    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        threading.Thread.__init__(self, None, None, "nv_midbox_ws")
        self.daemon = True
        self.os_context = nv_os_lib()

    def run(self):
        try:
            ws_app = Application()
            cert_file = os.getcwd() + "/ssl_data/nvmidbox.cert"
            key_file = os.getcwd() + "/ssl_data/nvmidbox.key"

            if self.os_context.is_path_exists(cert_file) and \
                self.os_context.is_path_exists(key_file):
                self.nv_log_handler.info("Starting midbox HTTPS server..")
                ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_ctx.load_cert_chain(cert_file, key_file)
                server = tornado.httpserver.HTTPServer(ws_app,
                                                       ssl_options=ssl_ctx)
            else:
                # ssl data is missing, so start webserver in http mode.
                self.nv_log_handler.info("Starting midbox HTTP server..")
                server = tornado.httpserver.HTTPServer(ws_app)

            server.listen(8080)
            tornado.ioloop.IOLoop.instance().start()
        except:
            self.nv_log_handler.error("Unknown error while starting"
                                      " websocket server")

    def stop(self):
        super(nv_midbox_ws, self).stop()

GBL_WEBSOCK_POOL = websock_connectionPool()