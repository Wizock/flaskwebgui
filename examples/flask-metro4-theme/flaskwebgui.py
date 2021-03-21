import psutil
import os, time
import sys, subprocess as sps
import logging
from threading import Thread
from datetime import datetime
import asyncio
import datetime
import websockets
import logging
import json
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


        
class FlaskUI:
    """
        This class opens in 3 threads the browser, the flask server, and a thread which closes the server if GUI is not opened
        
        Described Parameters:

        app,                              ==> flask  class instance 
        width=800                         ==> default width 800 
        height=600                        ==> default height 600
        fullscreen=False,                 ==> start app in fullscreen mode
        maximized=False,                  ==> start app in maximized window
        app_mode=True                     ==> by default it will start the application in chrome app mode
        browser_path="",                  ==> full path to browser.exe ("C:/browser_folder/chrome.exe")
                                              (needed if you want to start a specific browser)
        server="flask"                    ==> the default backend framework is flask, but you can add a function which starts 
                                              the desired server for your choosed framework (django, bottle, web2py pyramid etc)
        host="localhost"                  ==> specify other if needed
        port=5000                         ==> specify other if needed
        socketio                          ==> specify flask-socketio instance if you are using flask with socketio
        on_exit                           ==> specify on-exit function which will be run before closing the app

    """

    def __init__(self, app=None, width=800, height=600, fullscreen=False, maximized=False, app_mode=True,  browser_path="", server="flask", host="127.0.0.1", port=5000, socketio=None, on_exit=None):
        self.flask_app = app
        self.width = str(width)
        self.height= str(height)
        self.fullscreen = fullscreen
        self.maximized = maximized
        self.app_mode = app_mode
        self.browser_path = browser_path if browser_path else self.get_default_chrome_path()  
        self.server = server
        self.host = host
        self.port = port
        self.socketio = socketio
        self.on_exit = on_exit
        self.localhost = "http://{}:{}/".format(host, port) # http://127.0.0.1:5000/
        self.BROWSER_PROCESS = None
        
    def run(self):
        """
            Start the flask and gui threads instantiated in the constructor func
        """
        

        with ThreadPoolExecutor() as tex:
            tex.submit(self.run_web_server)
            tex.submit(self.open_browser)
            tex.submit(self.keep_alive_web_server)
            

        

    def run_web_server(self):
        """
            Run flask or other framework specified
        """

        if isinstance(self.server, str):
            if self.server.lower() == "flask":
                if self.socketio:
                    self.socketio.run(self.flask_app, host=self.host, port=self.port)
                else:
                    self.flask_app.run(host=self.host, port=self.port, threaded=True)

            elif self.server.lower() == "django":
                if sys.platform in ['win32', 'win64']:
                    os.system("python manage.py runserver {}:{}".format(self.host, self.port))
                else:
                    os.system("python3 manage.py runserver {}:{}".format(self.host, self.port))
            else:
                raise Exception("{} must be a function which starts the webframework server!".format(self.server))
        else:
            self.server()

    def get_default_chrome_path(self):
        """
            Credits for get_instance_path, find_chrome_mac, find_chrome_linux, find_chrome_win funcs
            got from: https://github.com/ChrisKnott/Eel/blob/master/eel/chrome.py
        """
        if sys.platform in ['win32', 'win64']:
            return FlaskUI.find_chrome_win()
        elif sys.platform in ['darwin']:
            return FlaskUI.find_chrome_mac()
        elif sys.platform.startswith('linux'):
            return FlaskUI.find_chrome_linux()

    @staticmethod
    def find_chrome_mac():
        default_dir = r'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        if os.path.exists(default_dir):
            return default_dir
        # use mdfind ci to locate Chrome in alternate locations and return the first one
        name = 'Google Chrome.app'
        alternate_dirs = [x for x in sps.check_output(["mdfind", name]).decode().split('\n') if x.endswith(name)] 
        if len(alternate_dirs):
            return alternate_dirs[0] + '/Contents/MacOS/Google Chrome'
        return None

    @staticmethod
    def find_chrome_linux():
        try:
            import whichcraft as wch
        except Exception as e:
            raise Exception("whichcraft module is not installed/found  \
                             please fill browser_path parameter or install whichcraft!") from e

        chrome_names = ['chromium-browser',
                        'chromium',
                        'google-chrome',
                        'google-chrome-stable']

        for name in chrome_names:
            chrome = wch.which(name)
            if chrome is not None:
                return chrome
        return None

    @staticmethod
    def find_chrome_win():
        import winreg as reg
        reg_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe'

        chrome_path = None
        last_exception = None

        for install_type in reg.HKEY_CURRENT_USER, reg.HKEY_LOCAL_MACHINE:
            try:
                reg_key = reg.OpenKey(install_type, reg_path, 0, reg.KEY_READ)
                chrome_path = reg.QueryValue(reg_key, None)
                reg_key.Close()
            except WindowsError as e:
                last_exception = e
            else:
                if chrome_path and len(chrome_path) > 0:
                    break

        # Only log some debug info if we failed completely to find chrome
        if not chrome_path:
            logging.exception(last_exception)
            logging.error("Failed to detect chrome location from registry")
        else:
            logging.debug(f"Chrome path detected as: {chrome_path}")

        return chrome_path

    def open_browser(self):
        """
            Open the browser selected (by default it looks for chrome)
        """

        if self.app_mode:
            launch_options = None
            if self.fullscreen:
                launch_options = ["--start-fullscreen"]
            elif self.maximized:
                launch_options = ["--start-maximized"]
            else:
                launch_options = ["--window-size={},{}".format(self.width, self.height)]

            options = [self.browser_path, "--new-window", '--app={}'.format(self.localhost)]
            options.extend(launch_options)

            self.BROWSER_PROCESS = sps.Popen(options,
                                             stdout=sps.PIPE, stderr=sps.PIPE, stdin=sps.PIPE)
        else:
            import webbrowser
            webbrowser.open_new(self.localhost)


    @staticmethod
    def kill_pids_by_ports(*ports):
        connections = psutil.net_connections()
        for conn in connections:
            open_port = conn.laddr[1]
            if open_port in ports:
                psutil.Process(conn.pid).kill()



    def keep_alive_web_server(self):

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def keep_alive(self, websocket, path):
            
            logging.warning('waiting..')

            async for msg in websocket:
                data = json.loads(msg)
                
                logging.warning(data)

                last_request_time = datetime.strptime(data['timestamp'], "%Y-%m-%d %H:%M:%S")
                diff = datetime.now() - last_request_time

                if diff.total_seconds() > 10:
                    if self.on_exit: self.on_exit()
                    FlaskUI.kill_pids_by_ports(self.port, self.port+1)
        

        server = websockets.serve(keep_alive, self.host, self.port+1)
        loop.run_coroutine_threadsafe(server)
        loop.run_forever()

        # loop.run_until_complete(server)
        # loop.run_forever()

        # asyncio.get_event_loop().run_until_complete(server)
        # asyncio.get_event_loop().run_forever()

        return server


    # @staticmethod
    # def keep_alive_web_server(self):
    #     """
    #         If no get request comes from browser on port + 1 
    #         then after 10 seconds the server will be closed 
    #     """

    #     logging.warning("keep_alive_web_server")

    #     server = self.create_ws_server()
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # loop.run_until_complete(server)
        # loop.run_forever()

        