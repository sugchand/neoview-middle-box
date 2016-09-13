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
import shutil

class nv_linux_lib():
    '''
    Library class for the linux operating system.
    '''
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()  

    def make_dir(self,dir_name):
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

    def remove_file(self, file_name):
        try:
            if os.path.exists(file_name):
                os.remove(file_name)
        except Exception as e:
            self.nv_log_handler.error("Failed to remove file %s" %str(e))
            raise e

    def remove_dir(self, dir_name):
        try:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
        except Exception as e:
            self.nv_log_handler.error("Failed to remove the directory %s"
                                      %str(e))

    def execute_cmd(self, cmd, args):
        exec_cmd = []
        exec_cmd.append(cmd)

        if(len(args)):
            exec_cmd = exec_cmd + list(args)

        self.nv_log_handler.debug("Excuting cmd: %s" %exec_cmd)
        try:
            out = subprocess.Popen(exec_cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        except Exception as e:
            self.nv_log_handler.error("Failed to run the bash command, " + e)
            raise e
        else:
            result, err = out.communicate()
            return err

    def is_path_exists(self, path):
        return os.path.exists(path)

    def get_dirname(self, path):
        '''
        Get the directory name for the specified path
        '''
        return os.path.dirname(path)

    def copy_file(self, src_file, dst_dir):
        shutil.copy(src_file, dst_dir)

    def get_parent_dir(self, file_path):
        return os.path.dirname(file_path)

    def get_last_filename(self, file_path):
        '''
        Find the last file name of a file.
        It returns only last level file name,
        for eg: /tmp/tmp2/dir will return 'dir'
        '''
        file_dir = os.path.dirname(file_path)
        if not file_dir:
            return None
        return os.path.relpath(file_path, file_dir)

    def join_dir(self, src_dir, new_dir):
        '''
        Join new_dir to dir. for eg:
        dir = /tmp, new_dir = test
        the result will be /tmp/test
        '''
        return os.path.join(src_dir, new_dir)

    def get_filesize_in_bytes(self, file_path):
        stat_info = os.stat(file_path)
        return stat_info.st_size

    def is_pgm_installed(self,program):
        '''
        Check if the program installed on the machine.
        params
            program: The name of the program
        '''
        fpath, _ = os.path.split(program)
        if fpath:
            is_exe = os.path.isfile(fpath) and os.access(fpath, os.X_OK)
            if is_exe:
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                is_exe = os.path.isfile(exe_file) and os.access(exe_file, os.X_OK)
                if is_exe:
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

    def remove_dir(self, dir_name):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
            raise ReferenceError("Undefined context, cannot remove dir.")
        return self.context.remove_dir(dir_name)

    def remove_file(self,file_name):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
            raise ReferenceError("Undefined context, cannot remove the file.")
        return self.context.remove_file(file_name)

    def is_path_exists(self, path):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.is_path_exists(path)

    def get_dirname(self, path):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.get_dirname(path)

    def copy_file(self, src_path, dst_dir):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.copy_file(src_path, dst_dir)

    def get_last_filename(self, file_path):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.get_last_filename(file_path)

    def get_parent_dir(self, file_path):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.get_parent_dir(file_path)

    def join_dir(self, src_dir, new_dir):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.join_dir(src_dir, new_dir)

    def get_filesize_in_bytes(self, file_path):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.get_filesize_in_bytes(file_path)
