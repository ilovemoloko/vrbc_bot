import sqlite3
from utils import SingletonMeta
import os
import threading


db_path = 'db/userdata.db'
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = sqlite3.connect(db_path, check_same_thread=False)
lock = threading.RLock()


def locked(func):
    def wrapper(*args, **kwargs):
        with lock:
            return func(*args, **kwargs)
    return wrapper


def connected(func):
    def wrapper(*args, **kwargs):
        with conn:
            return func(*args, **kwargs)
    return wrapper


class FSMDatabase(metaclass=SingletonMeta):
    def __init__(self):
        self.conn = conn
        self.create_table()

    @locked
    @connected
    def create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                state TEXT, 
                local_uid INTEGER
            )
        ''')
        self.conn.commit()

    @locked
    @connected
    def add_user(self, context, state):
        user_id_combined = f"{context.src}_{context.user_id}"
        self.conn.execute('''
            INSERT INTO users (user_id, state, local_uid) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET state=excluded.state
        ''', (user_id_combined, state, None))

    @locked
    @connected
    def update_state(self, context, new_state):
        user_id_combined = f"{context.src}_{context.user_id}"
        self.conn.execute('''
            UPDATE users SET state = ? WHERE user_id = ?
        ''', (new_state, user_id_combined))

    @locked
    def get_state(self, context):
        user_id_combined = f"{context.src}_{context.user_id}"
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT state FROM users WHERE user_id = ?
        ''', (user_id_combined,))
        result = cursor.fetchone()
        if result is None:
            self.add_user(context, 'first_msg')
            return 'first_msg'
        return result[0]

    @locked
    @connected
    def set_local_user_id(self, context, local_user_id):
        user_id_combined = f"{context.src}_{context.user_id}"
        self.conn.execute('''
            UPDATE users SET local_uid = ? WHERE user_id = ?
        ''', (local_user_id, user_id_combined))

    @locked
    def get_local_user_id(self, context):
        user_id_combined = f"{context.src}_{context.user_id}"
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT local_uid FROM users WHERE user_id = ?
        ''', (user_id_combined,))
        result = cursor.fetchone()
        if result is None:
            return None
        return result[0]

    @locked
    def close(self):
        self.conn.close()


fsm_db = FSMDatabase()


class LocalUsersDatabase(metaclass=SingletonMeta):
    def __init__(self):
        self.conn = conn
        self.create_table()

    @locked
    @connected
    def create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS localusers (
                local_user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                info TEXT DEFAULT '{}'
            )
        ''')

    @locked
    @connected
    def create_user(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO localusers DEFAULT VALUES
        ''')
        self.conn.commit()
        return cursor.lastrowid

    @locked
    def get_info(self, context):
        local_user_id = fsm_db.get_local_user_id(context)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT info FROM localusers WHERE local_user_id = ?
        ''', (local_user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    @locked
    @connected
    def update_info(self, context, new_info):
        local_user_id = fsm_db.get_local_user_id(context)
        self.conn.execute('''
            UPDATE localusers SET info = ? WHERE local_user_id = ?
        ''', (new_info, local_user_id))

    @locked
    def close(self):
        self.conn.close()

localuser_db = LocalUsersDatabase()
