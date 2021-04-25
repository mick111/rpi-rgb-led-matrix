#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Uses the Octoprint API

from octorest import OctoRest
import time

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

        return {
            "name": job_info["job"]["file"]["name"],
            "completion": completion,
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

    progression = job_info["completion"]

    while job_info is not None:
        avancement = int(progression * 32)
        print(avancement * "o" + (32 - avancement) * "*")
        time.sleep(1)
        job_info = octoprint.job_info()
