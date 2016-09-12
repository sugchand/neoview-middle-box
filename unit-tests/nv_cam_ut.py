'''
Created on 11 Jul 2016

@author: sugesh
'''
import uuid
import sys
import os.path
import ipaddress


def setup_src_path():
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(os.path.abspath(os.path.join(curr_dir, os.pardir)))

def nv_test_camera_stream_in():
    setup_src_path()
    from src.nvdb.nvdb_manager import nv_camera,nv_midbox_system
    from src.nvcamera.cam_handler import cam_handler
    sys_id = (uuid.uuid4().int>>64) & 0xFFFFFFFF
    nv_sys_record = nv_midbox_system(sys_id = sys_id, name = "nv-system1")
    nv_cam_record1 = nv_camera(cam_id = (uuid.uuid4().int>>64) & 0xFFFFFFFF,
                               name = 'camera 1',
                               ip_addr = int(ipaddress.IPv4Address('192.168.192.32')),
                               mac_addr = "00:00:00:00:00:01",
                               listen_port = 9000,
                               stream_file_time_sec = 30,
                               username = 'admin',
                               password = 'sugu&deepu',
                               nv_midbox = nv_sys_record
                               )
    stream_handler = cam_handler(nv_cam_record1)
    stream_handler.save_camera_stream_in_multifile()

if __name__ == '__main__':
    nv_test_camera_stream_in()