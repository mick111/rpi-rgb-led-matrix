#!/usr/bin/env python
import requests
import datetime


class MoteurTV(object):
    """Compteur"""

    last_time = datetime.datetime.now()
    last_etat = None
    # {"curr_position_pourcent": 72.0009, "etat": {"ratio_vitesse": 1.73333, "action": "stop", "position": 14825, "maximum": 20590, "pin_onoff": 13, "pin_direction": 12}, "curr_position": 14825, "info": "Etat OK"}

    URL = "http://192.168.0.129:28692"

    def __init__(self, url=None, apikey=None):
        super(MoteurTV, self).__init__()
        if url is not None:
            self.URL = url

    def etat(self):
        if datetime.datetime.now() - self.last_time < datetime.timedelta(seconds=2):
            self.last_etat = None

        if self.last_etat is None:
            self.last_etat = requests.get(f"{self.URL}/etat").json()
            self.last_time = datetime.datetime.now()
        return self.last_etat

    def position_pourcent(self):
        try:
            return self.etat()["curr_position_pourcent"]
        except Exception as e:
            print(e)
        return 0


if __name__ == "__main__":
    print("MoteurTV")
    moteur_tv = MoteurTV()
    print(moteur_tv.etat())
    print(moteur_tv.position_pourcent())
