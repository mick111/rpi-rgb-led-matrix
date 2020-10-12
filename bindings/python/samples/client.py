#!/usr/bin/env python
# Run a server to make things with the display
import socket

import Tkinter as tk
from tkColorChooser import askcolor

sock = None


def disconnect():
    global sock
    if sock is not None:
        sock.close()
    sock = None
    updateUI()


def connect():
    global sock
    if sock is not None:
        sock.close()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ipPort = HostPort.get().split(":")
    (ip, port) = ipPort[0], int(ipPort[1]) if len(ipPort) > 0 else 23735
    try:
        sock.connect((ip, port))
    except Exception as e:
        print(e)
        sock.close()
        sock = None
    updateUI()


def send():
    global sock
    if sock is None:
        updateUI()
        return
    try:
        sock.sendall("TEXT " + Message.get())
        sock.sendall(
            "COLOR "
            + str(float(color[0]) / 255)
            + " "
            + str(float(color[1]) / 255)
            + " "
            + str(float(color[2]) / 255)
        )
    except Exception as e:
        print(e)
        sock.close()
        sock = None
        updateUI()


def updateUI():
    if sock is not None:
        connectBouton["text"] = "Deconnecter"
        connectBouton["command"] = disconnect
        entree["state"] = tk.DISABLED
        messageEntree["state"] = tk.NORMAL
        envoiBouton["state"] = tk.NORMAL
        colorBouton["state"] = tk.NORMAL
    else:
        connectBouton["text"] = "Connecter"
        connectBouton["command"] = connect
        entree["state"] = tk.NORMAL
        messageEntree["state"] = tk.DISABLED
        envoiBouton["state"] = tk.DISABLED
        colorBouton["state"] = tk.DISABLED
    messageEntree["fg"] = colorHex


color = (255, 255, 255)
colorHex = "#ffffff"


def getColor():
    global color, colorHex
    color, colorHex = askcolor()
    if color is not None:
        sock.sendall(
            "COLOR "
            + str(float(color[0]) / 255)
            + " "
            + str(float(color[1]) / 255)
            + " "
            + str(float(color[2]) / 255)
        )
    updateUI()


fenetre = tk.Tk()

frameConnect = tk.Frame(fenetre)

label = tk.Label(frameConnect, text="IP(:port) :")
label.pack(side=tk.LEFT)

HostPort = tk.StringVar()
HostPort.set("192.168.42.16:23735")
entree = tk.Entry(frameConnect, textvariable=HostPort, width=30)
entree.pack(side=tk.LEFT)

connectBouton = tk.Button(frameConnect, text="Connecter", command=connect)
connectBouton.pack()

frameConnect.pack(side=tk.TOP)

frameMessage = tk.Frame(fenetre)

colorBouton = tk.Button(frameMessage, text="Select Color", command=getColor)
colorBouton.pack(side=tk.LEFT)

Message = tk.StringVar()
messageEntree = tk.Entry(
    frameMessage, textvariable=Message, width=30, bg="black", fg="white"
)
messageEntree.pack(side=tk.LEFT)
envoiBouton = tk.Button(frameMessage, text="Envoyer", command=send)
envoiBouton.pack(side=tk.LEFT)

frameMessage.pack(side=tk.TOP)

updateUI()

fenetre.mainloop()
