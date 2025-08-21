import time
import random
import subprocess
import sys

# Try to install socketio if it's not found
try:
    import socketio
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'socketio'])
    import socketio

sio = socketio.Client()

@sio.event
def connect():
    print('Connected to server')

@sio.event
def disconnect():
    print('Disconnected from server')

class WordBlocker:
    def __init__(self):
        self.blocked_words = []  # Initialize empty list
        self.sio = socketio.Client()
        self.setup_socket_events()

    def setup_socket_events(self):
        @self.sio.event
        def connect(self):
            print('Connected to server')
            # Request current blocked words list upon connection
            self.sio.emit('request_blocked_words')

        @self.sio.event
        def disconnect(self):
            print('Disconnected from server')

        @self.sio.on('blocked_words_update')
        def handle_blocked_words_update(data):
            print('Received updated blocked words list')
            self.blocked_words = data['blocked_words']

    def start(self, server_url):
        try:
            self.sio.connect(server_url)
        except Exception as e:
            print(f"Failed to connect to server: {e}")
