#!/bin/python
import selinux
import socket
import os, os.path, shutil, sys


socket_dir="/run/asilservice"
socket_path=socket_dir + "/asilservice.sock"
if os.path.exists(socket_dir):
  shutil.rmtree(socket_dir)

selinux.setfscreatecon("system_u:object_r:qm_file_t:s0")
selinux.setsockcreatecon("system_u:system_r:qm_t:s0")
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
os.mkdir(socket_dir)
server.bind(socket_path)
server.listen(1)
conn, addr = server.accept()
try:
  while True:
    data = conn.recv(1024)
    conn.send("ASIL reply: ".encode())
    conn.send(data)
    if data.decode().strip()=="goodby":
      break
except:
  pass
print(sys.argv[0] + ": exited\n")
conn.close()
