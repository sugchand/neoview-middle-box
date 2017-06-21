# neoview-middle-box
The transparent middlebox software running on a local server to relay the camera recording to the webserver.

## Architecture




                                                    s/w switch
                                                     +------+
                                                     |      |
                                                     | +--+ +----+
                                                     +------+    |
                                                       +--+      |
                +------------+                                   |
                |            |                                   |            +-----------+
                |    cam-1   +------------------------------+    |            |           |
                |            |                              |    |            |           |
                +------------+                              |    |            |           |
                                                   +-----------------+        |     W     |
                +------------+                     |                 |        |     e     |
                |            |                     |                 <--------+     b     |
                |    cam-2   +---------------------+   Middle-Box    +-------->           |
                |            |                     |                 |        |     S     |
                +------------+                     +-----------------+        |     e     |
                                                            |                 |     r     |
                      +                                     |                 |     v     |
                      |                                     |                 |     e     |
                      +                                     |                 |     r     |
                                                            |                 |           |
                +------------+                              |                 |           |
                |            |                              |                 +-----------+
                |    cam-n   |                              |
                |            +------------------------------+
                +------------+


### cam1 ... cam-n
The list of network cameras that can send video feed in rtsp.

### Middle-Box
The middlebox software in this repository does the camera streaming.

* Stream the video recording from the connected/configured cameras. Each camera
recordings are saved as multiple files into local storage. The size of each file
(lengh of video in minutes) can be configured in the middlebox.
* Provide CLI to configure the middlebox.
* offer a web-based s/w switch to control the camera streaming. User can turn
ON/OFF the camera streaming using this switch.
* The relay module copies the video files to the webserver. Webserver stream-out
these files to the user. Webserver software is not part of this source repo.

### S/W switch
A webpage that user can use to control the camera streaming. The webserver
running in middlebox box serves this webpage. It displys the camera details to
the user that configured in the middlebox.  The switch webpage is a software
substitue of real physical switch for camera ON and OFF.

It must be noted that the webserver also hosted webpages for the user.
These webpages are meant for normal-user/public who wanted to view the streaming.

### Web server
The web server is standard web server suite to display the streaming video to the
public. The webserver implementation is not under the scope of this project.
Middlebox copies the camera video chunks to the predefined directory in
webserver. Middlebox also propagate camera state information to the webserver on
a change event.

## How to Use

* Install the media player library vlc and non-X window libraries. The
installation can be done as below on a Ubuntu(Debian) machine.

  `apt-get install vlc`

  `apt-get install vlc-nox`

  `apt-get install ffmpeg`

* Install dependency packages for the middlebox as below

  `apt-get install python-pip python3-pip python-dev python3-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev libjpeg8-dev zlib1g-dev`

  `pip3 install cryptography`

* [OPTIONAL] Install the virtual environment if not present. This step is needed only when
middlebox is running in virtual environment.

  `apt-get install virtualenv`

* [OPTIONAL] Create a new virtual environment if not present.

  `virtualenv middlebox`

  middlebox is the name of new virtualenv.

* [OPTIONAL] Activate the virtualenv

  `source middlebox/bin/activate` or `. middlebox/bin/activate`

* Install the prerequisite libraries for the software.

  `pip3 install -r requirements.txt`

* Setup initial middlebox static configuration in the file  `src/settings.py`

* Start the middlebox software by

  `./src/nv_middlebox.py`

* Configure webserver and camera details using CLI options.

* [OPTIONAL] deactivate the virtualenv if used

  `deactivate`
