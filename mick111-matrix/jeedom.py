#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Access to Jeedom
import socket


class Jeedom(object):
    id_cmd = {
        'boutton_compte': {'set': (528, 'slider'), 'get': 526},
        'boutton_batterie': {'set': (534, 'slider'), 'get': 533},
        'boutton_unite': {'set': (529, 'title=&message'), 'get': 527},
    }

    def __init__(self, host, port, apikey):
        self.apikey = apikey
        self.host = host
        self.port = port
        self.addr = socket.getaddrinfo(host, port, family=socket.AF_INET, proto=socket.IPPROTO_TCP)[0][-1]
        print(self.addr)

    def command(self, command, value=None):
        if value is None:
            id_cmd = self.id_cmd[command]['get']
        else:
            id_cmd = self.id_cmd[command]['set'][0]
            param_cmd_set = self.id_cmd[command]['set'][1]

        path = "core/api/jeeApi.php?apikey={}&type=cmd&id={}".format(self.apikey, id_cmd)
        if value is not None:
            path += "&{}={}".format(param_cmd_set, value)
        try: 
            s = socket.socket()
            s.connect(self.addr)
            s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n' % (path, self.host), 'utf8'))
            datas = bytes()
            while True:
                data = s.recv(100)
                if data:
                    datas += data
                else:
                    break
            datas_str = str(datas, 'utf8')
            s.close()
        except Exception:
            return None
        ret = datas_str.split(2*'\r\n', 1)
        return ret[1].strip() if len(ret) > 1 else None

    def __getattr__(self, name):
        if name in self.id_cmd:
            return self.command(name)
        else:
            raise AttributeError(name)

    def __setattr__(self, key, value):
        if key in self.id_cmd:
            self.command(key, value)
        else:
            super().__setattr__(key, value)


if __name__ == '__main__':
    import json
    jeedom_json = json.loads(open("/Users/mmouchous/Downloads/API_KEY").read())
    jeedom_host, jeedom_port, jeedom_apikey = (
        jeedom_json["host"],
        jeedom_json["port"],
        jeedom_json["apikey"],
    )
    jeedom = Jeedom(host=jeedom_host, port=jeedom_port, apikey=jeedom_apikey)
    print(jeedom.boutton_batterie)
    print(jeedom.boutton_compte)
    print(jeedom.boutton_unite)
    jeedom.boutton_unite = "doses"
    print(jeedom.boutton_unite)
