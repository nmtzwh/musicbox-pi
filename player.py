import subprocess
# import threading
# import time
# import os
# import signal
# import random
# import re
# from ui import Ui
# from storage import Storage
# from api import NetEase
# from cache import Cache
# from config import Config
# import logger

class Player:
    def __init__(self):
        self.popen_handler = None
        # flag stop, prevent thread start
        self.playing_flag = False
        self.stop_flag = True
        # self.process_length = 0
        # self.process_location = 0
        # self.process_first = False
        # self.storage = Storage()
        # self.info = self.storage.database["player_info"]
        # self.songs = self.storage.database["songs"]
        # self.playing_id = -1
        # self.cache = Cache()
        # self.notifier = self.config.get_item("notifier")
        # self.mpg123_parameters = self.config.get_item("mpg123_parameters")
        # self.end_callback = None
        # self.playing_song_changed_callback = None

    def stop(self):
        if self.playing_flag and self.popen_handler:
            self.playing_flag = False
            self.stop_flag = True
            try:
                self.popen_handler.kill()
            except:
                return

    def playUrl(self, url_list):
        # http://linux.die.net/man/1/mpg123
        para = ['mpg123', '-z']
        for url in url_list:
            para.append(str(url))
        # print para
        if self.playing_flag: self.popen_handler.kill()
        while True:
            try:
                self.popen_handler = subprocess.Popen(para, stdin=subprocess.PIPE,
                                                            stdout=subprocess.PIPE,
                                                            stderr=subprocess.PIPE)
                self.playing_flag = True
                self.stop_flag = False
                break
            except socket.error, e:
                if isinstance(e.args, tuple):
                    print "errno is %d" % e[0]
                    if e[0] == errno.EPIPE:
                       # remote peer disconnected
                       print "Detected remote disconnect"
                    else:
                       # determine and handle different error
                       pass
                else:
                    print "socket error ", e
                self.popen_handler.close()
            except IOError, e:
                    # Hmmm, Can IOError actually be raised by the socket module?
                    print "Got IOError: ", e
                    break

        
        



