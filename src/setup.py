#! /usr/bin/python3
# -*- coding: utf8 -*-
# The middlebox software for remote camera management and relay streaming.
#
__author__ = "Sugesh Chandran"
__copyright__ = "Copyright (C) The neoview team."
__license__ = "GNU Lesser General Public License"
__version__ = "1.0"

from distutils.core import setup

setup(
      name='Neoview-Middlebox',
      version='0.1',
      license = 'Neoview Team, GNU public licence',
      description = "Neoview middlebox Streaming",
      author = "Sugesh Chandran",
      author_email = "sugeshchandran@gmail.com",
      url = "www.neoview.ie",
      long_description="Middlebox software to relay video streams from cameras"
                        "to the webserver",
      platforms = "python-3(linux)",
#      packages=[],
      include_package_data=True
      )
