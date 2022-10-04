'''
Copyright 2022 i-PRO Co., Ltd.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

'''
[Abstract]
    Skelton information application
    骨格情報活用アプリケーション

[Details]
    Analyze the skeleton information collected from VP skeleton detection and light up the patrol light.
    VP骨格検出から収集した骨格情報を分析してパトライトを光らせる。

[In working order (動作確認済み機器)]
    Module Camera: MK-DVASTNP01, MK-DVLTRNP01
    PATLITE:       NHP-3FB2-RYG, NHV4-3DP-RYG

[Author]
    Arai Takamitsu (i-PRO) and Ichiken

[Date]
    2022-10-03

[Version]
    1.0
'''

import libAdamApiPython
from datetime import datetime
import shutil
import threading
import hello
import time
import sys
import os

# 20210429
import websockets
import asyncio
import socket
import urllib.request as rq
import urllib.error as er
import json

serverIP = None
sendData = None
cnt = 0
loop = None
resoList = [(1920, 1080)]


def get_host_local_ip():
    """
    get local ip address of host.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()
    return ip


def stopCallback():
    """
    Get Callback function of stop.
    Stop loop function.
    """    
    global loop
    loop.exit()

def httpCallback(reqType, reqData):
    """
    Get Callback function of http.
    return: sample.htm
    """
    appPath = libAdamApiPython.adam_get_app_data_dir_path()
    fname = "%s/sample.htm" % appPath

    fp = open(fname, mode='r')
    htmlData = fp.read()
    bodySize = len(htmlData)
    fp.close()

    header = ""
    header = header + "HTTP/1.1 200 OK\r\n" \
                      "Content-Type: text/html\r\n" \
                      "Content-Length: %d\r\n" % (bodySize + 1)
    body = htmlData.encode('utf-8')
    return (header, body)

async def websocket_client():
    """
    Websocket client function.
    connect from front-end and send skelton data to front-end.
    determine alarm type(pose).
    """    
    global sendData
    pose_status = 0
# pose_status 0:手を下げていて、背筋が曲がっていない。もしくは人がいない 1:手を下げていて、背筋が曲がっている 2:手を挙げている
    level = libAdamApiPython.ADAM_LV_INF
    time.sleep(2)
    while serverIP is None:
        time.sleep(2)
#    async with websockets.connect('ws://192.168.0.10:8200') as websocket:
    async with websockets.connect('ws://'+serverIP+':8200') as websocket:
        libAdamApiPython.adam_debug_print(
            level, "Success to webSocket server.")
        while True:
            personData = await websocket.recv()
            sendData = personData
            json_dict = json.loads(personData)
            persons_num = 0
            try:
                for p in json_dict["persons"]:
                    libAdamApiPython.adam_debug_print(level, "exist persons")
                    if persons_num == 0:
                        persons_num = 1
                    else:
                        break
                    if 'body' in p:
                        libAdamApiPython.adam_debug_print(level, "exist persons body")
                        if 'nose' in p["body"]:
                            libAdamApiPython.adam_debug_print(level, "exist nose")
                            if 'wrist_left' in p["body"]:
                                libAdamApiPython.adam_debug_print(level, "exist wrist_left")
                                if 'wrist_right' in p["body"]:
                                    libAdamApiPython.adam_debug_print(level, "exist wrist_light")
                                    if p["body"]["nose"]["y"] > p["body"]["wrist_left"]["y"]:
                                        if p["body"]["nose"]["y"] > p["body"]["wrist_right"]["y"]:
                                            libAdamApiPython.adam_debug_print(level, "status:2")
                                            if pose_status != 2:
                                                pose_status = 2
                                                libAdamApiPython.adam_debug_print(level, "Alarms status:2")
                                                url = 'http://192.168.0.11/api/control?alert=120000'
                                                req = rq.Request(url)
                                                try:
                                                    with rq.urlopen(req,timeout=3) as res:
                                                        responsedt = res.read()
                                                except er.HTTPError as err:
                                                    libAdamApiPython.adam_debug_print(level, "HTTPError:%s" % err.code)
                                                except er.URLError as err:
                                                    libAdamApiPython.adam_debug_print(level, "URLError:%s" % err.reason)
                                            break
                            if 'shoulder_left' in p["body"]:
                                libAdamApiPython.adam_debug_print(level, "exist shoulder_left")
                                if 'shoulder_right' in p["body"]:
                                    libAdamApiPython.adam_debug_print(level, "exist shoulder_light")
                                    x_diff = abs(float(p["body"]["nose"]["x"])-(float(p["body"]["shoulder_left"]["x"])+float(p["body"]["shoulder_right"]["x"]))/2)
                                    y_diff = abs(float(p["body"]["nose"]["y"])-(float(p["body"]["shoulder_left"]["y"])+float(p["body"]["shoulder_right"]["y"]))/2)
                                    if y_diff != 0:
                                        if x_diff/y_diff >= 2:
                                            if pose_status != 1:
                                                pose_status = 1
                                                libAdamApiPython.adam_debug_print(level, "Alarms status:1")
                                                url = 'http://192.168.0.11/api/control?alert=001000'
                                                req = rq.Request(url)
                                                try:
                                                    with rq.urlopen(req,timeout=3) as res:
                                                        responsedt = res.read()
                                                except er.HTTPError as err:
                                                    libAdamApiPython.adam_debug_print(level, "HTTPError:%s" % err.code)
                                                except er.URLError as err:
                                                    libAdamApiPython.adam_debug_print(level, "URLError:%s" % err.reason)                                      
                                            break
                                    else:
                                        if pose_status != 1:
                                            pose_status = 1
                                            libAdamApiPython.adam_debug_print(level, "Alarms status:1")
                                            url = 'http://192.168.0.11/api/control?alert=001000'
                                            req = rq.Request(url)
                                            try:
                                                with rq.urlopen(req,timeout=3) as res:
                                                    responsedt = res.read()
                                            except er.HTTPError as err:
                                                libAdamApiPython.adam_debug_print(level, "HTTPError:%s" % err.code)
                                            except er.URLError as err:
                                                libAdamApiPython.adam_debug_print(level, "URLError:%s" % err.reason)
                            
                                        break
                    if pose_status != 0:
                        pose_status = 0
                        libAdamApiPython.adam_debug_print(level, "Alarms status:0")
                        url = 'http://192.168.0.11/api/control?alert=000000'
                        req = rq.Request(url)
                        try:
                            with rq.urlopen(req,timeout=3) as res:
                                responsedt = res.read()
                        except er.HTTPError as err:
                            libAdamApiPython.adam_debug_print(level, "HTTPError:%s" % err.code)
                        except er.URLError as err:
                            libAdamApiPython.adam_debug_print(level, "URLError:%s" % err.reason)


            except Exception as e:
                import traceback
                t = traceback.format_exc()
                libAdamApiPython.adam_debug_print(libAdamApiPython.ADAM_LV_ERR, (t))
                pose_status = 0

async def websocket_server(websocket, path):
    """
    Websocket Server function.
    transfer connect to skeleton_detection_app and get skelton data.
    """
    level = libAdamApiPython.ADAM_LV_INF
    libAdamApiPython.adam_debug_print(level, "WebSocket server:Open")
    global sendData
    while True:
        try:
            await websocket.send(sendData)
        except websockets.exceptions.ConnectionClosed:
            libAdamApiPython.adam_debug_print(level, "WebSocket server:Closing")
            break


def websocket_server_thread(thread_loop):
    """
    Start Websocket Server function.
    """
    level = libAdamApiPython.ADAM_LV_INF
    libAdamApiPython.adam_debug_print(level, "WebSocket server thread:Start")
    global serverIP

    serverIP = get_host_local_ip()
    while serverIP is None:
        time.sleep(2)
        serverIP = get_host_local_ip()

    asyncio.set_event_loop(thread_loop)
    start_server = websockets.serve(websocket_server, serverIP, 8081)
    thread_loop.run_until_complete(start_server)
    thread_loop.run_forever()


if __name__ == '__main__':
    """
    main function.
    """
    hello.hello()
    # set callback functions
    libAdamApiPython.adam_set_stop_callback(stopCallback)
    libAdamApiPython.adam_set_http_callback(httpCallback)
    level = libAdamApiPython.ADAM_LV_INF

    # Thread for WebSocket Server
    libAdamApiPython.adam_debug_print(level, "WebSocketServerfunction:Start")
    thread_loop = asyncio.new_event_loop()
    thread = threading.Thread(target=websocket_server_thread, args=(thread_loop,))
    thread.daemon = True
    thread.start()

    # WebSocket Client
    libAdamApiPython.adam_debug_print(level, "WebSocketclientfunction:Start")
    asyncio.run(websocket_client())
    libAdamApiPython.adam_debug_print(level, "Application:End")
