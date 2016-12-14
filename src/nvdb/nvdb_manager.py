#! /usr/bin/python
# -*- coding: utf8 -*-
# The database manager module for nv-middlebox.
#
# Use this file to interact with DB.

__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

import uuid
from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from src.settings import NVDB_SQLALCHEMY_DB
from src.nv_logger import nv_logger
from src.settings import NV_MID_BOX_APP_NAME
from sqlalchemy.pool import StaticPool

db_base = declarative_base()

class nv_midbox_system(db_base):
    '''
    The table model to store nv-middlebox system configurations
    '''
    __tablename__ = 'nv_midbox'
    sys_id = Column(Integer, primary_key = True)
    name = Column(String)
    # TODO :: More details to be added.

    def __repr__(self):
        return "<nv_midbox_system(sys_id=%d)>" % self.sys_id

class nv_webserver_system(db_base):
    '''
    The table to hold the webserver credentials.
    '''
    __tablename__ = 'nv_webserver'
    server_id = Column(Integer, primary_key = True)
    name = Column(String, nullable = False, default = 'localhost')
    video_path = Column(String, nullable = False)

    def __repr__(self):
        return "<nv_webserver(server_id=%d), name = %s, dst_path = %s>" % \
                (self.sys_id, self.name, self.video_path)

class enum_camStatus():
    CONST_CAMERA_NEW = 0 # OFF state/Invalid state.
    CONST_CAMERA_READY = 1 # ON state, not recording.
    CONST_CAMERA_RECORDING = 2 # ON and recording.
    # Camera/thread is busy, cannot do any operation now.
    CONST_CAMERA_DEFERRED = 3

class nv_camera(db_base):
    '''
    The table model to hold the camera parameters
    '''
    __tablename__ = 'nv_camera'
    cam_id = Column(Integer, primary_key = True)
    name = Column(String, nullable = False, unique = True)
    status = Column(Integer) # Should be the enum type enum_camStatus
    desc = Column(String) # Camera description.
    ip_addr = Column(Integer, nullable = False, unique = True)
    mac_addr = Column(String, nullable = False, unique = True)
    listen_port = Column(Integer, nullable = False)
    username = Column(String, nullable = False)
    password = Column(String, nullable = False)
    src_protocol = Column(Integer, default = 554)
    # Number of streaming files
    stream_file_cnt = Column(Integer, default = 0)
    # The size of each stream file in seconds, default is 60 seconds
    stream_file_time_sec = Column(Integer, default = 60)
    #Number of active connections to the camera.
    active_conn = Column(Integer,  default = 0)
    nv_midbox_id = Column(Integer,  ForeignKey('nv_midbox.sys_id'))
    nv_midbox = relationship(nv_midbox_system,
                            backref=backref('nv_cameras',
                                            uselist=True,
                                            cascade='delete,all'))

    def __repr__(self):
        return "<nv_camera(cam_id=%d name='%s', ip_addr='%d', mac_addr='%s') \
                listen_port=%d, username=%s, password=%s, src_protocol=%d, \
                stream_file_cnt=%d, stream_file_time_sec=%d, \
                active_conn=%d, nv_midbox_id=%d), status = %d, \
                desc = %s >" % (self.cam_id, self.name, \
                self.ip_addr, self.mac_addr, self.listen_port, \
                self.username, self.password, self.src_protocol, \
                self.stream_file_cnt, self.stream_file_time_sec, \
                self.active_conn, self.nv_midbox_id, \
                self.status, self.desc)


