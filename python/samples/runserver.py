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
    ins = {"chambre": 0.0, "salon": 0.0}
    out = 0.0
        
    @classmethod
    def updateTemps(cls):
        for room in ["chambre", "salon"]:
            ds = {"chambre": "28-03164783ecff",
                  "salon": "28-0416526fcfff"}[room]
            f = open(os.path.join("/sys/bus/w1/devices/", ds, "w1_slave")).read()
            cls.ins[room] = float(f.split('\n')[1].split('=')[1])/1000
        
        j = requests.get("http://api.openweathermap.org/data/2.5/weather?id=2968815&APPID={}&units=metric".format(open("openweathermap_apikey").read().strip())).json()
        cls.out = float(j['main']['temp']) #float(requests.get("http://api.openweathermap.org/data/2.5/weather?id=2968815&APPID={}&units=metric".format(open("openweathermap_apikey").read().strip())).json()['main']['temp'])
        cls.ico = Image.open('./weathericons/' + j['weather'][0]['icon']+'.png').convert("RGB")
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
                self.server.server_runner.hour = True
            elif command == "NYAN" or command == "NYAN32":
                # Show NyanCat
                self.server.server_runner.background = (3,37,83)
                self.server.server_runner.images = [Image.open(i).convert("RGB") for i in sorted(glob.glob('Nyan1664/*.gif'))]
                self.server.server_runner.pos = -64 if command == "NYAN" else -32
                self.server.server_runner.sleeptime = 0.07
            elif command == "GET" and len(commands) > 1 and commands[1].startswith("/HISTORY"):
                history = self.server.server_runner.getHistory()
                self.request.sendall("""HTTP/1.1 200 OK\r\nDate: Sun, 19 Mar 2017 21:13:55 GMT\r\nServer: Apache/2.4.23 (Unix)\r\nVary: negotiate\r\nTCN: choice\r\nLast-Modified: Mon, 11 Jun 2007 18:53:14 GMT\r\nETag: "2d-432a5e4a73a80"\r\nContent-Type: text/html\r\n\r\n<html><body>{}</body></html>\r\n""".format("<br/>".join(history)))
                return
            elif command == "GET":
                self.request.sendall("""HTTP/1.1 200 OK\r\nDate: Sun, 19 Mar 2017 21:13:55 GMT\r\nServer: Apache/2.4.23 (Unix)\r\nVary: negotiate\r\nTCN: choice\r\nLast-Modified: Mon, 11 Jun 2007 18:53:14 GMT\r\nETag: "2d-432a5e4a73a80"\r\nContent-Type: text/html\r\n\r\n<html><body><h1>This is not a website...</h1><h6>Perdu!</h6></body></html>\r\n""")
                return
            elif command == "TEXT" and len(commands) > 1:
                self.server.server_runner.text = commands[1].decode('utf-8').strip()
                self.server.server_runner.pos = self.server.server_runner.offscreen_canvas.width
            elif (command == "COLOR" or command == "BGCOLOR") and len(commands) > 1:
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
        print "Goodbye {}".format(self.client_address[0])

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class RunServer(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunServer, self).__init__(*args, **kwargs)
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
    
    def show(self):
        # Run forever
        while True:
            # Wait for a certain time
            time.sleep(self.sleeptime)
        
            # Reset dimming to 15 sec each 15 minutes when displaying time
            if self.hour and (time.localtime().tm_min % 15) == 0 and time.localtime().tm_sec < 10:
                self.timeBeforeDimming = max(time.time() + 15, self.timeBeforeDimming)
            
            # Dimm brightness after a certain amount of time
            timeBeforeDimming = self.timeBeforeDimming - time.time()
            self.matrix.brightness = 0 if timeBeforeDimming < 0 else self.max_brightness if timeBeforeDimming > 15 else (self.max_brightness * timeBeforeDimming) / 15
            
            # Check if there is something to show
            if timeBeforeDimming < 0 or (self.hour is None and self.text is None and self.images is None):
                # Reset the canvas
                self.offscreen_canvas.Clear()
                self.matrix.brightness = self.max_brightness / 20

                co, f, ca = graphics.Color(self.textColor[0], self.textColor[1], self.textColor[2]), self.fontLittle, self.offscreen_canvas
                hm = time.strftime("%H%M")
                
                # Print hours
                graphics.DrawText(ca, f, 0, 7, co, hm[0:2])
                # Print columns
                if int(timeBeforeDimming) % 2: graphics.DrawText(ca, f, 9, 7, co, ":")
                # Print Minutes
                graphics.DrawText(ca, f, 13, 7, co, hm[2:4])

                # Print Temperatures
                graphics.DrawText(ca, f, 22,  7, co, u"{:2.0f}".format((Weather().insideTemperature("chambre") + Weather().insideTemperature("salon"))/2))


                # Print weather
                self.offscreen_canvas.SetImage(Weather().icon(), 23, 7)

                graphics.DrawText(ca, f, 12, 16, co, u"{:2.0f}".format(Weather().outsideTemperature()))
                
                
                self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
                time.sleep(1)
                continue
        
            # First, fill the background
            self.offscreen_canvas.Fill(self.background[0], self.background[1], self.background[2])
            
            # In order of priority: Hour -> Text -> Image
            if self.text is not None or self.hour is not None:
                try:
                    color = graphics.Color(self.textColor[0], self.textColor[1], self.textColor[2])
                    leng = graphics.DrawText(self.offscreen_canvas, # Canvas destination
                                             self.font,             # Font to show
                                             self.pos, 12,          # Position
                                             color, # Color
                                             self.text if self.hour is None else time.strftime("%H:%M:%S")) # Data to draw
                    # Next position is shifted by one on the left
                    self.pos -= 1
                    if (self.pos + leng < 0):
                        # Reset the position
                        self.pos = self.offscreen_canvas.width
                except Exception as e:
                    print "Cannot draw text", str(e)

            elif self.images is not None:
                im = self.images[self.pos % len(self.images)]
                width, height = im.size
                self.offscreen_canvas.SetImage(im, min(self.pos-width, self.offscreen_canvas.width-width), 0)
                self.pos += 1
                if self.pos > 1000:
                    self.images = None

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
