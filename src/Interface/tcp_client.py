# -*- coding:utf-8 -*-
import socket
import json


class TCPClient:

    def __init__(self, ip, port):
        self.ip = None
        self.port = None
        self.socket = None
        self.in_ = None
        self.out = None
        self.connected = False
        self.debug = False
        self.buffer = b''
        self.ip = ip
        self.port = port

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            print(message)

    def connect(self):
        if not self.connected:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.ip, self.port))
                self.print_debug(
                    'connect to ' + str(self.ip) + '/' + str(self.port))
            except socket.gaierror:
                self.connected = False
                self.print_debug('fail to connect ' +
                                 str(self.ip) + '/' + str(self.port))
                return False
            self.connected = True
            return True
        else:
            self.print_debug('already connected')
            return False

    def disconnect(self):
        if self.connected:
            self.print_debug('client disconnected')
            try:
                self.socket.close()
            except NameError:
                pass
            self.connected = False

    def send(self, cmd, encoding):
        if not self.connected:
            return 'ERROR: Not connected'

        try:
            self.socket.send(bytes(cmd, encoding))
            self.print_debug('[Client] send : ' + cmd)
            return 'OK'
        except OSError:
            self.connected = False
            return 'ERROR: Server disconnected'

    def send_line(self, cmd, encoding):
        return self.send(cmd + '\n', encoding)

    def read_line_blocking(self):
        if not self.connected:
            return 'ERROR: Not connected'
        try:
            self.socket.settimeout(0)
        except socket.error:
            pass

        try:
            tmp = self.socket.recv(1024).decode('utf-8')
            self.print_debug('[Client] receive : ' + tmp)
            return tmp
        except OSError as e:
            return str(e)

    def read_line_non_blocking(self):
        if not self.connected:
            return 'ERROR: Not connected'
        try:
            self.socket.settimeout(10)
        except socket.error:
            pass

        try:
            tmp = self.socket.recv(1024)
            firstData = tmp[0]
            if firstData > 0:
                self.socket.settimeout(0)
                tmp = tmp.decode('utf-8')
                self.print_debug('[Client] receive : ' + tmp)
                return tmp
            else:
                return None
        except OSError:
            return None

    def read_json_object(self):
        if not self.connected:
            return 'ERROR: Not connected'
        try:
            self.socket.settimeout(10)
        except socket.error:
            pass

        try:
            received = self.buffer
            while True:
                data = self.socket.recv(1).to_bytes(1, byteorder="little")
                if int.from_bytes(data, byteorder='little') <= 0:
                    self.buffer = received
                    received = b''
                    break
                received += data
                # reset
                if not (received.decode().startswith('{')) and (received.decode().endswith('}{')):
                    received = b'{'
                try:
                    json.loads(received)
                    self.buffer = b''
                    break
                except json.JSONDecodeError as e:
                    print(e)
            if not received:
                return None
            self.print_debug('[Client] receive : ' + received.decode())
            return received.decode()
        except OSError:
            return None

    def is_connected(self):
        return self.connected
