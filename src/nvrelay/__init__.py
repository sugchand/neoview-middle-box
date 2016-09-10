'''
Created on 10 Sep 2016

@author: sugesh
'''

#! /usr/bin/python3
# -*- coding: utf8 -*-
# The camera handler module for nv-middlebox. 
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"
'''
    Relay the generated camera streams to the webserver. 
    If webserver and middlebox are in the same machine, the agent does
    the local copying of files. The copy has to be remote FTP when the webserver
    is deployed in different location
'''
