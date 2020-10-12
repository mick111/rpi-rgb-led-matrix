#!/usr/bin/python3
# -*- coding: utf-8 -*-

import socketserver
import glob
import time
import urllib2
from PIL import Image

# To create a Threaded TCP Server for each connexion
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def gif_to_imgs(im, duration=0.05):
    ims = []
    try:
        while 1:
            im.seek(im.tell() + 1)
            imduration = float(im.info["duration"]) / 1000.0
            imo = Image.new("RGB", (16, 16), "black")
            pix = im.convert("RGB").load()
            pixo = imo.load()
            for x in range(8):
                for y in range(8):
                    pixo[(2 * x, 2 * y)] = pix[(x, y)]
                    pixo[(2 * x, 2 * y + 1)] = pix[(x, y)]
                    pixo[(2 * x + 1, 2 * y)] = pix[(x, y)]
                    pixo[(2 * x + 1, 2 * y + 1)] = pix[(x, y)]
            ims.extend([imo] * max(1, int(imduration / duration)))
    except EOFError:
        pass
    if len(ims) > 0:
        # first image to be shown will be the 16 % len(ims) th
        first_img = 16 if len(ims) > 16 else (16 % len(ims))
        ims = (
            ims[first_img:] + ims[:first_img]
        )  # We put the first_img last items at the begining to make it start by the first one
    return ims

