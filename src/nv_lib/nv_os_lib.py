#! /usr/bin/python3
# -*- coding: utf8 -*-
# The operating system interaction module for nv-middlebox. 
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import platform
from src.nv_logger import nv_logger
import subprocess
import os

class nv_linux_lib():
    '''
    Library class for the linux operating system.
    '''
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()  

    def make_dir(self,dir_name):
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

    def execute_cmd(self, cmd, args):
        exec_cmd = []
        exec_cmd.append(cmd)

        if(len(args)):
            exec_cmd = exec_cmd + list(args)

        exec_cmd = filter(None, exec_cmd)
        self.nv_log_handler.debug("Excuting cmd:" + exec_cmd)
        
        try:
            out = subprocess.Popen(exec_cmd)
        except Exception as e:
            self.nv_log_handler.error("Failed to run the bash command, " + e)
        out.wait()

    def is_pgm_installed(self,program):
        '''
        Check if the program installed on the machine.
        params
            program: The name of the program
        '''
        fpath, _ = os.path.split(program)
        if fpath:
            is_exe = os.path.isfile(fpath) and os.access(fpath, os.X_OK)(program)
            if is_exe:
                return program
            else:
                for path in os.environ["PATH"].split(os.pathsep):
                    path = path.strip('"')
                    exe_file = os.path.join(path, program)
                    if is_exe(exe_file):
                        return exe_file
        return None

class nv_os_lib():
    '''
    Library class for OS interaction.All the external application interaction
    handled by this class.
    '''
    context = None

    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        if platform.system() == 'Linux':
            self.context = nv_linux_lib()
        elif platform.system() == 'Windows':
            self.nv_log_handler.error("Windows support is not available now.")
            raise NotImplementedError("Windows support is not available.")
        else:
            self.nv_log_handler.error("The platform cannot determined ")
            raise NotImplementedError("Unsupported platform %s" 
                                      % platform.system())

    def execute_cmd(self, cmd, args):
        ''''
        Execute a command on the system.
        params :
            cmd :command to be executed on th system.
            args : A list of arguments in the form of [arg1,arg2, arg3, ..]
        ''' 
        if self.context is None:
            self.nv_log_handler.error("Platform is not defined.")
            raise ReferenceError("Undefined context, cannot run the command")
            
        self.context.execute_cmd(cmd, args)

    def is_pgm_installed(self, pgm_name):
        '''
        Check if the external program available/installed on the platform.
        params :
            pgm_name : The name of the program to search for.
        Returns :
            Path to the program if found and None otherwise.
        '''
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
            raise ReferenceError("Undefined context, cannot find the program.")
        return self.context.is_pgm_installed(pgm_name)

    def make_dir(self,dir_name):
        '''
        Create a new directory in the system if its not exists.
        params :
            dir_name : Directory name in absolute path.
        '''
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
            raise ReferenceError("Undefined context, cannot find the program.")
        return self.context.make_dir(dir_name)