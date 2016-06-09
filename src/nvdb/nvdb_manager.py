#! /usr/bin/python
# -*- coding: utf8 -*-
# The database manager module for nv-middlebox.
#
# Use this file to interact with DB.

__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from settings import NVDB_SQLALCHEMY_DB
from nv_logger import nv_log_handler

db_base = declarative_base()

class nv_midbox_system(db_base):
    '''
    The table model to store nv-middlebox system configurations
    '''
    __tablename__ = 'nv_midbox'
    id = Column(Integer, primary_key = True)
    name = Column(String)
    # TODO :: More details to be added.

    def __repr__(self):
        return "<nv_midbox_system(id=%d)>" % self.id

class nv_camera(db_base):
    '''
    The table model to hold the camera parameters
    '''
    __tablename__ = 'nv_camera'
    id = Column(Integer, primary_key = True)
    name = Column(String, nullable = False, unique = True)
    ip_addr = Column(Integer, nullable = False, unique = True)
    mac_addr = Column(String, nullable = False, unique = True)
    port = Column(Integer, nullable = False)
    username = Column(String, nullable = False)
    password = Column(String, nullable = False)
    src_protocol = Column(Integer)
    active_conn = Column(Integer,  default = 0)
    nv_midbox_id = Column(Integer,  ForeignKey('nv_midbox.id'))
    nv_midbox = relationship(nv_midbox_system,
                            backref=backref('nv_cameras',
                                            uselist=True,
                                            cascade='delete,all'))

    def __repr__(self):
        return "<nv_camera(id=%d name='%s', ip_addr='%d', mac_addr='%s') \
                port=%d, username=%s, password=%s, src_protocol=%d, \
                active_conn=%d, nv_midbox_id=%d)>" % (self.id, self.name, \
                self.ip_addr, self.mac_addr, self.port, \
                self.username, self.password, self.src_protocol, \
                self.active_conn, self.nv_midbox_id)


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
        self.db_engine = create_engine(NVDB_SQLALCHEMY_DB)
        self.db_session_cls = sessionmaker(bind=self.db_engine)
        db_base.metadata.create_all(self.db_engine)
        nv_log_handler.debug("Tables created in nvdb")

    def setup_session(self):
        if self.db_session is None:
            nv_log_handler.debug("NULL db session, create a new one..")
            self.db_session = self.db_session_cls()

    def add_record(self, record_obj):
        nv_log_handler.debug("Adding a new record")
        self.db_session.add(record_obj)

    def db_commit(self):
        nv_log_handler.debug("Committing the changes to DB.")
        self.db_session.commit()

    def delete_record(self, record_obj):
        nv_log_handler.debug("Delete a record from table")
        self.db_session.delete(record_obj)

    def clean_table(self, table_name):
        for row in self.db_session.query(table_name).all():
            self.db_session.delete(row)
        nv_log_handler.debug("Cleaning the table %s", table_name.__name__)

    def get_tbl_record_cnt(self, table_name):
        nv_log_handler.debug("Get number of records in %s",
                               table_name.__name__)
        return self.db_session.query(table_name).count()

    def get_tbl_records(self, table_name):
        nv_log_handler.debug("Collect all records in %s", table_name.__name__)
        return self.db_session.query(table_name).all()


db_mgr_obj = db_manager()