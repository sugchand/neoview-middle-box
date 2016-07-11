'''
Created on 11 Jul 2016

@author: sugesh
'''

def nv_cam_test_static_video():
    pass

def nv_test_camera_stream_in():
    sys_id = (uuid.uuid4().int>>64) & 0xFFFFFFFF
    nv_sys_record = nv_midbox_system(id = sys_id, name = "nv-system1")
    nv_cam_record1 = nv_camera(id = (uuid.uuid4().int>>64) & 0xFFFFFFFF,
                               name = 'camera 1',
                               ip_addr = int(ipaddress.IPv4Address('10.10.10.1')),
                               mac_addr = "00:00:00:00:00:01",
                               port = 1234,
                               username = 'test',
                               password = 'test123',
                               nv_midbox = nv_sys_record
                               )
if __name__ == '__main__':
    pass