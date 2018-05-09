#!/usr/bin/env python
#-*- coding: utf-8 -*-
# Run a server to make things with the display
from samplebase import SampleBase
from rgbmatrix import graphics
import time
import threading
import SocketServer
from PIL import Image
import glob
import argparse
import os
import requests
import json
import colorsys
import math
import random

# Classe pour gerer la Meteo
class Weather():
    # Intervale de temps entre chaque mise a jour
    outsideTimeInterval = 10*60
    # Intervale de temps entre chaque mise a jour
    insideTimeInterval = 2*60

    # Timestamp sur la derniere mise a jour
    lastInsideUpdate = time.time() - 10*60
    lastOutsideUpdate = time.time() - 10*60
    # Temperatures interieures
    ins = {"chambre": None, "salon": None}
    # Temperature exterieure
    out = None
    # Icone a afficher
    ico = None

    # Temperature moyenne des temperatures interieures
    @classmethod
    def meanTemps(cls):
        # On met a jour si necessaire
        if time.time() - cls.lastInsideUpdate > cls.insideTimeInterval: cls.updateInsideTemps()

        temps = 0.0
        count = 0
        for (piece, temp) in cls.ins.items():
            try:
                temps += float(temp)
                count += 1
            except:
                continue
        return None if count == 0 else (temps / count)

    @classmethod
    def updateInsideTemps(cls):
        # Mise a jour des temperatures interieures
        try:
            # On reinitialise les valeurs
            cls.ins = {"chambre": None, "salon": None}
            for room in ["chambre", "salon"]:
               # Identifiants des peripheriques One-Wire
               ds = {"chambre": "28-03164783ecff",
                     "salon": "28-0416526fcfff"}[room]
               # Mise a jour des temperatures par lecture des fichiers de One-Wire
               f = open(os.path.join("/sys/bus/w1/devices/", ds, "w1_slave")).read()
               # On reccupere et sauve la valeur
               cls.ins[room] = float(f.split('\n')[1].split('=')[1])/1000
        except Exception as e:
            pass
        # On met a jour le timestamp
        cls.lastInsideUpdate = time.time()

    # Mise a jour des temperatures interieures et exterieure
    @classmethod
    def updateOutsideTemps(cls):
        # Mise a jour de la temperature exterieure et de l'icone meteo
        try:
            # On reinitialise les valeurs
            cls.out = None
            cls.ico = None

            # On reccupere les valeurs par internet
            j = requests.get("http://api.openweathermap.org/data/2.5/weather?id=2968815&APPID={}&units=metric".format(cls.openweathermap_apikey)).json()
            cls.out = float(j['main']['temp'])
            cls.ico = j['weather'][0]['icon']
        except Exception as e:
            pass
        # On met a jour le timestamp
        cls.lastOutsideUpdate = time.time()

    @classmethod
    def insideTemperature(cls, room):
        # On met a jour si necessaire
        if time.time() - cls.lastInsideUpdate > cls.insideTimeInterval: cls.updateInsideTemps()
        return cls.ins[room]

    @classmethod
    def outsideTemperature(cls):
        # On met a jour si necessaire
        if time.time() - cls.lastOutsideUpdate > cls.outsideTimeInterval: cls.updateOutsideTemps()
        return cls.out

    selectedAnimation = 0
    iconNo = 0
    @classmethod
    def icon(cls, size):
        # Update the temperatures if needed
        if time.time() - cls.lastOutsideUpdate > cls.outsideTimeInterval: cls.updateOutsideTemps()

        # Tick + 1
        cls.iconNo = (cls.iconNo + 1)

        if size == 16:
            path = './weathericons/mick111/'
        else:
            path = './weathericons/unicornhat_weather_icons-master/png/SD/'

        iconName = {
            "01d": "clear-day",
            "02d": "partly-cloudy-day",
            "03d": "cloudy",
            "04d": "cloudy",
            "09d": "rain",
            "10d": "rain",
            "11d": "storm",
            "13d": "snow",
            "50d": "fog",
            "01n": "clear-night",
            "02n": "partly-cloudy-night",
            "03n": "cloudy",
            "04n": "cloudy",
            "09n": "rain",
            "10n": "rain",
            "11n": "storm",
            "13n": "snow",
            "50n": "fog",
        }.get(cls.ico,"error")
        im = Image.open(path + iconName +'.png').convert("RGB")

        # Deduce the number of images according to the size of the file
        imageWidth = im.size[0]
        imageHeight = im.size[1]
        nbAnimations = int(math.ceil(float(imageHeight) / size))
        nbIcons = int(math.ceil(float(imageWidth) / size))

        # Make some temporization on first image
        moduleImages = nbIcons + (10 if nbAnimations > 1 else 0)

        # Get the icon number
        iconNo = cls.iconNo % moduleImages

        # Change selected animation if we are at the end of the current animation
        if iconNo == (moduleImages - 1):
            cls.selectedAnimation = int(math.floor(random.uniform(0, nbAnimations)))

        if cls.selectedAnimation >= nbAnimations:
             cls.selectedAnimation = 0

        # Compute horizontal and vertical offset
        hOffset = size*(iconNo if iconNo < nbIcons else 0)
        vOffset = size*cls.selectedAnimation

        image = im.crop((hOffset, vOffset,
                        hOffset + size, vOffset + size))

        return image



