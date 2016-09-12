#! /usr/bin/python3
# -*- coding: utf8 -*-
# The UT test case functions for nv-db.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import uuid
import sys
import os.path
import ipaddress

def setup_src_path():
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(os.path.abspath(os.path.join(curr_dir, os.pardir)))

def setup_db_ut():
    from src.nvdb.nvdb_manager import db_mgr_obj, nv_camera, nv_midbox_system
    db_mgr_obj.setup_session()
    print("Neoview Midbox system table record count %d"
          % db_mgr_obj.get_tbl_record_cnt(nv_midbox_system))
    print ("Neoview nv_camera record count %d"
           % db_mgr_obj.get_tbl_record_cnt(nv_camera))

    sys_id = (uuid.uuid4().int>>64) & 0xFFFFFFFF
    nv_sys_record = nv_midbox_system(sys_id = sys_id, name = "nv-system1")
    nv_cam_record1 = nv_camera(cam_id = (uuid.uuid4().int>>64) & 0xFFFFFFFF,
                               name = 'camera 1',
                               ip_addr = int(ipaddress.IPv4Address('10.10.10.1')),
                               mac_addr = "00:00:00:00:00:01",
                               listen_port = 1234,
                               username = 'test',
                               password = 'test123',
                               nv_midbox = nv_sys_record
                               )
    nv_cam_record2 = nv_camera(cam_id = (uuid.uuid4().int>>64) & 0xFFFFFFFF,
                               name = 'camera 2',
                               ip_addr = int(ipaddress.IPv4Address('10.10.10.2')),
                               mac_addr = "00:00:00:00:00:02",
                               listen_port = 1234,
                               username = 'test',
                               password = 'test123',
                               nv_midbox = nv_sys_record
                               )
    db_mgr_obj.add_record(nv_sys_record)
    db_mgr_obj.add_record(nv_cam_record1)
    db_mgr_obj.add_record(nv_cam_record2)
    db_mgr_obj.db_commit()
    print("Neoview Midbox system table record count %d"
          % db_mgr_obj.get_tbl_record_cnt(nv_midbox_system))
    print ("Neoview nv_camera record count %d"
           % db_mgr_obj.get_tbl_record_cnt(nv_camera))
    print(db_mgr_obj.get_tbl_records(nv_midbox_system))
    print(db_mgr_obj.get_tbl_records(nv_camera))

def main():
    setup_src_path()
    setup_db_ut()
    print("The test completed successfully")

main()