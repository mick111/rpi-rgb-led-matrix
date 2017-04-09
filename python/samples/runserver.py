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

            # Reset dimming
            self.server.server_runner.timeBeforeDimming  = time.time() + 600

            commands = data.strip().split(" ", 1)
            command = commands[0].strip().upper()

            # Reset the display and log the command in the HISTORY for some commands
            if command not in ["BGCOLOR", "COLOR", "FONT", "GET", "DEDIM"] or (command == "GET" and len(commands) > 1 and commands[1].startswith("/CLEAR")):
                self.server.server_runner.reset()
                self.server.server_runner.addToHistory("[" + self.client_address[0] + "] " + command)
            if command == "CLEAR":
                # Nothing to do, we already reset the display
                pass
            elif command == "HOUR":
                self.server.server_runner.hour = True
            elif command == "NYAN" or command == "NYAN32":
                # Show NyanCat
                self.server.server_runner.background = graphics.Color(3,37,83)
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
                if   color == 'red':     gColor = graphics.Color(255, 0, 0)
                elif color == 'blue':    gColor = graphics.Color(0, 0, 255)
                elif color == 'green':   gColor = graphics.Color(0, 255, 0)
                elif color == 'yellow':  gColor = graphics.Color(255, 255, 0)
                elif color == 'cyan':    gColor = graphics.Color(0, 255, 255)
                elif color == 'magenta': gColor = graphics.Color(255, 0, 255)
                elif color == 'white':   gColor = graphics.Color(255, 255, 255)
                else:
                    try:
                        components = [int(255 * float(col)) for col in color.split()]
                        if len(components) == 3 : gColor = graphics.Color(components[0], components[1], components[2])
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
            
            # Dimm brightness after a certain amount of time
            timeBeforeDimming = self.timeBeforeDimming - time.time()
            self.matrix.brightness = 0 if timeBeforeDimming < 0 else self.max_brightness if timeBeforeDimming > 100 else self.max_brightness * (timeBeforeDimming / 100)
            
            # Check if there is something to show
            if timeBeforeDimming < 0 or (self.hour is None and self.text is None and self.images is None):
                # Reset the canvas
                self.offscreen_canvas.Clear()
                self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
                continue
        
            # First, fill the background
            self.offscreen_canvas.Fill(self.background)
            
            # In order of priority: Hour -> Text -> Image
            if self.text is not None or self.hour is not None:
                try:
                    leng = graphics.DrawText(self.offscreen_canvas, # Canvas destination
                                             self.font,             # Font to show
                                             self.pos, 12,          # Position
                                             self.textColor,        # Color
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
        
        self.background = graphics.Color(0, 0, 0)
        self.textColor = graphics.Color(255, 255, 255)
        
        self.offscreen_canvas = self.matrix.CreateFrameCanvas()
        
        self.font = graphics.Font()
        self.font.LoadFont("../../fonts/9x15.bdf")

        self.pos = self.offscreen_canvas.width

        self.history = self.args.history
        
        self.timeBeforeDimming  = time.time() + 600
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
