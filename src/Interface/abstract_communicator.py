# -*- coding: utf-8 -*-
from tcp_client import TCPClient
import threading


class AbstractCommunicator:

    def __init__(self, hostname, port):
        self.client = TCPClient(hostname, port)

    def start(self):
        if not self.client.connect():
            print('could not start ' + self.__class__.__name__)
            return
        self.start_receive_thread()

    def stop(self):
        self.client.disconnect()

    def send_line(self, command, encoding='utf-8'):
        if self.client.debug:
            print('{} send command -> {}'.format(self.__class__.__name__, command))
        self.client.send_line(command, encoding)

    def start_receive_thread(self):
        def run(self):
            while self.client.connected:
                try:
                    message = None
                    message = self.client.read_line_non_blocking()
                    if (message != None) and (not message.startswith('ERROR')):
                        self.on_received(message)
                except Exception as e:
                    pass
        thread = threading.Thread(target=run, args=(self,))
        thread.start()

    def on_received(self, message):
        pass
