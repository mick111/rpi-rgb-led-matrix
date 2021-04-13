#!/usr/bin/python3
# -*- coding: utf-8 -*-


class Compteur(object):
    """Compteur"""

    def __init__(self, name=None, compte=0):
        super(Compteur, self).__init__()
        self.name = name
        self.compte = 0

    def action(self, arguments):
        print("COMPT", arguments)
        if arguments is None:
            self.name = None
            self.compte = 0
            return

        arguments = arguments.split()

        if arguments[0] in ["+", "-"]:
            try:
                compte = int(arguments[1])
            except Exception:
                compte = 1
            self.compte += {"+": compte, "-": -compte}[arguments[0]]
            return

        self.name = arguments[0]
        try:
            self.compte = int(arguments[1])
        except Exception:
            self.compte = 0
