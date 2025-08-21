# Real-Time Keylogger Blocked-Word Manager

A Flask/Socket.IO dashboard to manage a live blocklist of words. Admins can add, edit, or delete blocked words and all connected Python clients update instantly. If a blocked word is typed, the client system locks until unlocked with an admin password.

## Features

* **Web dashboard:** Add, edit, or delete blocked words in real time
* **Live update:** All clients instantly receive blocklist changes via Socket.IO
* **Client monitoring:** Dashboard shows all clients & statuses
* **Instant lock:** Typing a blocked word disables the client until an admin password is entered
* **History log:** All incidents are viewable from the dashboard
* **Admin login:** Secure, hashed password authentication

## Quick Start

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

2. **Set up Python environment**

```bash
conda create -n keylogger_env python=3.11
conda activate keylogger_env
pip install -r requirements.txt
```

3. **Run the server (in one terminal)**

```bash
python app.py
```

4. **Run the client (in another terminal)**

```bash
python main.py
```

5. Access the web dashboard at http://127.0.0.1:5000.

## How It Works

* The admin dashboard lets you manage the list of blocked words.
* Any change to the blocklist is pushed live to all clients via Socket.IO.
* If a client types a blocked word, their system is locked with a fullscreen overlay until the correct admin password is entered.
* All incidents are logged and viewable in the dashboard.

## Requirements

* Python 3.10+
* Flask
* Flask-SocketIO
* python-socketio
* pynput
* keyboard
* werkzeug

Install all dependencies:

```bash
pip install -r requirements.txt
```

## Security & Legal

***Important: Use this project only in controlled/demo environments with informed consent. Unauthorized use may violate privacy and local laws.***

## License

MIT
