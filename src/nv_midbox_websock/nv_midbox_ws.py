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
from tornado.web import asynchronous
from tornado import gen
from tornado.ioloop import IOLoop
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
from time import sleep, time
from src.nv_logger import nv_logger
from src.nvdb.nvdb_manager import db_mgr_obj, nv_camera
from src.nv_logger import default_nv_log_handler
from src.nv_lib.nv_sync_lib import GBL_NV_SYNC_OBJ
from src.nv_midbox_websock.nv_midbox_wsClient import GBL_WSCLIENT
import json

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
        print("Writing camera...")
        for conn in self.connections:
            try:
                cam_json = []
                cam_json.append(conn.get_camera_json(camera))
                print(cam_json)
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
                   "token" : None # A unique token to idenfity source of ws
                   }
        return cam_dic

    def send_all_camera_to_all_ws(self):
        cam_json = []
        try:
            cameras = db_mgr_obj.get_tbl_records(nv_camera)
            if not cameras:
                return
            for camera in cameras:
                cam_json.append(self.get_camera_json(camera))
            if not cam_json:
                return
            GBL_WEBSOCK_POOL.write_to_all_connections(json.dumps(cam_json))
        except Exception as e:
            default_nv_log_handler.error("Exception while opening user websocket"
                                         " %s", e)

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
        for data in ws_json:
            if not 'token' in data:
                default_nv_log_handler.debug("token field is missing, do nothing")
                return
            token_id = data['token']
            if GBL_WSCLIENT.validate_token(token_id = token_id):
                GBL_WSCLIENT.delete_token(token_id = token_id)
                # Message from the system itself.
                self.send_all_camera_to_all_ws()

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

    def run(self):
        try:
            ws_app = Application()
            server = tornado.httpserver.HTTPServer(ws_app)
            server.listen(8080)
            tornado.ioloop.IOLoop.instance().start()
        except:
            self.nv_log_handler.error("Unknown error while starting"
                                      " websocket server")

    def stop(self):
        super(nv_midbox_ws, self).stop()

GBL_WEBSOCK_POOL = websock_connectionPool()