class ServerHandler(SocketServer.BaseRequestHandler):
    # Nothing pecular to do on setup
    def setup(self):
        pass

    def handle(self):
        # Receive a new connection from the outside world
        # print "Connection from {}".format(self.client_address[0])

        databuffer = ""
        # Keep connection alive with an infinite loop
        while True:
            # Read some data, we assume that we will not get more than 1024 bytes per received commands
            datarecv = self.request.recv(1024)

            # print "Received from {}".format(self.client_address[0])
            # Received data is None if the client disconnected. We go outside the loop
            if not datarecv: break

            # We append the received data in the incomming buffer
            databuffer += datarecv

            # Parse received data. Each commands must be separated by a '\n'
            datasplit = databuffer.split('\n', 1)

            if len(datasplit) < 2 : continue

            # We extract the command to treat, we keep the rest for later
            data, databuffer = datasplit[0], datasplit[1]

            # Remove extra whitespaces
            data = data.strip()

            # Go on next command
            if data == '': continue

            # Parse all content
            commands = data.split(" ", 1)
            command = commands[0].strip().upper()

            # Reset dimming date, 300 seconds later
            self.server.server_runner.timeBeforeIdle = time.time() + 300

            # Reset the display (remove all content) and log the command in the HISTORY for some commands
            if command not in ["BGCOLOR", "COLOR", "FONT", "GET", "DEDIM"] or (command == "GET" and len(commands) > 1 and commands[1].startswith("/CLEAR")):
                self.server.server_runner.reset()
                self.server.server_runner.addToHistory("[" + self.client_address[0] + "] " + data)

            # Command dispatch
            if command == "CLEAR":
                # Nothing to do, we already reset the display
                pass
            elif command == "DEDIM":
                # Reset dimming with lower value that usual value for dimming
                self.server.server_runner.timeBeforeIdle = time.time() + 30
            elif command == "HOUR":
                self.server.server_runner.hour = True
                self.server.server_runner.timeBeforeIdle = time.time() + 30
            elif command == "IMAGES" and len(commands) > 1:
                # Show images from specific folder
                self.server.server_runner.imageBackgroundColorRGB = (0,0,0)
                self.server.server_runner.images = [Image.open(i).convert("RGB") for i in sorted(glob.glob(commands[1]))]
                self.server.server_runner.pos = 0
                self.server.server_runner.sleeptime = 2
                self.server.server_runner.timeBeforeIdle = time.time() + 4*len(self.server.server_runner.images)
            elif command == "NYAN" or command == "NYAN32":
                # Show NyanCat
                self.server.server_runner.imageBackgroundColorRGB = (3,37,83)
                self.server.server_runner.images = [Image.open(i).convert("RGB") for i in sorted(glob.glob('Nyan1664/*.gif'))]
                self.server.server_runner.pos = -64 if command == "NYAN" else -32
                self.server.server_runner.sleeptime = 0.07
                self.server.server_runner.timeBeforeIdle = time.time() + 30
            elif command == "GET" and len(commands) > 1 and commands[1].startswith("/HISTORY"):
                # Get History of commands and serves a web page
                history = self.server.server_runner.getHistory()
                self.request.sendall("""HTTP/1.1 200 OK\r\nDate: Sun, 19 Mar 2017 21:13:55 GMT\r\nServer: Apache/2.4.23 (Unix)\r\nVary: negotiate\r\nTCN: choice\r\nLast-Modified: Mon, 11 Jun 2007 18:53:14 GMT\r\nETag: "2d-432a5e4a73a80"\r\nContent-Type: text/html\r\n\r\n<html><body>{}</body></html>\r\n""".format("<br/>".join(history)))
                # We disconnect the client
                break
            elif command == "GET":
                # Serves a dummy web page
                self.request.sendall("""HTTP/1.1 200 OK\r\nDate: Sun, 19 Mar 2017 21:13:55 GMT\r\nServer: Apache/2.4.23 (Unix)\r\nVary: negotiate\r\nTCN: choice\r\nLast-Modified: Mon, 11 Jun 2007 18:53:14 GMT\r\nETag: "2d-432a5e4a73a80"\r\nContent-Type: text/html\r\n\r\n<html><body><h1>This is not a website...</h1><h6>Perdu!</h6></body></html>\r\n""")
                # We disconnect the client
                break
            elif command == "TEXT" and len(commands) > 1:
                # Sets the text to show
                self.server.server_runner.text = commands[1].decode('utf-8').strip()
                self.server.server_runner.pos = self.server.server_runner.offscreen_canvas.width
            elif (command == "COLOR" or command == "BGCOLOR") and len(commands) > 1:
                # Sets the text color or the background color
                color = commands[1].replace('\x00', '').strip().lower()
                gColor = None
                if   color == 'red':     gColor = (255, 0, 0)
                elif color == 'blue':    gColor = (0, 0, 255)
                elif color == 'green':   gColor = (0, 255, 0)
                elif color == 'yellow':  gColor = (255, 255, 0)
                elif color == 'cyan':    gColor = (0, 255, 255)
                elif color == 'magenta': gColor = (255, 0, 255)
                elif color == 'white':   gColor = (255, 255, 255)
                else:
                    try:
                        components = [int(255 * float(col)) for col in color.split()]
                        if len(components) == 3 : gColor = components
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
                fontname = commands[1].replace('\x00', '').strip().lower()
                # Go through all available fonts
                for i in glob.glob('../../../fonts/*.bdf'):
                    if fontname in i.lower():
                        self.server.server_runner.font.LoadFont(i)
                        break
        # Client has disconnected
        print "Goodbye {}".format(self.client_address[0])

