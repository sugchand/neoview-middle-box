#! /usr/bin/python3
# -*- coding: utf8 -*-
# The operating system interaction module for nv-middlebox. 
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import platform
import errno
from src.nv_logger import nv_logger
import subprocess
import os
import shutil
import paramiko
from signal import SIGTERM
class nv_linux_lib():
    '''
    Library class for the linux operating system.
    '''
    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.ssh = None
        self.sftp = None

    def get_remote_host_connection(self, hostname, username, pwd):
        '''
        Returns a ssh object to connect 'hostname'.
        If the connection failed, error returned with NULL object.
        NOTE :: Called must close the SSH connection explicitly.
        Its not safe to keep rogue ssh connections around.
        '''
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(hostname, username = username,
                                password = pwd)
            return self.ssh
        except Exception as e:
            self.nv_log_handler.error("Failed to reach remote machine %s"
                                      % hostname);
            raise e

    def get_remote_sftp_connection(self, hostname, username, pwd):
        try:
            self.ssh = self.get_remote_host_connection(hostname, username, pwd)
            self.sftp = self.ssh.open_sftp()
            return self.sftp
        except Exception as e:
            self.nv_log_handler.error("Failed to get the sftp connection to %s"\
                                      % hostname)
            raise e

    def close_remote_sftp_connection(self):
        if self.sftp:
            self.sftp.close()

    def close_remote_host_connection(self):
        if self.ssh:
            self.ssh.close()

    def make_dir(self,dir_name):
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

    def remote_make_dir(self, sftp, dir_name):
        '''
        Recursive directory creation on a remote machine.
        '''
        parent_dir = os.path.abspath(os.path.join(dir_name, os.pardir))
        if not self.is_remote_path_exists(sftp, parent_dir):
            self.remote_make_dir(sftp, parent_dir)
        self.nv_log_handler.debug("creating remote directory %s" % dir_name)
        sftp.mkdir(dir_name)

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
            self.nv_log_handler.error("Failed to run the bash command, %s" + e)
            raise e
        else:
            _, err = out.communicate()
            return err

    def execute_cmd_bg(self, cmd, args):
        '''
        Execute a command in background. To handle the process externally, the
        process group is assigned a session id. The proocess id can be used to
        kill the process later. Or send signals to the process groups.
        @return: proc_obj : process Obj of process group leader/session.
        '''
        exec_cmd = []
        exec_cmd.append(cmd)

        if(len(args)):
            exec_cmd = exec_cmd + list(args)

        self.nv_log_handler.debug("Executing cmd in bg: %s" %exec_cmd)
        try:
            proc = subprocess.Popen(exec_cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    preexec_fn=os.setsid)
            return proc
        except Exception as e:
            self.nv_log_handler.error("Failed to run bash command %s", e)
            raise e

    def wait_cmd_complete(self, process_obj):
        '''
        Wait on a bg process that created by ' execute_cmd_bg ' .
        '''
        if not process_obj:
            self.nv_log_handler.error("Cannot wait on empty process obj")
            return
        try:
            process_obj.communicate()
        except Exception as e:
            self.nv_log_handler.error("Error on waiting on process obj %s", e)
            raise e

    def kill_process(self, process_obj):
        '''
        Kill the process that created by the subprocess popen. It is necessary
        to start the process with new session to kill all the child process.
        @param process_obj: the process obj that returned by execute_cmd_bg
        '''
        if not process_obj:
            self.nv_log_handler.info("Cannot kill a non existent process")
            return
        try:
            process_obj.terminate()
            process_obj.communicate()
        except Exception as e:
            self.nv_log_handler.error("Failed to kill the process %d "
                                      "Exception :  %s", process_obj.pid, e)
            raise e

    def is_path_exists(self, path):
        return os.path.exists(path)

    def is_remote_path_exists(self, sftp, path):
        if not sftp:
            self.nv_log_handler.error("Empty sftp handler, failed to "
                                      "validate the path")
            return
        try:
            sftp.stat(path)
        except IOError as e:
            if e.errno == errno.ENOENT:
                return False
        else:
            return True

    def get_dirname(self, path):
        '''
        Get the directory name for the specified path
        '''
        return os.path.dirname(path)

    def copy_file(self, src_file, dst_dir):
        '''
        Copy the file locally on a same machine. No validation for src/dst files
        are exists on the machine. The file will be overwritten when the file
        present at destination. Similarly if the file not present at source ,
        error out.
        '''
        shutil.copy(src_file, dst_dir)

    def remote_copy_file(self, sftp, src_file, remote_dir):
        '''
        Copy a file 'src_file' to a remote system at 'remote_dir'.
        sftp is a sftp session object for the specific remote machine.
        XXX :: Copy may fail when the destination directory permissions are not
        sufficient.
        '''
        try:
            if not sftp:
                return
            remote_file = os.path.join(remote_dir,
                                       self.get_last_filename(src_file))
            sftp.put(src_file, remote_file)
            self.nv_log_handler.debug("%s file copied to %s"
                                      % (src_file, remote_dir))
        except Exception as e:
            self.nv_log_handler.error("Failed to copy to remote machine.")
            raise e

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

    def get_free_listen_port(self):
        '''
        Returns a unused port in the system for the module to use.
        NOTE :: It is the responsibility of application to use the port as soon
        as possible.. It is possible that the port may be used by some other
        appln if it take long time to consume.
        This method offers the ports in best effort. It doesnt guarantee the
        port is free as long as its used. What it offer is, a free
        port that is available at the moment of executing the function.
        @return: port : port number/socket number.
        '''
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("",0))
            s.listen(1)
            port = s.getsockname()[1]
            s.close()
        except Exception as e:
            self.nv_log_handler.error("Failed to get a unused port, %s", e)
            raise e
        return port

    def is_remote_port_open(self, ip, port):
        '''
        Check if a port is open on a remote system. useful to check the
        connectivity to the camera.
        @param ip : ip address of remote machine in string format.
        @param port: port to check connectivity. Integer value
        @return: TRUE/FALSE : If port is open or not.
        '''
        if ip is None or port is None:
            self.nv_log_handler.info("Invalid port/ip, cannot validate port-open")
            return False
        try:
            import socket
            socket.setdefaulttimeout(10)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((ip,port))
            if result == 0:
                return True
        except Exception as e:
            self.nv_log_handler.error("Cannot validate if port is open"
                                      "Exception %s", e)
            return False
        finally:
            socket.setdefaulttimeout(None)
            sock.close()

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

    def get_remote_host_connection(self, hostname, username, pwd):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
            raise ReferenceError("Undefined context, cannot find the program.")
        return self.context.get_remote_host_connection(hostname, username, pwd)

    def get_remote_sftp_connection(self, hostname, username, pwd):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
            raise ReferenceError("Undefined context, cannot find the program.")
        return self.context.get_remote_sftp_connection(hostname, username, pwd)

    def close_remote_host_connection(self):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
            raise ReferenceError("Undefined context, cannot find the program.")
        return self.context.close_remote_host_connection()

    def close_remote_sftp_connection(self):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
            raise ReferenceError("Undefined context, cannot find the program.")
        return self.context.close_remote_sftp_connection()

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

    def remote_make_dir(self,sftp, dir_name):
        '''
        Create a new directory in the remote system if its not exists.
        params :
            sftp : the sftp session handle to talk to remote machine.
            dir_name : Directory name in absolute path.
        '''
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
            raise ReferenceError("Undefined context, cannot find the program.")
        return self.context.remote_make_dir(sftp, dir_name)

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

    def is_remote_path_exists(self, sftp, path):
        '''
        Check if a path exist on a given ssh connection.
        '''
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.is_remote_path_exists(sftp, path)

    def get_dirname(self, path):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.get_dirname(path)

    def copy_file(self, src_path, dst_dir):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.copy_file(src_path, dst_dir)

    def remote_copy_file(self, sftp, src_file, remote_dir):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.remote_copy_file(sftp, src_file,
                                             remote_dir)

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

    def get_free_listen_port(self):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.get_free_listen_port()

    def execute_cmd_bg(self, cmd, args):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.execute_cmd_bg(cmd, args)

    def wait_cmd_complete(self, process_obj):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined")
        return self.context.wait_cmd_complete(process_obj)

    def kill_process(self, process_obj):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.kill_process(process_obj)

    def is_remote_port_open(self, ip, port):
        if self.context is None:
            self.nv_log_handler.error("Platform not defined.")
        return self.context.is_remote_port_open(ip, port)
