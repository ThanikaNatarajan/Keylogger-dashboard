import json
import time
import tkinter as tk
from tkinter import messagebox
import keyboard  # Requires admin
import socketio
from pynput import keyboard as pynput_keyboard
import os

blocked_words = []   # Global - always updated by the server

sio = socketio.Client()

client_id = os.path.expanduser('~').split('\\')[-1]  # Adjust for your OS if needed

key_buffer = ''

def show_overlay():
    def check_password():
        if password_entry.get() == "ADMIN":
            root.destroy()
            keyboard.unblock_key('windows')
            keyboard.unblock_key('ctrl')
            keyboard.unblock_key('alt')
            keyboard.unblock_key('space')
            if sio.connected:
                sio.emit('status', {'client_id': client_id, 'status': 'enabled'})
                print("Sent 'enabled' status to server")
        else:
            messagebox.showerror("Incorrect Password", "Incorrect password. Try again.")

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.protocol("WM_DELETE_WINDOW", lambda: None)

    keyboard.block_key('windows')
    keyboard.block_key('ctrl')
    keyboard.block_key('alt')
    keyboard.block_key('space')

    label = tk.Label(root, text="System Disabled", font=("Helvetica", 48))
    label.pack(pady=50)

    password_label = tk.Label(root, text="Enter Password:", font=("Helvetica", 24))
    password_label.pack(pady=20)

    password_entry = tk.Entry(root, show="*", font=("Helvetica", 24))
    password_entry.pack()

    submit_button = tk.Button(root, text="Submit", command=check_password, font=("Helvetica", 24))
    submit_button.pack(pady=20)

    root.mainloop()

@sio.event
def connect():
    print('Connected to server')
    sio.emit('status', {'client_id': client_id, 'status': 'enabled'})
    sio.emit('request_blocked_words')

@sio.event
def disconnect():
    print('Disconnected from server')

@sio.on('blocked_words_update')
def handle_blocked_words_update(data):
    global blocked_words
    print('Received updated blocked words list')
    blocked_words = data['blocked_words']
    print('Blocked words now:', blocked_words)

def send_disabled_status(blocked_word):
    if sio.connected:
        sio.emit('blocked_word', {'client_id': client_id, 'word': blocked_word})
        sio.emit('status', {'client_id': client_id, 'status': 'disabled'})
        print(f"Sent 'disabled' status and blocked word '{blocked_word}' to server")
    show_overlay()

def on_press(key):
    global key_buffer
    try:
        key_buffer += key.char
    except AttributeError:
        if key == pynput_keyboard.Key.space:
            key_buffer += ' '
        elif key == pynput_keyboard.Key.backspace and len(key_buffer) > 0:
            key_buffer = key_buffer[:-1]

    for word in blocked_words:
        if word.lower() in key_buffer.lower():
            send_disabled_status(word)
            key_buffer = ''
            break

def main():
    global blocked_words
    try:
        with open('blocked_words.json', 'r') as f:
            blocked_words_data = json.load(f)
            blocked_words = blocked_words_data['blocked_words']
    except Exception as e:
        print("Waiting for blocked word list from server...")

    try:
        sio.connect('http://127.0.0.1:5000')
    except Exception as e:
        print(f"Failed to connect to server: {e}")

    with pynput_keyboard.Listener(on_press=on_press) as listener:
        listener.join()
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