# To make a Threaded TCP Server
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

# Main RGBMatrix Sample Class
class RunServer(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunServer, self).__init__(*args, **kwargs)
        # Adds more arguments
        self.parser.add_argument("--conffile", help="Json file where parameters are read and saved.", default="/etc/ledbanner.json")
        self.parser.add_argument("--openweathermap_apikey", help="File Containing Open Weather Map API key.", default="/etc/openweathermap_apikey")
        self.parser.add_argument("--history", type=argparse.FileType('a+'), help="History of messages received by clients..")
        self.parser.add_argument("-l", "--listening-port", type=int, help="The port on which commands are received.", default=23735)

    # Update from configuration file
    def updateFromConfigFile(self):
        try:
            fileinfo = json.load(open(self.fileinformation))
        except:
            fileinfo = {"hue": 0.0, "saturation": 100.0, "powerState": 1, "brightness": 100.0, "saturation_bg": 100.0, "light_bg": 0.0, "hue_bg": 0.0}

        powerState = fileinfo.get("powerState", 1)
        brightness = fileinfo.get("brightness", 100.0)
        hue = fileinfo.get("hue", 0.0)
        saturation = fileinfo.get("saturation", 100.0)

        saturation_bg = fileinfo.get("saturation_bg", 100.0)
        light_bg = fileinfo.get("light_bg", 0.0)
        hue_bg = fileinfo.get("hue_bg", 0.0)

        self.powerState = powerState
        self.max_brightness = min(brightness/100.0, 1.0)
        rgb = colorsys.hls_to_rgb(hue/360.0,
                                  0.5,
                                  saturation/100.0)
        self.textColorRGB = (int(rgb[0]*255.0), int(rgb[1]*255.0), int(rgb[2]*255.0))

        rgb = colorsys.hls_to_rgb(hue_bg/360.0,
                                  light_bg/100.0,
                                  saturation_bg/100.0)
        self.backgroundColorRGB = (int(rgb[0]*255.0), int(rgb[1]*255.0), int(rgb[2]*255.0))

    def updateToConfigFile(self):
        try:
            fileinfo = {}
            fileinfo["powerState"] = self.powerState
            fileinfo["brightness"] = min(self.max_brightness * 100.0, 100.0)
            rgb = (float(self.textColorRGB[0]) / 255.0, float(self.textColorRGB[1]) / 255.0, float(self.textColorRGB[2]) / 255.0)
            hls = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
            fileinfo["hue"] = int(hls[0]*360)
            fileinfo["saturation"] = int(hls[2]*100)

            rgb = (float(self.backgroundColorRGB[0]) / 255.0, float(self.backgroundColorRGB[1]) / 255.0, float(self.backgroundColorRGB[2]) / 255.0)
            hls = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
            fileinfo["hue_bg"] = int(hls[0]*360)
            fileinfo["light_bg"] = int(hls[1]*100)
            fileinfo["saturation_bg"] = int(hls[2]*100)

            json.dump(fileinfo,open(self.fileinformation,"w+"))
        except Exception as e:
            print "updateToConfigFile", e
            pass

    # Add a text line in history
    def addToHistory(self, data):
        self.history.write(time.strftime("%b %d %Y %H:%M:%S") + ": " + data + "\n")

    # Get all content of history, in a list of lines
    def getHistory(self):
        self.history.flush()
        self.history.seek(0)
        return self.history.readlines()

    # Reset the display
    def reset(self):
        self.text = None
        self.images = None
        self.hour = None
        self.pos = 0
        self.sleeptime = 0.05
        self.timeBeforeIdle = 0.0
        self.updateFromConfigFile()

    def drawIdlePanel(self):
        # Idle Panel:
        co, f, f2, ca = graphics.Color(self.textColorRGB[0], self.textColorRGB[1], self.textColorRGB[2]), self.fontLittle, self.fontLittle2, self.offscreen_canvas

        ca.Fill(self.backgroundColorRGB[0], self.backgroundColorRGB[1], self.backgroundColorRGB[2])

        hm = time.strftime("%H%M%S")

        if ca.width == 32:
            timePos = (5, 6)
            inTempPos = 0, 15
            outTempPos = 13, 15
            iconSize = 8
            iconPos = 23, 7
        elif ca.width == 64:
            timePos = 5, 11
            iconPos = 64-16, 0
            iconSize = 16
            inTempPos  = 32,  6
            outTempPos = 32, 15

        # Print hours
        graphics.DrawText(ca, f, timePos[0]+0, timePos[1], co, hm[0:2])
        # Print columns
        if int(hm[-1]) % 2: graphics.DrawText(ca, f2, timePos[0]+9, timePos[1], co, ":")
        # Print Minutes
        graphics.DrawText(ca, f, timePos[0]+12, timePos[1], co, hm[2:4])

        # Print Temperatures
        tempFormat = u"{:2.0f}"
        temp = Weather().meanTemps()
        if temp is not None:
            length = graphics.DrawText(ca, f, inTempPos[0], inTempPos[1], co, tempFormat.format(temp))
            if ca.width == 64:
                length -= 2
                length += graphics.DrawText(ca, f, inTempPos[0]+length, inTempPos[1], co, u"°")
                length -= 1
                length += graphics.DrawText(ca, f, inTempPos[0]+length, inTempPos[1], co, "C")



        # Print weather icon (origin is TopLeft, coordinates are flipped)
        ico = Weather().icon(iconSize)
        if ico is not None:
            ca.SetImage(ico, iconPos[0], iconPos[1])

        outTemp = Weather().outsideTemperature()
        if outTemp is not None:
            length = graphics.DrawText(ca, f, outTempPos[0], outTempPos[1], co, tempFormat.format(outTemp))
            if ca.width == 64:
                length -= 2
                length += graphics.DrawText(ca, f, outTempPos[0]+length, outTempPos[1], co, u"°")
                length -= 1
                length += graphics.DrawText(ca, f, outTempPos[0]+length, outTempPos[1], co, "C")

    # Run loop of the server
    def show(self):
        # Run forever
        while True:
            # Wait for a certain time for each display
            time.sleep(self.sleeptime)

            # Compute if we have to go to idle.
            if self.timeBeforeIdle - time.time() < 0:
                self.hour = None
                self.text = None
                self.images = None

            # Check if we are OFF
            if not self.powerState:
                # Clear all content
                self.offscreen_canvas.Clear()
                self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
                # We are currently off, we are not in a hurry
                time.sleep(1)
                continue

            # Update data from configuration file
            self.updateFromConfigFile()

            # Check if we are Idle, eg nothing special to display
            if (self.hour is None and self.text is None and self.images is None):
                # Reduces the brightness
                self.matrix.brightness = min(100.0, 100.0*self.max_brightness)
                # Draw informations of idle panel
                self.drawIdlePanel()
                # Show canvas
                self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
                time.sleep(0.3) # No need to urge, we are idle, sleep extratime
                continue

            # In order of priority: Hour -> Text -> Image
            if self.text is not None or self.hour is not None:
                try:
                    # Draw hour/text
                    self.offscreen_canvas.Fill(self.backgroundColorRGB[0], self.backgroundColorRGB[1], self.backgroundColorRGB[2])
                    color = graphics.Color(self.textColorRGB[0], self.textColorRGB[1], self.textColorRGB[2])
                    textToDraw = self.text if self.hour is None else time.strftime("%H:%M:%S")
                    leng = graphics.DrawText(self.offscreen_canvas, # Canvas destination
                                             self.font,             # Font to show
                                             self.pos, 12,          # Position
                                             color,                 # Color
                                             textToDraw) # Data to draw

                    # Next position is shifted by one on the left
                    self.pos -= 1
                    if (self.pos + leng < 0):
                        # Reset the position
                        self.pos = self.offscreen_canvas.width
                except Exception as e:
                    print "Cannot draw text", str(e)

            elif self.images is not None:
                # Get the current image
                self.offscreen_canvas.Fill(self.imageBackgroundColorRGB[0], self.imageBackgroundColorRGB[1], self.imageBackgroundColorRGB[2])
                im = self.images[self.pos % len(self.images)]
                width, height = im.size

                # Origin is TopLeft, coordinates are flipped
                posX = min(self.pos-width, self.offscreen_canvas.width-width)
                self.offscreen_canvas.SetImage(im, posX, 0)

                # Next position is shifted by one on the right
                self.pos += 1
                if self.pos > 1000:
                    self.images = None

            # Show prepared Canvas
            self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)


    def run(self):
        self.fileinformation = self.args.conffile
        Weather.openweathermap_apikey = open(self.args.openweathermap_apikey).read().strip()

        self.reset()

        self.backgroundColorRGB = (0, 0, 0)
        self.textColorRGB = (255, 255, 255)
        self.updateFromConfigFile()

        self.offscreen_canvas = self.matrix.CreateFrameCanvas()

        self.font = graphics.Font()
        self.font.LoadFont("/home/pi/Documents/display16x32/rpi-rgb-led-matrix/fonts/9x15.bdf")

        self.fontLittle = graphics.Font()
        self.fontLittle.LoadFont("/home/pi/Documents/display16x32/rpi-rgb-led-matrix/fonts/5x7.bdf")
        self.fontLittle2 = graphics.Font()
        self.fontLittle2.LoadFont("/home/pi/Documents/display16x32/rpi-rgb-led-matrix/fonts/4x6.bdf")

        self.pos = self.offscreen_canvas.width

        self.history = self.args.history

        self.timeBeforeIdle  = time.time() + 300
        self.max_brightness = 1.0

        # Create a new server
        server = ThreadedTCPServer(('', self.args.listening_port), ServerHandler)
        server.server_runner = self
        server.allow_reuse_address = True

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        print "Serving on port", server.server_address
        server_thread.start()

        # Start thread for showing text
        self.show()

        server.shutdown()
        server.server_close()

# Main function
if __name__ == "__main__":
    run_server = RunServer()
    if (not run_server.process()):
        run_server.print_help()
