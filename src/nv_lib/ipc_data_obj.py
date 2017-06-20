#! /usr/bin/python3
# -*- coding: utf8 -*-
# Collection of ipc data element objects.
# All the ipc uses one of the data class to communicate each other.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

class enum_ipcType():
    '''
    the Queue object type to be passed in the object.
    Note :: Do not use this class for any IPC
    '''
    CONST_INVALID_IPC_OBJ = 0
    CONST_CAMERA_OBJ = 1
    CONST_SYSTEM_STATUS_OBJ = 2
    CONST_WEBSERVER_OBJ = 3

# Dont create any element after this, Used for validating the object.
    CONST_QUIT_MIDBOX = 10

class enum_ipcOpCode():
    CONST_INVALID_IPC_OP = 0
    CONST_EXIT_OP = 1
    CONST_ADD_WEBSERVER_OP = 2
    CONST_DEL_WEBSERVER_OP = 3
    CONST_ADD_CAMERA_OP = 4
    CONST_DEL_CAMERA_OP = 5
    CONST_START_CAMERA_STREAM_OP = 6
    CONST_STOP_CAMERA_STREAM_OP = 7
    CONST_UPDATE_CAMERA_STATUS = 8
    CONST_START_CAMERA_LIVESTREAM = 9
    CONST_STOP_CAMERA_LIVESTREAM = 10
    CONST_IPC_OP_MAX_LIMIT = 100

class ipc_data():
    '''
    The parent class for the ipc data. Any IPC data class must inherit this class.
    '''
    def __init__(self, ipc_type = enum_ipcType.CONST_INVALID_IPC_OBJ,
                 ipc_op = enum_ipcOpCode.CONST_INVALID_IPC_OP):
        self.__type = ipc_type
        self.__op = ipc_op

    def is_ipc_datatype_valid(self):
        if (self.__type < enum_ipcType.CONST_INVALID_IPC_OBJ or
            self.__type > enum_ipcType.CONST_QUIT_MIDBOX):
            return False
        return self.__type is not enum_ipcType.CONST_INVALID_IPC_OBJ

    def get_ipc_datatype(self):
        return self.__type

    def get_ipc_op(self):
        return self.__op

    def is_ipc_op_valid(self):
        if (self.__op > enum_ipcOpCode.CONST_INVALID_IPC_OP and
            self.__op < enum_ipcOpCode.CONST_IPC_OP_MAX_LIMIT):
            return True
        return False

class camera_data(ipc_data):
    '''
    Class to hold the camera details.
    ''' 
    def __init__(self, op, name, status, ip, macAddr, port, time_len, uname,
                 pwd, desc = None, live_url = None):
        super(camera_data, self).__init__(ipc_type =
                                          enum_ipcType.CONST_CAMERA_OBJ,
                                          ipc_op = op)
        self.name = name
        self.status = status
        self.desc = desc
        self.ip = ip
        self.macAddr = macAddr
        self.port = port
        self.time_len = time_len
        self.uname = uname
        self.pwd = pwd
        self.live_url = live_url

class webserver_data(ipc_data):
    '''
    Class for manage the webserver data
    '''
    def __init__(self, op, name, videopath, uname , pwd):
        super(webserver_data, self).__init__(ipc_type =
                                             enum_ipcType.CONST_WEBSERVER_OBJ,
                                             ipc_op = op)
        self.name = name
        self.videopath = videopath
        self.uname = uname
        self.pwd = pwd

class exitSys_data(ipc_data):
    '''
    Class to send exit system information between threads
    '''
    def __init__(self):
        super(exitSys_data, self).__init__(ipc_type = enum_ipcType.CONST_QUIT_MIDBOX,
                                           ipc_op = enum_ipcOpCode.CONST_EXIT_OP)
