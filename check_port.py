import socket
s = socket.socket()
s.settimeout(2)
result = s.connect_ex(('localhost', 8001))
if result == 0:
    print('Port 8001: OPEN')
else:
    print('Port 8001: CLOSED')
s.close()