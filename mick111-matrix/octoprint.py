#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Uses the Octoprint API

from octorest import OctoRest
import time
import datetime
import json


class Octoprint(object):
    def __init__(self, url, apikey):
        self.url = url
        self.apikey = apikey
        self.connect()

    def connect(self):
        self.octoprint = None
        try:
            self.octoprint = OctoRest(url=self.url, apikey=self.apikey)
        except ConnectionError as ex:
            print(ex)

    def job_info(self):
        if self.octoprint is None:
            self.connect()
        if self.octoprint is None:
            return None

        job_info = self.octoprint.job_info()
        if job_info["state"] != "Printing":
            return None

        completion = (
            job_info["progress"]["completion"] if "progress" in job_info else 0.0
        )
        time_left = (
            job_info["progress"]["printTimeLeft"] if "progress" in job_info else 0.0
        )

        return {
            "name": job_info["job"]["file"]["name"],
            "completion": completion,
            "time_left": time_left,
        }


if __name__ == "__main__":
    octoprint_json = json.loads(open("/etc/octoprint_creds.json").read())
    octoprint_url, octoprint_apikey = (
        octoprint_json["url"],
        octoprint_json["apikey"],
    )
    octoprint = Octoprint(url=octoprint_url, apikey=octoprint_apikey)

    job_info = octoprint.job_info()
    if job_info is None:
        exit(octoprint.octoprint.job_info()["state"])

    while job_info is not None:
        progression = job_info["completion"]
        time_left = job_info["time_left"]

        print(
            (
                "{:3.2f}% ".format(progression)
                + str(datetime.timedelta(seconds=time_left))
            ).center(32)
        )
        avancement = int(progression / 100 * 32)
        print(avancement * "o" + (32 - avancement) * "*")
        job_info = octoprint.job_info()
        if job_info is None:
            break
        time.sleep(1)
