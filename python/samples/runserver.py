#!/usr/bin/env python
# Run a server to make things with the display
from samplebase import SampleBase
from rgbmatrix import graphics
import time
import threading
import SocketServer
from PIL import Image
import glob

class ServerHandler(SocketServer.BaseRequestHandler):
    def setup(self):
        pass
    
    def handle(self):
        print "Connection from {}".format(self.client_address[0])
        while True:
          data = self.request.recv(1024)
          print "Receive from {}".format(self.client_address[0])
          if not data: break
          datas = data.split("\n")
          print repr(datas)
          for data in datas:
            if data == '': break
            print repr(data)
            commands = data.strip().split(" ", 1)
            command = commands[0].strip().upper()
            if command not in ["COLOR", "FONT"]:
              self.server.server_runner.text = None
              self.server.server_runner.images = None
              self.server.server_runner.pos = 0
              self.server.server_runner.sleeptime = 0.05
            if command == "CLEAR":
                pass
            elif command == "NYAN":
                self.server.server_runner.images = [Image.open(i).convert("RGB") for i in sorted(glob.glob('Nyan1632/*.gif'))]
                self.server.server_runner.pos = -32
                self.server.server_runner.sleeptime = 0.07
            elif command == "GET":
                self.request.sendall("""HTTP/1.1 200 OK\r\nDate: Sun, 19 Mar 2017 21:13:55 GMT\r\nServer: Apache/2.4.23 (Unix)\r\nVary: negotiate\r\nTCN: choice\r\nLast-Modified: Mon, 11 Jun 2007 18:53:14 GMT\r\nETag: "2d-432a5e4a73a80"\r\nContent-Type: text/html\r\n\r\n<html><body><h1>This is not a website...</h1><h6>Perdu!</h6></body></html>\r\n""")
                return
            elif command == "TEXT":
                print "TEXT was :", self.server.server_runner.text
                self.server.server_runner.text = commands[1].decode('utf-8').strip() if len(commands) > 1 else None
                print "TEXT is :", self.server.server_runner.text
                self.server.server_runner.pos = self.server.server_runner.offscreen_canvas.width
            elif command == "COLOR":
                color = commands[1].replace('\x00', '').strip().lower()
                try:
                    colors = [int(255 * float(col)) for col in color.split()]
                    self.server.server_runner.textColor = graphics.Color(colors[0], colors[1], colors[2])
                except Exception as e:
                    print e
                    if   color == 'red':     self.server.server_runner.textColor = graphics.Color(255, 0, 0)
                    elif color == 'blue':    self.server.server_runner.textColor = graphics.Color(0, 0, 255)
                    elif color == 'green':   self.server.server_runner.textColor = graphics.Color(0, 255, 0)
                    elif color == 'yellow':  self.server.server_runner.textColor = graphics.Color(255, 255, 0)
                    elif color == 'cyan':    self.server.server_runner.textColor = graphics.Color(0, 255, 255)
                    elif color == 'magenta': self.server.server_runner.textColor = graphics.Color(255, 0, 255)
                    elif color == 'white':   self.server.server_runner.textColor = graphics.Color(255, 255, 255)
            elif command == "FONT":
                self.server.server_runner.font.LoadFont("../../fonts/unifont.bdf")
        print "Goodbye {}".format(self.client_address[0])

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class RunServer(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunServer, self).__init__(*args, **kwargs)
        self.parser.add_argument("-l", "--listening-port", type=int, help="The port on which commands are received.", default=23735)
    
    def show(server_runner):
        while True:
            server_runner.offscreen_canvas.Fill(server_runner.background[0],server_runner.background[1],server_runner.background[2])
            time.sleep(server_runner.sleeptime)
            if server_runner.text is None and server_runner.images is None:
                server_runner.offscreen_canvas = server_runner.matrix.SwapOnVSync(server_runner.offscreen_canvas)
                continue
    
            if server_runner.text is not None:
                try:
                    leng = graphics.DrawText(server_runner.offscreen_canvas,
                                             server_runner.font,
                                             server_runner.pos, 12,
                                             server_runner.textColor,
                                             server_runner.text)
                    server_runner.pos -= 1
                    if (server_runner.pos + leng < 0):
                        server_runner.pos = server_runner.offscreen_canvas.width
                except Exception as e: print "Cannot draw text", str(e)
            elif server_runner.images is not None:
                im = server_runner.images[server_runner.pos % len(server_runner.images)]
                server_runner.offscreen_canvas.SetImage(im, min(server_runner.pos-32,0), 0)
                server_runner.pos += 1
                if server_runner.pos > 1000: server_runner.images = None

            server_runner.offscreen_canvas = server_runner.matrix.SwapOnVSync(server_runner.offscreen_canvas)
    
    def run(self):
        self.sleeptime = 0.05
        self.text = None
        self.images = None
        self.background = (0,0,0)
        self.offscreen_canvas = self.matrix.CreateFrameCanvas()
        self.font = graphics.Font()
        self.font.LoadFont("../../fonts/9x15.bdf")
        self.textColor = graphics.Color(255, 255, 255)
        self.pos = self.offscreen_canvas.width

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