class db_manager():
    '''
    DB manager class to track and manage DB operations. 
    NOTE :: Isolation is not inherent with db manager implementation. So in 
    multithreaded implementation, its responsibility of caller to take care of
    it.
    '''
    db_engine = None
    db_session_cls = None #Session Maker factory class
    db_session = None

    def __init__(self):
        self.nv_log_handler = nv_logger(self.__class__.__name__).get_logger()
        self.db_engine = create_engine(NVDB_SQLALCHEMY_DB,
                                    connect_args={'check_same_thread': False},
                                    poolclass=StaticPool, echo=False)
        session_maker = sessionmaker(bind=self.db_engine)
        self.db_session_cls = session_maker()
        db_base.metadata.create_all(self.db_engine)
        self.nv_midbox_db_entry = None
        self.nv_webserver = None
        self.nv_log_handler.debug("Tables created in nvdb")

    def setup_session(self):
        if self.db_session is None:
            self.nv_log_handler.debug("NULL db session, create a new one..")
            self.db_session = self.db_session_cls

    def init_webserver_params(self, webserver_db_entry):
        if self.db_session is None:
            self.nv_log_handler.error("Can't create webserver record, "
                                      "DB session is not initialized")
            return
        if self.nv_webserver is not None:
            self.nv_log_handler.error("Cannot create multiple webserver for"
                                    "same machine")
            return
        self.nv_webserver = webserver_db_entry
        self.nv_log_handler.info("Setting the webserver DB record %d"
                                 % webserver_db_entry.server_id)
        self.add_record(self.nv_midbox_db_entry)
        self.db_commit()

    def del_webserver(self):
        if self.db_session is None:
            self.nv_log_handler.error("Can't create webserver record, "
                                      "DB session is not initialized")
            return
        if self.nv_webserver is None:
            self.nv_log_handler.error("Cannot delete non-existant webserver"
                                    " instance")
            return
        self.clean_table(table_name=nv_webserver_system)

    def create_system_record(self):
        if self.db_session is None:
            self.nv_log_handler.error("Can't create system record, "
                                      "DB session is not initialized")
            return
        if self.nv_midbox_db_entry is not None:
            self.nv_log_handler.error("Cannot create multiple system entries for"
                                      "same machine")
            return
        sys_id = (uuid.uuid4().int>>64) & 0xFFFFFFFF
        self.nv_midbox_db_entry = nv_midbox_system(sys_id = sys_id,
                                      name = NV_MID_BOX_APP_NAME)
        self.nv_log_handler.info("Setting the middlebox DB record %d" % sys_id)
        self.add_record(self.nv_midbox_db_entry)
        self.db_commit()

    def get_own_system_record(self):
        return self.nv_midbox_db_entry

    def get_webserver_record(self):
        return self.nv_webserver

    def add_record(self, record_obj):
        self.nv_log_handler.debug("Adding a new record")
        self.db_session.add(record_obj)

    def db_commit(self):
        self.nv_log_handler.debug("Committing the changes to DB.")
        self.db_session.commit()

    def delete_record(self, record_obj):
        self. nv_log_handler.debug("Delete a record from table")
        self.db_session.delete(record_obj)

    def clean_table(self, table_name):
        '''
        Params:
            table_name : the table class name, just pass the class name as is.
        '''
        for row in self.db_session.query(table_name).all():
            self.db_session.delete(row)
        self.nv_log_handler.debug("Cleaning the table %s", table_name.__name__)

    def get_tbl_record_cnt(self, table_name):
        '''
        Params:
            table_name : the table class name, just pass the class name as is.
        '''
        self.nv_log_handler.debug("Get number of records in %s",
                               table_name.__name__)
        return self.db_session.query(table_name).count()

    def get_tbl_records(self, table_name):
        '''
        Params:
            table_name : the table class name, just pass the class name as is.
        '''
        self.nv_log_handler.debug("Collect all records in %s", table_name.__name__)
        return self.db_session.query(table_name).all()

    def get_tbl_records_filterby(self, table_name, kwargs):
        '''
        Params:
            table_name : the table class name, just pass the class name as is.
            kwargs : the filter argument to be used in filter.
        '''
        '''
        the kwargs must be dictionary, for eg: to get all the records matches
        a name the kwargs will be
        kwargs = {'name' : 'sugu'}
        '''
        self.nv_log_handler.debug("Collect records using filter %s"
                                  % ' '.join(list(kwargs)))
        return self.db_session.query(table_name).filter_by(**kwargs).all()

    def get_tbl_records_filterby_first(self, table_name, kwargs):
        '''
        the kwargs must be dictionary, for eg: to get all the records matches
        a name the kwargs will be
        kwargs = {'name' : 'sugu'}
        table_name : the table class name, just pass the class name as is.
        '''
        self.nv_log_handler.debug("Collect records using filter %s"
                                  % ' '.join(list(kwargs)))
        return self.db_session.query(table_name).filter_by(**kwargs).first()

    def get_tbl_records_filterby_cnt(self, table_name, kwargs):
        '''
        the kwargs must be dictionary, for eg: to get all the records matches
        a name the kwargs will be
        kwargs = {'name' : 'sugu'}
        table_name : the table class name, just pass the class name as is.
        '''
        self.nv_log_handler.debug("Collect records using filter %s"
                                  % ' '.join(list(kwargs)))
        return self.db_session.query(table_name).filter_by(**kwargs).count()

db_mgr_obj = db_manager()

