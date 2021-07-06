#!/usr/bin/env python
import time
import math
import requests
import os
from PIL import Image
import random


# Classe pour gerer la Meteo
class Meteo(object):
    def __init__(self, openweathermap_apikey):
        self.openweathermap_apikey = openweathermap_apikey

    # Intervale de temps entre chaque mise a jour
    outsideTimeInterval = 10 * 60
    # Intervale de temps entre chaque mise a jour
    insideTimeInterval = 2 * 60

    # Timestamp sur la derniere mise a jour
    lastInsideUpdate = time.time() - 10 * 60
    lastOutsideUpdate = time.time() - 10 * 60

    # Temperatures interieures
    ins = {"chambre": None, "salon": None}
    # Temperature exterieure
    out = None
    # Icone a afficher
    ico = None

    # Temperature moyenne des temperatures interieures
    def meanTemps(self):
        # On met a jour si necessaire
        if time.time() - self.lastInsideUpdate > self.insideTimeInterval:
            self.updateInsideTemps()

        temps = 0.0
        count = 0
        for (piece, temp) in self.ins.items():
            try:
                temps += float(temp)
                count += 1
            except Exception:
                continue
        return None if count == 0 else (temps / count)

    def updateInsideTemps(self):
        # Mise a jour des temperatures interieures
        try:
            # On reinitialise les valeurs
            self.ins = {"chambre": None, "salon": None}
            for room in ["chambre", "salon"]:
                # Identifiants des peripheriques One-Wire
                ds = {"chambre": "28-03164783ecff", "salon": "28-0416526fcfff"}[room]
                # Mise a jour des temperatures par lecture des fichiers de One-Wire
                f = open(os.path.join("/sys/bus/w1/devices/", ds, "w1_slave")).read()
                # On reccupere et sauve la valeur
                self.ins[room] = float(f.split("\n")[1].split("=")[1]) / 1000
        except Exception:
            pass
        # On met a jour le timestamp
        self.lastInsideUpdate = time.time()

    # Mise a jour des temperatures interieures et exterieure
    def updateOutsideTemps(self):
        # Mise a jour de la temperature exterieure et de l'icone meteo
        try:
            # On reinitialise les valeurs
            self.out = None
            self.ico = None

            # On reccupere les valeurs par internet
            j = requests.get(
                "http://api.openweathermap.org/data/2.5/weather?id=2968815&APPID={}&units=metric".format(
                    self.openweathermap_apikey
                ),
                timeout=1,
            ).json()
            self.out = float(j["main"]["temp"])
            iconName = j["weather"][0]["icon"]

            self.ico = {
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
            }.get(iconName, "error")
        except Exception:
            self.ico = "error"

        # On met a jour le timestamp
        self.lastOutsideUpdate = time.time()

    def insideTemperature(self, room):
        # On met a jour si necessaire
        if time.time() - self.lastInsideUpdate > self.insideTimeInterval:
            self.updateInsideTemps()
        return self.ins[room]

    def outsideTemperature(self):
        # On met a jour si necessaire
        if time.time() - self.lastOutsideUpdate > self.outsideTimeInterval:
            self.updateOutsideTemps()
        return self.out

    selectedAnimation = 0
    iconNo = 0

    def icon(self, size):
        # Update the temperatures if needed
        if time.time() - self.lastOutsideUpdate > self.outsideTimeInterval:
            self.updateOutsideTemps()

        # Tick + 1
        self.iconNo = self.iconNo + 1

        if size == 16:
            path = "./weathericons/mick111/"
        else:
            path = "./weathericons/unicornhat_weather_icons-master/png/SD/"

        im = Image.open(path + self.ico + ".png").convert("RGB")

        # Deduce the number of images according to the size of the file
        imageWidth = im.size[0]
        imageHeight = im.size[1]
        nbAnimations = int(math.ceil(float(imageHeight) / size))
        nbIcons = int(math.ceil(float(imageWidth) / size))

        # Make some temporization on first image
        moduleImages = nbIcons + (10 if nbAnimations > 1 else 0)

        # Get the icon number
        iconNo = self.iconNo % moduleImages

        # Change selected animation if we are at the end of the current animation
        if iconNo == (moduleImages - 1):
            self.selectedAnimation = int(math.floor(random.uniform(0, nbAnimations)))

        if self.selectedAnimation >= nbAnimations:
            self.selectedAnimation = 0

        # Compute horizontal and vertical offset
        hOffset = size * (iconNo if iconNo < nbIcons else 0)
        vOffset = size * self.selectedAnimation

        image = im.crop((hOffset, vOffset, hOffset + size, vOffset + size))

        return image