# To create the handler for the server
class ServerHandler(socketserver.BaseRequestHandler):
    # Nothing pecular to do on setup
    def setup(self):
        pass

    def HTTP_process(self, command, commands):
        if len(commands) == 1:
            # Serves a dummy page
            self.request.sendall(
                """HTTP/1.1 200 OK\r\nDate: Sun, 19 Mar 2017 21:13:55 GMT\r\nServer: Apache/2.4.23 (Unix)\r\nVary: negotiate\r\nTCN: choice\r\nLast-Modified: Mon, 11 Jun 2007 18:53:14 GMT\r\nETag: "2d-432a5e4a73a80"\r\nContent-Type: text/html\r\n\r\n<html><body><h1>This is not a website...</h1><h6>Perdu!</h6></body></html>\r\n"""
            )
            return

        if commands[1].startswith("/CLEAR"):
            # Reset the server
            self.server.server_runner.reset()
            self.server.server_runner.timeBeforeIdle = time.time()
        elif commands[1].startswith("/HISTORY"):
            # Get History of commands and serves a web page
            history = self.server.server_runner.getHistory()
            self.request.sendall(
                """HTTP/1.1 200 OK\r\nDate: Sun, 19 Mar 2017 21:13:55 GMT\r\nServer: Apache/2.4.23 (Unix)\r\nVary: negotiate\r\nTCN: choice\r\nLast-Modified: Mon, 11 Jun 2007 18:53:14 GMT\r\nETag: "2d-432a5e4a73a80"\r\nContent-Type: text/html\r\n\r\n<html><body>{}</body></html>\r\n""".format(
                    "<br/>".join(history)
                )
            )

    def handle(self):
        # Receive a new connection from the outside world

        # Buffer containing the data
        databuffer = ""

        # Keep connection alive with an infinite loop
        while True:
            # Read some data, and collect it in the databuffer
            # If there is a '\n' in the databuffer, then it contains a command to treat
            if "\n" not in databuffer:
                # Wait for some data
                datarecv = self.request.recv(1024)
                # Received data is None if the client disconnected.
                # We go outside the infinite loop
                if not datarecv:
                    break
                # We append the received data in the buffer
                databuffer += datarecv

            # Parse received data. Commands must be ended by '\n'
            datasplit = databuffer.split("\n", 1)

            # In this case, there is no '\n' yet
            if len(datasplit) < 2:
                continue

            # We extract the command to treat, we keep the rest for later
            data, databuffer = datasplit[0].strip(), datasplit[1]

            # Go on next command if empty
            if data == "":
                continue

            # Parse content to get the first word
            commands = data.split(" ", 1)
            command = commands[0].strip().upper()
            arguments = commands[1] if len(commands) > 1 else None

            # Command dispatch
            if command == "CLEAR":
                self.server.server_runner.reset()
                self.server.server_runner.timeBeforeIdle = time.time()
                pass
            elif command == "HOUR":
                self.server.server_runner.reset()
                self.server.server_runner.addToHistory(
                    "[" + self.client_address[0] + "] " + data
                )
                self.server.server_runner.timeBeforeIdle = time.time() + 30
                self.server.server_runner.hour = True

            elif command == "EVENT" and arguments:
                self.server.server_runner.reset()
                self.server.server_runner.addToHistory(
                    "[" + self.client_address[0] + "] " + data
                )
                event = arguments.strip().upper()
                if event not in EVENTS:
                    self.addToHistory("EVENT {} NOT REGISTERED".format(event))
                    pass
                self.server.server_runner.showEvent(event)

            elif command == "URLGIF" and arguments:
                commands = data.split(" ")
                self.server.server_runner.reset()
                self.server.server_runner.addToHistory(
                    "[" + self.client_address[0] + "] " + data
                )
                self.server.server_runner.timeBeforeIdle = time.time() + (
                    float(commands[2]) if len(commands) > 2 else 10
                )
                duration = 0.05
                ims = None
                im = Image.open(urllib2.urlopen(commands[1]))
                if ".gif" in commands[1]:
                    ims = gif_to_imgs(im, duration)
                else:
                    imo = Image.new("RGB", (16, 16), "black")
                    pix = im.convert("RGB").load()
                    pixo = imo.load()
                    for x in range(8):
                        for y in range(8):
                            pixo[(2 * x, 2 * y)] = pix[(x, y)]
                            pixo[(2 * x, 2 * y + 1)] = pix[(x, y)]
                            pixo[(2 * x + 1, 2 * y)] = pix[(x, y)]
                            pixo[(2 * x + 1, 2 * y + 1)] = pix[(x, y)]
                    ims = [imo]
                self.server.server_runner.images = ims
                self.server.server_runner.imageBackgroundColorRGB = (0, 0, 0)
                self.server.server_runner.pos = 16
                self.server.server_runner.sleeptime = duration

            elif command == "IMAGES" and len(commands) > 1:
                self.server.server_runner.reset()
                self.server.server_runner.addToHistory(
                    "[" + self.client_address[0] + "] " + data
                )
                self.server.server_runner.timeBeforeIdle = time.time() + 4 * len(
                    self.server.server_runner.images
                )
                # Show images from specific folder
                self.server.server_runner.imageBackgroundColorRGB = (0, 0, 0)
                self.server.server_runner.images = [
                    Image.open(i).convert("RGB") for i in sorted(glob.glob(commands[1]))
                ]
                self.server.server_runner.pos = 0
                self.server.server_runner.sleeptime = 2
            elif command == "NYAN" or command == "NYAN32":
                self.server.server_runner.reset()
                self.server.server_runner.addToHistory(
                    "[" + self.client_address[0] + "] " + data
                )
                self.server.server_runner.timeBeforeIdle = time.time() + 30
                # Show NyanCat
                self.server.server_runner.imageBackgroundColorRGB = (3, 37, 83)
                self.server.server_runner.images = [
                    Image.open(i).convert("RGB")
                    for i in sorted(glob.glob("Nyan1664/*.gif"))
                ]
                self.server.server_runner.pos = -64 if command == "NYAN" else -32
                self.server.server_runner.sleeptime = 0.07
            elif command == "TEXT" and len(commands) > 1:
                self.server.server_runner.reset()
                self.server.server_runner.addToHistory(
                    "[" + self.client_address[0] + "] " + data
                )
                self.server.server_runner.timeBeforeIdle = time.time() + 30
                # Sets the text to show
                self.server.server_runner.text = commands[1].decode("utf-8").strip()
                self.server.server_runner.pos = (
                    self.server.server_runner.offscreen_canvas.width
                )
            elif command == "BRIGHTNESS?":
                self.server.server_runner.updateFromConfigFile()
                self.request.sendall(
                    "{}\n".format(self.server.server_runner.max_brightness * 100.0)
                )
            elif (command == "BRIGHTNESS") and len(commands) > 1:
                try:
                    self.server.server_runner.max_brightness = max(
                        0, min(float(commands[1]) / 100.0, 1.0)
                    )
                    self.server.server_runner.updateToConfigFile()
                except Exception:
                    pass
            elif command == "POWERSTATE?":
                self.server.server_runner.updateFromConfigFile()
                self.request.sendall(
                    "{}\n".format("1" if self.server.server_runner.powerState else "0")
                )
            elif (command == "POWERSTATE") and len(commands) == 1:
                try:
                    self.server.server_runner.powerState = (
                        1 - self.server.server_runner.powerState
                    )
                except Exception:
                    pass
                self.server.server_runner.updateToConfigFile()
            elif (command == "POWERSTATE") and len(commands) > 1:
                try:
                    self.server.server_runner.powerState = commands[
                        1
                    ].strip().upper() in ["ON", "1", "TRUE", "YES"]
                except Exception:
                    pass
                self.server.server_runner.updateToConfigFile()
            elif command == "COLOR?":
                self.server.server_runner.updateFromConfigFile()
                self.request.sendall(
                    "#{0:02X}{1:02X}{2:02X}\n".format(
                        *self.server.server_runner.textColorRGB
                    )
                )
            elif command == "BGCOLOR?":
                self.server.server_runner.updateFromConfigFile()
                self.request.sendall(
                    "#{0:02X}{1:02X}{2:02X}\n".format(
                        *self.server.server_runner.backgroundColorRGB
                    )
                )
            elif (command == "COLOR" or command == "BGCOLOR") and len(commands) > 1:
                # Sets the text color or the background color
                color = commands[1].replace("\x00", "").strip().lower()
                gColor = None
                if color == "red":
                    gColor = (255, 0, 0)
                elif color == "blue":
                    gColor = (0, 0, 255)
                elif color == "green":
                    gColor = (0, 255, 0)
                elif color == "yellow":
                    gColor = (255, 255, 0)
                elif color == "cyan":
                    gColor = (0, 255, 255)
                elif color == "magenta":
                    gColor = (255, 0, 255)
                elif color == "white":
                    gColor = (255, 255, 255)
                else:
                    try:
                        if color.startswith("#") and len(color) == 7:
                            components = (
                                int(color[1:3], 16),
                                int(color[3:5], 16),
                                int(color[5:7], 16),
                            )
                        else:
                            components = [
                                int(255 * float(col)) for col in color.split()
                            ]
                        if len(components) == 3:
                            gColor = components
                    except Exception as e:
                        gColor = None
                if command == "COLOR" and gColor is not None:
                    self.server.server_runner.textColorRGB = gColor
                    self.server.server_runner.updateToConfigFile()
                elif command == "BGCOLOR" and gColor is not None:
                    self.server.server_runner.backgroundColorRGB = gColor
                    self.server.server_runner.updateToConfigFile()
            elif command == "FONT" and len(commands) > 1:
                # Get the font name to show
                fontname = commands[1].replace("\x00", "").strip().lower()
                # Go through all available fonts
                for i in glob.glob("../../../fonts/*.bdf"):
                    if fontname in i.lower():
                        self.server.server_runner.font.LoadFont(i)
                        break

            elif command == "GET":
                self.HTTP_process(command, commands)
