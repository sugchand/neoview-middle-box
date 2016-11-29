#! /usr/bin/python3
# -*- coding: utf8 -*-
# The web interface to program/configure the middlebox.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"
from bottle import request, get, post

def check_login():
    pass

@get('/login') # or @route('/login')
def login():
    return '''
        <form action="/login" method="post">
        Username: <input name="username" type="text" />
        Password: <input name="password" type="password" />
        <input value="Login" type="submit" />
        </form>
    '''

@post('/login') # or @route('/login', method='POST')
def do_login():
    username = request.forms.get('username')
    password = request.forms.get('password')
    if check_login(username, password):
        return "<p>Your login information was correct.</p>"
    else:
        return "<p>Login failed.</p>"

class midbox_web():

    def __init__(self):
        
        pass

    def start_webserver(self):
        pass

    def stop_webserver(self):
        pass

midbox_web_obj = midbox_web()