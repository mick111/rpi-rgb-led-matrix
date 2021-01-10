#!/usr/bin/python3
# -*- coding: utf-8 -*-

#!/usr/bin/env python
# Run a server to make things with the display

from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions

import time
import threading
from tcp_server import ThreadedTCPServer, ServerHandler, EVENTS

from PIL import Image
import argparse
import json
import colorsys
import datetime
import sys

from meteo import Meteo

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



# Main Matrice class
class Matrice(object):
    def __init__(self, args):
        self.args = args

        # Create RGBMatrixOptions to launch arguments
        options = RGBMatrixOptions()

        if self.args.led_gpio_mapping is not None:
            options.hardware_mapping = self.args.led_gpio_mapping
        options.rows = self.args.led_rows
        options.cols = self.args.led_cols
        options.chain_length = self.args.led_chain
        options.parallel = self.args.led_parallel
        options.row_address_type = self.args.led_row_addr_type
        options.multiplexing = self.args.led_multiplexing
        options.pwm_bits = self.args.led_pwm_bits
        options.brightness = self.args.led_brightness
        options.pwm_lsb_nanoseconds = self.args.led_pwm_lsb_nanoseconds
        options.led_rgb_sequence = self.args.led_rgb_sequence
        options.pixel_mapper_config = self.args.led_pixel_mapper
        options.panel_type = self.args.led_panel_type

        if self.args.led_show_refresh:
            options.show_refresh_rate = 1

        if self.args.led_slowdown_gpio is not None:
            options.gpio_slowdown = self.args.led_slowdown_gpio
        if self.args.led_no_hardware_pulse:
            options.disable_hardware_pulsing = True

        self.matrix = RGBMatrix(options=options)

        try:
            # Start Infinite loop
            print("Press CTRL-C to stop matrix")
            self.run()
        except KeyboardInterrupt:
            print("Exiting\n")
            sys.exit(0)
        return True

    def run(self):
        self.fileinformation = self.args.conffile
        openweathermap_apikey = open(self.args.openweathermap_apikey).read().strip()
        self.meteo = Meteo(openweathermap_apikey)

        self.reset()

        self.backgroundColorRGB = (0, 0, 0)
        self.textColorRGB = (255, 255, 255)
        self.updateFromConfigFile()

        self.offscreen_canvas = self.matrix.CreateFrameCanvas()

        self.font = graphics.Font()
        self.font.LoadFont(
            "../fonts/9x15.bdf"
        )

        self.fontSmall = graphics.Font()
        self.fontSmall.LoadFont(
            "../fonts/6x10.bdf"
        )
        self.fontLittle = graphics.Font()
        self.fontLittle.LoadFont(
            "../fonts/5x7.bdf"
        )
        self.fontTiny = graphics.Font()
        self.fontTiny.LoadFont(
            "../fonts/4x6.bdf"
        )

        self.pos = self.offscreen_canvas.width

        self.history = self.args.history

        self.timeBeforeIdle = time.time()
        self.max_brightness = 1.0

        # Create a new server
        server = ThreadedTCPServer(("", self.args.listening_port), ServerHandler)
        server.server_runner = self
        server.allow_reuse_address = True

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        print("Serving on port {}".format(server.server_address))
        server_thread.start()

        # Start thread for showing text
        self.show()

        server.shutdown()
        server.server_close()

    # Update from configuration file
    def updateFromConfigFile(self):
        try:
            fileinfo = json.load(open(self.fileinformation))
        except Exception:
            fileinfo = {
                "hue": 0.0,
                "saturation": 100.0,
                "powerState": 1,
                "brightness": 100.0,
                "saturation_bg": 100.0,
                "light_bg": 0.0,
                "hue_bg": 0.0,
            }

        powerState = fileinfo.get("powerState", 1)
        brightness = fileinfo.get("brightness", 100.0)
        hue = fileinfo.get("hue", 0.0)
        saturation = fileinfo.get("saturation", 100.0)

        saturation_bg = fileinfo.get("saturation_bg", 100.0)
        light_bg = fileinfo.get("light_bg", 0.0)
        hue_bg = fileinfo.get("hue_bg", 0.0)

        self.powerState = powerState
        self.max_brightness = min(brightness / 100.0, 1.0)
        rgb = colorsys.hls_to_rgb(hue / 360.0, 0.5, saturation / 100.0)
        self.textColorRGB = (
            int(rgb[0] * 255.0),
            int(rgb[1] * 255.0),
            int(rgb[2] * 255.0),
        )

        rgb = colorsys.hls_to_rgb(
            hue_bg / 360.0, light_bg / 100.0, saturation_bg / 100.0
        )
        self.backgroundColorRGB = (
            int(rgb[0] * 255.0),
            int(rgb[1] * 255.0),
            int(rgb[2] * 255.0),
        )

    def updateToConfigFile(self):
        try:
            fileinfo = {}
            fileinfo["powerState"] = self.powerState
            fileinfo["brightness"] = min(self.max_brightness * 100.0, 100.0)
            rgb = (
                float(self.textColorRGB[0]) / 255.0,
                float(self.textColorRGB[1]) / 255.0,
                float(self.textColorRGB[2]) / 255.0,
            )
            hls = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
            fileinfo["hue"] = int(hls[0] * 360)
            fileinfo["saturation"] = int(hls[2] * 100)

            rgb = (
                float(self.backgroundColorRGB[0]) / 255.0,
                float(self.backgroundColorRGB[1]) / 255.0,
                float(self.backgroundColorRGB[2]) / 255.0,
            )
            hls = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
            fileinfo["hue_bg"] = int(hls[0] * 360)
            fileinfo["light_bg"] = int(hls[1] * 100)
            fileinfo["saturation_bg"] = int(hls[2] * 100)

            json.dump(fileinfo, open(self.fileinformation, "w+"))
        except Exception as e:
            print("updateToConfigFile error", e)

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
        self.event_day = None
        self.hour = None
        self.pos = 0
        self.sleeptime = 0.05
        self.updateFromConfigFile()

    def clear(self):
        # Reset all
        self.reset()
        # Go to idle now
        self.timeBeforeIdle = time.time()

    def hour(self):
        self.reset()
        self.timeBeforeIdle = time.time() + 30
        self.hour = True

    def event(self, name, timeBeforeIdle=15):
        self.reset()
        EVENT = EVENTS[name]

        date = EVENT["date"]
        days_before_event = (date - datetime.datetime.now()).days + 1

        URL_TEMPLATE = "./lametric_caches/{}"
        urls = [URL_TEMPLATE.format(num) for num in EVENT["images"]]

        ims = []
        for url in urls:
            im = Image.open(url)
            duration = 0.05
            if ".gif" in url:
                ims.extend(gif_to_imgs(im) * 2)
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
                ims.extend([imo] * 50)

        self.timeBeforeIdle = time.time() + timeBeforeIdle
        self.images = ims
        self.event_day = days_before_event
        self.imageBackgroundColorRGB = (0, 0, 0)
        self.pos = 16
        self.sleeptime = duration

    def drawIdlePanel(self):
        # Idle Panel:
        co, f, f2, ca = (
            graphics.Color(
                self.textColorRGB[0], self.textColorRGB[1], self.textColorRGB[2]
            ),
            self.fontLittle,
            self.fontTiny,
            self.offscreen_canvas,
        )

        ca.Fill(
            self.backgroundColorRGB[0],
            self.backgroundColorRGB[1],
            self.backgroundColorRGB[2],
        )

        hm = time.strftime("%H%M%S")

        # Xmas Time
        xmas = datetime.datetime(year=datetime.datetime.now().year, month=12, day=25, hour=3)
        # Time before Xmas
        remaining = xmas - datetime.datetime.now()

        if ca.width == 32:
            timePos = 3, 6
            inTempPos = 0, 15
            outTempPos = 13, 15
            iconSize = 8
            iconPos = 23, 7
        elif ca.width == 64:
            timePos = 3, 6
            iconPos = 64 - 16, 0
            iconSize = 16
            inTempPos = 30, 6
            outTempPos = 30, 14

        print_xmas = remaining.days < 35
 
        if print_xmas:
            timePos = timePos[0], timePos[1] + 5

        # Print hours
        graphics.DrawText(ca, f, timePos[0] + 0, timePos[1], co, hm[0:2])
        # Print columns
        if int(hm[-1]) % 2:
            graphics.DrawText(ca, f2, timePos[0] + 9, timePos[1], co, ":")
        # Print Minutes
        graphics.DrawText(ca, f, timePos[0] + 12, timePos[1], co, hm[2:4])

        if print_xmas:
            # Xmas Time
            xmas = datetime.datetime(year=datetime.datetime.now().year, month=12, day=25, hour=3)
            # Time before Xmas
            remaining = xmas - datetime.datetime.now()
            # Colors
            red = graphics.Color(255, 0, 0)
            green = graphics.Color(0, 255, 0)

            # Days
            graphics.DrawText(ca, f2, 8, 14, green, "dodos")
            graphics.DrawText(ca, f2, 1 if remaining.days+1 > 9 else 0, 14, red, "{:2d}".format(remaining.days+1))

        # Print Temperatures
        tempFormat = "{:2.0f}"
        temp = self.meteo.meanTemps()
        if temp is not None:
            length = graphics.DrawText(
                ca, f, inTempPos[0], inTempPos[1], co, tempFormat.format(temp)
            )
            if ca.width == 64:
                length -= 2
                length += graphics.DrawText(
                    ca, f, inTempPos[0] + length, inTempPos[1], co, "°"
                )
                length -= 1
                length += graphics.DrawText(
                    ca, f, inTempPos[0] + length, inTempPos[1], co, "C"
                )

        # Print weather icon (origin is TopLeft, coordinates are flipped)
        ico = self.meteo.icon(iconSize)
        if ico is not None:
            ca.SetImage(ico, iconPos[0], iconPos[1])

        outTemp = self.meteo.outsideTemperature()
        if outTemp is not None:
            length = graphics.DrawText(
                ca, f, outTempPos[0], outTempPos[1], co, tempFormat.format(outTemp)
            )
            if ca.width == 64:
                length -= 2
                length += graphics.DrawText(
                    ca, f, outTempPos[0] + length, outTempPos[1], co, "°"
                )
                length -= 1
                length += graphics.DrawText(
                    ca, f, outTempPos[0] + length, outTempPos[1], co, "C"
                )

    # Run loop of the server
    def show(self):
        # Run forever
        # print "[",self.__class__.__name__,"]", "entering infinite loop"
        last_time = time.localtime()
        event_count = 0

        while True:
            # Wait for a certain time for each display
            # print "[",self.__class__.__name__,"]", "sleep for", self.sleeptime
            time.sleep(self.sleeptime)

            # Compute if we have to go to idle.
            if self.timeBeforeIdle < time.time():
                # print "[",self.__class__.__name__,"]", "Got idle, performing reset"
                self.reset()

            # Update data from configuration file
            self.updateFromConfigFile()

            # Check if we are OFF
            if not self.powerState:
                # print "[",self.__class__.__name__,"]", "OFF-state style"
                # Clear all content
                self.offscreen_canvas.Clear()
                self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
                # We are currently off, we are not in a hurry
                time.sleep(1)
                continue

            new_time = time.localtime()

            if new_time.tm_min != last_time.tm_min and (new_time.tm_min % 15 == 0):
                events_names = sorted(list(EVENTS.keys()))
                event_count += 1
                self.event(events_names[event_count % len(events_names)])
            last_time = new_time

            # Check if we are Idle, eg nothing special to display
            if self.hour is None and self.text is None and self.images is None:
                # print "[",self.__class__.__name__,"]", "IDLE because everything is None"
                # Reduces the brightness
                self.matrix.brightness = min(100.0, 100.0 * self.max_brightness)
                # Draw informations of idle panel
                self.drawIdlePanel()
                # Show canvas
                self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
                time.sleep(0.3)  # No need to urge, we are idle, sleep extratime
                continue

            # In order of priority: Hour -> Text -> Image
            if self.hour is not None:
                # print "[",self.__class__.__name__,"]", "HOUR"
                try:
                    # Draw hour
                    self.offscreen_canvas.Fill(
                        self.backgroundColorRGB[0],
                        self.backgroundColorRGB[1],
                        self.backgroundColorRGB[2],
                    )
                    color = graphics.Color(
                        self.textColorRGB[0], self.textColorRGB[1], self.textColorRGB[2]
                    )
                    textToDraw = time.strftime("%H:%M:%S")
                    leng = graphics.DrawText(
                        self.offscreen_canvas,  # Canvas destination
                        self.font,  # Font to show
                        self.pos,
                        12,  # Position
                        color,  # Color
                        textToDraw,
                    )  # Data to draw

                    # Next position is shifted by one on the left
                    self.pos -= 1
                    if self.pos + leng < 0:
                        # Reset the position
                        self.pos = self.offscreen_canvas.width
                except Exception as e:
                    print("Cannot draw Hour", str(e))

            elif self.text is not None:
                # print "[",self.__class__.__name__,"]", "TEXT"
                try:
                    # Draw text
                    self.offscreen_canvas.Fill(
                        self.backgroundColorRGB[0],
                        self.backgroundColorRGB[1],
                        self.backgroundColorRGB[2],
                    )
                    color = graphics.Color(
                        self.textColorRGB[0], self.textColorRGB[1], self.textColorRGB[2]
                    )

                    textToDraw = self.text.split(";", 1)
                    if len(textToDraw) == 1:
                        leng = graphics.DrawText(
                            self.offscreen_canvas,  # Canvas destination
                            self.font,  # Font to show
                            self.pos,
                            12,  # Position
                            color,  # Color
                            textToDraw[0],
                        )  # Data to draw
                    else:
                        graphics.DrawText(
                            self.offscreen_canvas,  # Canvas destination
                            self.fontTiny,  # Font to show
                            1,
                            5,  # Position
                            color,  # Color
                            textToDraw[0],
                        )  # Data to draw
                        leng = graphics.DrawText(
                            self.offscreen_canvas,  # Canvas destination
                            self.fontSmall,  # Font to show
                            self.pos,
                            14,  # Position
                            color,  # Color
                            textToDraw[1],
                        )  # Data to draw

                    # Next position is shifted by one on the left
                    self.pos -= 1
                    if self.pos + leng < 0:
                        # Reset the position
                        self.pos = self.offscreen_canvas.width
                except Exception as e:
                    print("Cannot draw text", str(e))

            elif self.images is not None:
                # print "[",self.__class__.__name__,"]", "IMAGE", self.pos, "over", len(self.images)
                # Get the current image
                self.offscreen_canvas.Fill(
                    self.imageBackgroundColorRGB[0],
                    self.imageBackgroundColorRGB[1],
                    self.imageBackgroundColorRGB[2],
                )
                im = self.images[self.pos % len(self.images)]
                width, height = im.size

                # Origin is TopLeft, coordinates are flipped
                posX = min(self.pos - width, self.offscreen_canvas.width - width)
                self.offscreen_canvas.SetImage(im, posX, 0)

                # Next position is shifted by one on the right
                self.pos += 1
                if self.pos > 2000:
                    # print "[",self.__class__.__name__,"]", "Watchdog for pos to high"
                    self.images = None
                if self.event_day is not None and posX > 32:
                    color = graphics.Color(
                        self.textColorRGB[0], self.textColorRGB[1], self.textColorRGB[2]
                    )
                    graphics.DrawText(
                        self.offscreen_canvas,  # Canvas destination
                        self.fontSmall,  # Font to show
                        10 if self.event_day < 100 else 5,
                        12,  # Position
                        color,  # Color
                        "J-{:d}".format(self.event_day),
                    )  # Data to draw

            # Show prepared Canvas
            self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)


