# -*- coding: utf-8 -*-
from TCPClient import TCPClient
import threading

class AbstractCommunicator:
	
	
	def __init__(self, hostname, port):
		self.client = TCPClient(hostname, port)
		self.isRosClient = False
		
	def start(self):
		if not self.client.connect():
			print('could not start ' + self.__class__.__name__)
			return 
		self.startReceiveThread()
		
	def stop(self):
		self.client.disconnect()
		
	def sendLine(self, command, encoding='utf-8'):
		if self.client.debug == True:
			print('{} send command -> {}'.format(self.__class__.__name__, command))
		self.client.sendLine(command, encoding)
		
	def startReceiveThread(self):
		def run(self):
			while self.client.connected:
				try:
					message = None
					if self.isRosClient:
						message = self.client.readJsonObject()
					else:
						message = self.client.readLineNonBlocking()
					if (message != None) and (not message.startswith('ERROR')):
						self.onReceived(message)
				except Exception:
					pass

		thread = threading.Thread(target=run, args=(self,))
		thread.start()

	def onReceived(self, message):
		pass
