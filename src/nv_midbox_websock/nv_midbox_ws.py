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
import json

class ServerWebSocketHandler(tornado.websocket.WebSocketHandler):
    '''
    Web socket handler for handling communication with webserver.
    '''
    def open(self):
        print("websocket open")
        pass

    def on_message(self, message):
        while(1):
            sleep(10)
            self.write_message(u"Your message was: " + message)

    def on_close(self):
        pass

class UserWebSocketHandler(tornado.websocket.WebSocketHandler):
    '''
    Web socket handler to manage the user interface. Providing hard switch
    functionality with this web socket
    '''
    @asynchronous
    @gen.engine
    def open(self):
        # Read the DB for all the camera and system details
        # Format it into json
        # send out it as a message
        cam_json = []
        try:
            cameras = db_mgr_obj.get_tbl_records(nv_camera)
            if not cameras:
                return
            for camera in cameras:
                cam_json.append(self.get_camera_json(camera))
            if not cam_json:
                return
            self.write_message(json.dumps(cam_json))
        except Exception as e:
            default_nv_log_handler.error("Exception while opening user websocket"
                                         " %s", e)
            return
        finally:
            '''
            Do the looping for update here,
            '''
            #while(1):
                #yield gen.Task(IOLoop.instance().add_timeout, time.time() + 5)
            #    yield gen.sleep(10)
            #   self.write_message("In loop")
            self.finish()

    def get_camera_json(self, camera):
        '''
        camera is a object of db class nv_camera.
        Populate only the relevant fields.
        '''
        cam_dic = {
                   "name" : camera.name,
                   "status" : camera.status,
                   "description" : camera.desc
                   }
        return cam_dic

    def on_message(self, message):
        self.write_message(u"Your message was: " + message)

    def on_close(self):
        self.finish()

class IndexPageHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

class ServerIndexPageHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("serv_index.html")

class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r'/', IndexPageHandler),
            (r'/server', ServerIndexPageHandler),
            (r'/userwebsocket', UserWebSocketHandler),
            (r'/serverwebsocket', ServerWebSocketHandler)
        ]
        settings = {
            'template_path': 'src/nv_midbox_websock/templates'
        }
        tornado.web.Application.__init__(self, handlers, **settings)

class nv_midbox_ws(threading.Thread):

    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.nv_log_handler.error("In ws...")
        threading.Thread.__init__(self, None, None, "nv_midbox_ws")
        self.daemon = True

    def run(self):
        print("starting the ws")
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