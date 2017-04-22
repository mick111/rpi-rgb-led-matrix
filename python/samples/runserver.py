#!/usr/bin/env python
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

class Weather():
    lastupdate = time.time() - 100
    ins = {"chambre": None, "salon": None}
    out = None
    ico = None

    @classmethod
    def updateTemps(cls):
        try:
            cls.ins = {"chambre": None, "salon": None}
            for room in ["chambre", "salon"]:
               ds = {"chambre": "28-03164783ecff",
                     "salon": "28-0416526fcfff"}[room]
               f = open(os.path.join("/sys/bus/w1/devices/", ds, "w1_slave")).read()
               cls.ins[room] = float(f.split('\n')[1].split('=')[1])/1000
        
            cls.out = None
            cls.ico = None
            j = requests.get("http://api.openweathermap.org/data/2.5/weather?id=2968815&APPID={}&units=metric".format(open("openweathermap_apikey").read().strip())).json()
            cls.out = float(j['main']['temp']) #float(requests.get("http://api.openweathermap.org/data/2.5/weather?id=2968815&APPID={}&units=metric".format(open("openweathermap_apikey").read().strip())).json()['main']['temp'])
            cls.ico = Image.open('./weathericons/' + j['weather'][0]['icon']+'.png').convert("RGB")
        except Exception as e:
            pass
        cls.lastupdate = time.time()

    @classmethod
    def insideTemperature(cls, room):
        if time.time() - cls.lastupdate > 60: cls.updateTemps()
        return cls.ins[room]

    @classmethod
    def outsideTemperature(cls):
        if time.time() - cls.lastupdate > 60: cls.updateTemps()
        return cls.out

    @classmethod
    def icon(cls):
        if time.time() - cls.lastupdate > 60: cls.updateTemps()
        return cls.ico

