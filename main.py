import json
import uuid
import time
import tkinter as tk
from tkinter import messagebox
import keyboard  # Requires admin
import socketio
from pynput import keyboard as pynput_keyboard
import os
import sys


def resource_path(relative_path: str) -> str:
    """Return an absolute path to a resource, working for dev and for PyInstaller onefile.

    When packaged with PyInstaller --onefile, files added with --add-data are extracted to
    a temporary folder available via sys._MEIPASS. In normal execution use the script dir.
    """
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

blocked_words = []   # Global - always updated by the server

# Overlay control
import queue

overlay_queue = None  # type: ignore
overlay_root = None  # type: ignore
keys_blocked = False

sio = socketio.Client()

username = os.getlogin()
mac_addr = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
client_id = f"{username}_{mac_addr}"

key_buffer = ''

def show_overlay():
    def check_password():
        if password_entry.get() == "ADMIN":
            root.destroy()
            # Safely unblock keys — unblocking a key that isn't blocked may raise KeyError
            safe_unblock_key('windows')
            safe_unblock_key('ctrl')
            safe_unblock_key('alt')
            safe_unblock_key('space')
            if sio.connected:
                sio.emit('status', {'client_id': client_id, 'status': 'enabled'})
                print("Sent 'enabled' status to server")
        else:
            messagebox.showerror("Incorrect Password", "Incorrect password. Try again.")

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.protocol("WM_DELETE_WINDOW", lambda: None)

    # Initialize overlay control queue and root so other threads can request close
    global overlay_queue, overlay_root, keys_blocked
    overlay_queue = queue.Queue()
    overlay_root = root

    # Block keys if not already blocked and mark state
    safe_block_key('windows')
    safe_block_key('ctrl')
    safe_block_key('alt')
    safe_block_key('space')
    keys_blocked = True

    # Poll the overlay_queue periodically; if 'destroy' is received, close overlay
    def _poll_overlay_queue():
        try:
            cmd = overlay_queue.get_nowait()
        except Exception:
            cmd = None
        if cmd == 'destroy':
            try:
                root.destroy()
            except Exception:
                pass
            return
        root.after(200, _poll_overlay_queue)

    label = tk.Label(root, text="System Disabled", font=("Helvetica", 48))
    label.pack(pady=50)

    password_label = tk.Label(root, text="Enter Password:", font=("Helvetica", 24))
    password_label.pack(pady=20)

    password_entry = tk.Entry(root, show="*", font=("Helvetica", 24))
    password_entry.pack()

    submit_button = tk.Button(root, text="Submit", command=check_password, font=("Helvetica", 24))
    submit_button.pack(pady=20)

    # start polling and run the overlay
    root.after(200, _poll_overlay_queue)
    root.mainloop()

    # After overlay closes, ensure keys are unblocked and clear overlay controls
    try:
        safe_unblock_key('windows')
        safe_unblock_key('ctrl')
        safe_unblock_key('alt')
        safe_unblock_key('space')
    except Exception:
        pass
    # Clear overlay controls (variables are already declared global at function start)
    overlay_queue = None
    overlay_root = None
    keys_blocked = False

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
    global blocked_words, key_buffer
    print('Received updated blocked words list')
    blocked_words = data['blocked_words']
    # Clear typing buffer to avoid immediately matching an already-typed word
    key_buffer = ''
    print('Blocked words now:', blocked_words)
    
@sio.on('system_disable')
def handle_system_disable(data=None):
    if not data or data.get('client_id') == client_id:
        print("System disabled by admin command.")
        show_overlay()

@sio.on('system_enable')
def handle_system_enable(data=None):
    if not data or data.get('client_id') == client_id:
        print("System enabled by admin command.")
        # Remove overlay, unblock keys, reset status, etc.
        # If overlay is active, ask it to close via the queue (thread-safe)
        global overlay_queue
        if overlay_queue is not None:
            try:
                overlay_queue.put('destroy')
            except Exception:
                pass
        # Also attempt to unblock keys safely
        safe_unblock_key('windows')
        safe_unblock_key('ctrl')
        safe_unblock_key('alt')
        safe_unblock_key('space')
        # If overlay is up, destroy it:
        # try: root.destroy() except: pass


def safe_unblock_key(key_name: str) -> None:
    """Attempt to unblock a key but ignore KeyError if the key wasn't blocked.

    The `keyboard` library raises KeyError when unhooking/unblocking a key that
    isn't currently hooked/blocked. Wrapping in try/except avoids crashing the
    Tkinter callback or event handler.
    """
    try:
        keyboard.unblock_key(key_name)
    except KeyError:
        # Key wasn't blocked — ignore silently
        pass


def safe_block_key(key_name: str) -> None:
    """Block a key only if it's not already blocked (use global keys_blocked flag).

    This avoids attempting to block keys repeatedly and keeps a simple local state.
    """
    global keys_blocked
    try:
        if not keys_blocked:
            keyboard.block_key(key_name)
    except Exception:
        # ignore blocking errors — best-effort
        pass


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
    # Try to load initial blocked words from a local file. When running as a
    # PyInstaller-built EXE, use resource_path to find bundled files.
    try:
        bw_path = resource_path('blocked_words.json')
        with open(bw_path, 'r') as f:
            blocked_words_data = json.load(f)
            blocked_words = blocked_words_data.get('blocked_words', [])
    except Exception:
        print("Waiting for blocked word list from server...")

    try:
        """These should be the production and development env files."""
        sio.connect('https://anything.anokxz.in')
    except Exception as e:
        print(f"Failed to connect to server: {e}")

    with pynput_keyboard.Listener(on_press=on_press) as listener:
        listener.join()

main()

