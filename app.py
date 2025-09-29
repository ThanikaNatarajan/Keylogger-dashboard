import os
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
DB_NAME = 'clients.db'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT UNIQUE,
        status TEXT,
        sid TEXT,
        ip TEXT
    )''')
    conn.commit()
    create_users_table(conn)
    create_history_table(conn)
    conn.close()

def create_users_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    conn.commit()

def create_history_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        word TEXT NOT NULL,
        FOREIGN KEY (client_id) REFERENCES clients(client_id)
    )''')
    conn.commit()

def set_client_status(client_id, status, sid, ip):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO clients (client_id, status, sid, ip)
                 VALUES (?, ?, ?, ?)''', (client_id, status, sid, ip))
    conn.commit()
    conn.close()

def add_history_record(client_id, word):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO history (client_id, word) VALUES (?, ?)", (client_id, word))
    conn.commit()
    conn.close()

def remove_client_by_sid(sid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM clients WHERE sid = ?", (sid,))
    conn.commit()
    conn.close()

def get_all_statuses():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT client_id, status, ip FROM clients")
    rows = c.fetchall()
    conn.close()
    return {row[0]: {'status': row[1], 'ip': row[2]} for row in rows}

init_db()

BLOCKED_WORDS_FILE = os.path.join(os.path.dirname(__file__), 'blocked_words.json')

def read_blocked_words():
    # Try to read blocked_words.json, create if missing
    if not os.path.exists(BLOCKED_WORDS_FILE):
        with open(BLOCKED_WORDS_FILE, 'w') as f:
            json.dump({"blocked_words": []}, f, indent=2)
        return []
    with open(BLOCKED_WORDS_FILE, 'r') as f:
        data = json.load(f)
    return data.get("blocked_words", [])

def write_blocked_words(words_list):
    with open(BLOCKED_WORDS_FILE, 'w') as f:
        json.dump({"blocked_words": words_list}, f, indent=2)

@app.route('/')
@login_required
def index():
    current_statuses = get_all_statuses()
    return render_template('index.html', statuses=current_statuses)

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    client_id = data.get("client_id")
    new_status = data.get("status", "enabled")
    if client_id:
        # Update status in DB
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE clients SET status = ? WHERE client_id = ?", (new_status, client_id))
        conn.commit()
        conn.close()
        return {"message": f"Set status to {new_status} for {client_id}"}, 200
    return {"error": "client_id required"}, 400

# ---- SocketIO Events ----

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    remove_client_by_sid(request.sid)
    emit('status_update', get_all_statuses(), broadcast=True)

@socketio.on('status')
def handle_status(data):
    client_id = data['client_id']
    status = data['status']
    client_ip = request.remote_addr  # The IP address of the client connection
    set_client_status(client_id, status, request.sid, client_ip)
    emit('status_update', get_all_statuses(), broadcast=True)

@socketio.on('blocked_word')
def handle_blocked_word(data):
    client_id = data['client_id']
    word = data['word']
    add_history_record(client_id, word)
    print(f"Blocked word '{word}' detected from client '{client_id}' and recorded.")

@socketio.on('request_blocked_words')
def handle_blocked_words_request():
    words_list = read_blocked_words()
    emit('blocked_words_update', {'blocked_words': words_list})

# ------------- Authentication Routes -------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            session['user_id'] = username
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Username already exists')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            session['user_id'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/history')
@login_required
def history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Select all columns for each client
    c.execute("SELECT client_id, status, ip FROM clients ORDER BY client_id")
    clients = []
    for row in c.fetchall():
        clients.append({
            'client_name': row[0],  # client_id
            'system_number': row[0],  # or however you define system number
            'ip': row[2],
            'status': 'Online' if row[1] == 'enabled' else 'Offline'
        })
    conn.close()
    return render_template('history_users.html', clients=clients)



@app.route('/history/<client_id>')
@login_required
def history_user(client_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # All incidents for the user (most recent first)
    c.execute("""
        SELECT word, COUNT(*) AS total_times, MAX(timestamp) AS last_time
        FROM history
        WHERE client_id = ?
        GROUP BY word
        ORDER BY total_times DESC, last_time DESC
    """, (client_id,))
    word_stats = [
    {'word': row[0], 'total': row[1], 'last': row[2]}
    for row in c.fetchall()
    ]

    conn.close()
    return render_template('history_user.html', client_id=client_id, word_stats=word_stats)


@app.route('/manage_blocked_words', methods=['GET', 'POST'])
@login_required
def manage_blocked_words():
    if request.method == 'POST':
        action = request.form.get('action')
        words_list = read_blocked_words()
        changed = False

        if action == 'add':
            new_word = request.form.get('new_word', '').strip()
            if new_word and new_word.lower() not in [w.lower() for w in words_list]:
                words_list.append(new_word)
                write_blocked_words(words_list)
                changed = True
        elif action == 'delete':
            word_to_delete = request.form.get('word_to_delete', '')
            if word_to_delete in words_list:
                words_list = [w for w in words_list if w != word_to_delete]
                write_blocked_words(words_list)
                changed = True
        elif action == 'edit':
            old_word = request.form.get('old_word', '')
            new_word = request.form.get('new_word', '').strip()
            # Prevent duplicate blocked words on edit
            if old_word in words_list and new_word and new_word.lower() not in [w.lower() for w in words_list if w != old_word]:
                updated_list = []
                for w in words_list:
                    if w == old_word:
                        updated_list.append(new_word)
                    else:
                        updated_list.append(w)
                write_blocked_words(updated_list)
                changed = True

        # Broadcast to clients if the list has changed
        if changed:
            broadcast_list = read_blocked_words()
            socketio.emit('blocked_words_update', {'blocked_words': broadcast_list})


        return redirect(url_for('manage_blocked_words'))

    current_words = read_blocked_words()
    return render_template('manage_blocked_words.html', blocked_words=current_words)

if __name__ == '__main__':
    #socketio.run(app, debug=True)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