# Main function
if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # RGBMatrixOptions specific options
    parser.add_argument(
        "-r",
        "--led-rows",
        action="store",
        help="Display rows. 16 for 16x32, 32 for 32x32. Default: 16",
        default=16,
        type=int,
    )
    parser.add_argument(
        "--led-cols",
        action="store",
        help="Panel columns. Typically 32 or 64. (Default: 32)",
        default=32,
        type=int,
    )
    parser.add_argument(
        "-c",
        "--led-chain",
        action="store",
        help="Daisy-chained boards. Default: 2.",
        default=2,
        type=int,
    )
    parser.add_argument(
        "-P",
        "--led-parallel",
        action="store",
        help="For Plus-models or RPi2: parallel chains. 1..3. Default: 1",
        default=1,
        type=int,
    )
    parser.add_argument(
        "-p",
        "--led-pwm-bits",
        action="store",
        help="Bits used for PWM. Something between 1..11. Default: 11",
        default=11,
        type=int,
    )
    parser.add_argument(
        "-b",
        "--led-brightness",
        action="store",
        help="Sets brightness level. Default: 100. Range: 1..100",
        default=100,
        type=int,
    )
    parser.add_argument(
        "-m",
        "--led-gpio-mapping",
        help="Hardware Mapping: regular, adafruit-hat, adafruit-hat-pwm, mick111",
        choices=["regular", "adafruit-hat", "adafruit-hat-pwm", "mick111"],
        default="adafruit-hat-pwm",
        type=str,
    )
    parser.add_argument(
        "--led-scan-mode",
        action="store",
        help="Progressive or interlaced scan. 0 Progressive, 1 Interlaced (default)",
        default=1,
        choices=range(2),
        type=int,
    )
    parser.add_argument(
        "--led-pwm-lsb-nanoseconds",
        action="store",
        help="Base time-unit for the on-time in the lowest significant bit in nanoseconds. Default: 130",
        default=130,
        type=int,
    )
    parser.add_argument(
        "--led-show-refresh",
        action="store_true",
        help="Shows the current refresh rate of the LED panel",
    )
    parser.add_argument(
        "--led-slowdown-gpio",
        action="store",
        help="Slow down writing to GPIO. Range: 0..4. Default: 2",
        default=2,
        type=int,
    )
    parser.add_argument(
        "--led-no-hardware-pulse",
        action="store",
        help="Don't use hardware pin-pulse generation",
    )
    parser.add_argument(
        "--led-rgb-sequence",
        action="store",
        help="Switch if your matrix has led colors swapped. Default: RGB",
        default="RGB",
        type=str,
    )
    parser.add_argument(
        "--led-pixel-mapper",
        action="store",
        help='Apply pixel mappers. e.g "Rotate:90"',
        default="Rotate:180",
        type=str,
    )
    parser.add_argument(
        "--led-row-addr-type",
        action="store",
        help="0 = default; 1=AB-addressed panels; 2=row direct; 3=ABC-addressed panels; 4 = ABC Shift + DE direct",
        default=0,
        type=int,
        choices=[0, 1, 2, 3, 4],
    )
    parser.add_argument(
        "--led-multiplexing",
        action="store",
        help="Multiplexing type: 0=direct; 1=strip; 2=checker; 3=spiral; 4=ZStripe; 5=ZnMirrorZStripe; 6=coreman; 7=Kaler2Scan; 8=ZStripeUneven... (Default: 0)",
        default=0,
        type=int,
    )
    parser.add_argument(
        "--led-panel-type",
        action="store",
        help="Needed to initialize special panels. Supported: 'FM6126A'",
        default="",
        type=str,
    )

    # Matrice specific options
    parser.add_argument(
        "--conffile",
        help="Json file where parameters are read and saved.",
        default="/etc/ledbanner.json",
    )
    parser.add_argument(
        "--openweathermap_apikey",
        help="File Containing Open Weather Map API key.",
        default="/etc/openweathermap_apikey",
    )
    parser.add_argument(
        "--history",
        type=argparse.FileType("a+"),
        help="History of messages received by clients.",
        default=open("/var/log/ledbanner.history", "a+"),
    )
    parser.add_argument(
        "-l",
        "--listening-port",
        type=int,
        help="The port on which commands are received.",
        default=23735,
    )

    args = parser.parse_args()

    matrice = Matrice(args)