class ServerHandler(SocketServer.BaseRequestHandler):
    def setup(self):
        pass
    
    def handle(self):
        # Receive a new connection from the outside world
        print "Connection from {}".format(self.client_address[0])
        # Keep connection alive
        while True:
          # Read some data, we assume that we will not get more than 1024 bytes per received commands
          data = self.request.recv(1024)

          print "Received from {}".format(self.client_address[0])
          # Data is none if the client disconnected
          if not data: break
          # Parse received data. Each commands must be separated by a '\n'
          datas = data.split("\n")

          # Show the data to be processed                              
          print repr(datas)

          for data in datas:
            # Go on next command
            if data == '': continue

            print repr(data)

            commands = data.strip().split(" ", 1)
            command = commands[0].strip().upper()
            
            # Reset dimming
            if command not in ["GET"]:
                self.server.server_runner.timeBeforeDimming = time.time() + 300
            # Reset the display and log the command in the HISTORY for some commands
            if command not in ["BGCOLOR", "COLOR", "FONT", "GET", "DEDIM"] or (command == "GET" and len(commands) > 1 and commands[1].startswith("/CLEAR")):
                self.server.server_runner.reset()
                self.server.server_runner.addToHistory("[" + self.client_address[0] + "] " + data)
            if command == "CLEAR":
                # Nothing to do, we already reset the display
                pass
            elif command == "DEDIM":
                # Reset dimming with lower value
                self.server.server_runner.timeBeforeDimming = time.time() + 30
            elif command == "HOUR":
                self.server.server_runner.hour = True#
            elif command == "IMAGES" and len(commands) > 1:
                # Show images from specific folder
                self.server.server_runner.images = [Image.open(i).convert("RGB") for i in sorted(glob.glob(commands[1]))]
                self.server.server_runner.sleeptime = 2
                self.server.server_runner.pos = 0
            elif command == "NYAN" or command == "NYAN32":
                # Show NyanCat
                self.server.server_runner.background = (3,37,83)
                self.server.server_runner.images = [Image.open(i).convert("RGB") for i in sorted(glob.glob('Nyan1664/*.gif'))]
                self.server.server_runner.pos = -64 if command == "NYAN" else -32
                self.server.server_runner.sleeptime = 0.07
            elif command == "GET" and len(commands) > 1 and commands[1].startswith("/HISTORY"):
                # Get History of commands and serves a web page
                history = self.server.server_runner.getHistory()
                self.request.sendall("""HTTP/1.1 200 OK\r\nDate: Sun, 19 Mar 2017 21:13:55 GMT\r\nServer: Apache/2.4.23 (Unix)\r\nVary: negotiate\r\nTCN: choice\r\nLast-Modified: Mon, 11 Jun 2007 18:53:14 GMT\r\nETag: "2d-432a5e4a73a80"\r\nContent-Type: text/html\r\n\r\n<html><body>{}</body></html>\r\n""".format("<br/>".join(history)))
                return
            elif command == "GET":
                # Serves a dummy web page
                self.request.sendall("""HTTP/1.1 200 OK\r\nDate: Sun, 19 Mar 2017 21:13:55 GMT\r\nServer: Apache/2.4.23 (Unix)\r\nVary: negotiate\r\nTCN: choice\r\nLast-Modified: Mon, 11 Jun 2007 18:53:14 GMT\r\nETag: "2d-432a5e4a73a80"\r\nContent-Type: text/html\r\n\r\n<html><body><h1>This is not a website...</h1><h6>Perdu!</h6></body></html>\r\n""")
                return
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
                    self.server.server_runner.textColor = gColor
                elif command == "BGCOLOR" and gColor is not None:
                    self.server.server_runner.background = gColor
            elif command == "FONT" and len(commands) > 1:
                # Get the font name to show
                fontname = commands[1].replace('\x00', '').strip().lower()
                # Go through all available fonts
                for i in glob.glob('../../fonts/*.bdf'):
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
        self.parser.add_argument("--history", type=argparse.FileType('a+'), help="History of messages received by clients..")
        self.parser.add_argument("-l", "--listening-port", type=int, help="The port on which commands are received.", default=23735)

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
        self.timeBeforeDimming = 0.0
    
    def drawIdlePanel(self):
        # Idle Panel:
        co, f, f2, ca = graphics.Color(self.textColor[0], self.textColor[1], self.textColor[2]), self.fontLittle, self.fontLittle2, self.offscreen_canvas
        hm = time.strftime("%H%M%S")
                
        # Print hours
        graphics.DrawText(ca, f, 5+0, 6, co, hm[0:2])
        # Print columns
        if int(hm[-1]) % 2: graphics.DrawText(ca, f2, 5+9, 6, co, ":")
        # Print Minutes
        graphics.DrawText(ca, f, 5+12, 6, co, hm[2:4])
        
        # Print Temperatures
        temp = Weather().insideTemperature("chambre")
        temp2 = Weather().insideTemperature("salon")
        temp3 = (temp if temp is not None else 0.0) + (temp2 if temp2 is not None else 0.0)
        temp = None if temp is None and temp2 is None else temp3 if temp is None or temp2 is None else (temp3/2)
        if temp is not None: graphics.DrawText(ca, f, 0, 15, co, u"{:2.0f}".format(temp))
        
        # Print weather icon (origin is TopLeft, coordinates are flipped)
        ico = Weather().icon()
        if ico is not None:
            self.offscreen_canvas.SetImage(ico, 23, 7)
        outTemp = Weather().outsideTemperature()
        if outTemp is not None:
            graphics.DrawText(ca, f, 13, 15, co, u"{:2.0f}".format(outTemp))

    # Run loop of the server
    def show(self):
        # Run forever
        while True:
            # Wait for a certain time
            time.sleep(self.sleeptime)
            
            timeBeforeDimming = self.timeBeforeDimming - time.time()

            # Check if we are Idle
            if timeBeforeDimming < 0 or (self.hour is None and self.text is None and self.images is None):
                # Reset the canvas
                self.offscreen_canvas.Clear()
                # Reduces the brightness
                self.matrix.brightness = self.max_brightness / 20

                # Draw informations of idle panel
                self.drawIdlePanel()
                # Show canvas
                self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
                time.sleep(1) # No need to urge, we are idle
                continue
        
            # First, fill the background
            self.offscreen_canvas.Fill(self.background[0], self.background[1], self.background[2])
            
            # Reset dimming to 15 sec each 15 minutes when displaying time
            if self.hour and (time.localtime().tm_min % 15) == 0 and time.localtime().tm_sec < 10:
                self.timeBeforeDimming = max(time.time() + 15, self.timeBeforeDimming)
            
            # Dimm brightness after a certain amount of time
            self.matrix.brightness = 0 if timeBeforeDimming < 0 else self.max_brightness if timeBeforeDimming > 15 else (self.max_brightness * timeBeforeDimming) / 15
            
            # In order of priority: Hour -> Text -> Image
            if self.text is not None or self.hour is not None:
                try:
                    # Draw text
                    color = graphics.Color(self.textColor[0], self.textColor[1], self.textColor[2])
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
        self.reset()
        
        self.background = (0, 0, 0)
        self.textColor = (255, 255, 255)
        
        self.offscreen_canvas = self.matrix.CreateFrameCanvas()
        
        self.font = graphics.Font()
        self.font.LoadFont("../../fonts/9x15.bdf")

        self.fontLittle = graphics.Font()
        self.fontLittle.LoadFont("../../fonts/5x7.bdf")
        self.fontLittle2 = graphics.Font()
        self.fontLittle2.LoadFont("../../fonts/4x6.bdf")
        
        self.pos = self.offscreen_canvas.width

        self.history = self.args.history
        
        self.timeBeforeDimming  = time.time() + 300
        self.max_brightness = self.matrix.brightness
        
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
