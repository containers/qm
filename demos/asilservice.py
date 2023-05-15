#!/bin/python

import selinux

import socket
import os, os.path

socket_path="/run/uprotocol/uprotocol.sock"
if os.path.exists(socket_path):
  os.remove(socket_path)

selinux.setsockcreatecon("system_u:system_r:qm_t:s0")
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(socket_path)
while True:
  server.listen(1)
  conn, addr = server.accept()
  data = conn.recv(1024)
  conn.send(data)
  conn.close()
