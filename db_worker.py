import copy
import sqlite3

import local_server
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


def return_false_on_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            return False
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
        ''', (str(new_info), local_user_id))

    @locked
    def close(self):
        self.conn.close()


localuser_db = LocalUsersDatabase()


class DBInfoWorker(metaclass=SingletonMeta):
    def get_value(self, context, key, src=None):
        info = self.get_info(context)
        value = info.get(key, None)
        if value is None:
            if src is not None:
                pool_src = src
            else:
                pool_src = local_server.get_default_values()['default_user']
            value = pool_src[key]
        return value

    def set_value(self, context, key, value):
        info = self.get_info(context)
        info[key] = value
        if value == local_server.get_default_values()['default_user'][key]:
            info.pop(key)
        localuser_db.update_info(context, info)

    def set_info(self, context, info):
        info = str(info)
        localuser_db.update_info(context, info)

    def get_info(self, context):
        return eval(localuser_db.get_info(context))

    def get_cart_size(self, context):
        size = 0
        cart = self.get_value(context, 'cart')
        for item in cart:
            if isinstance(cart[item], list):
                size += len(cart[item])
            else:
                size += 1
        return size

    @staticmethod
    def check_stackable(item_info):
        stackable = False
        if isinstance(item_info[-1], dict):
            stackable = item_info[-1].get('stackable', False)
        return stackable

    @return_false_on_error
    def add_to_cart(self, context, item, amount):
        cart_size = self.get_cart_size(context)
        cart_max_size = self.get_value(context, 'cart_size')
        cart = self.get_value(context, 'cart')
        item_info = self.get_bot_values(context)['items'][item]
        if cart_size >= cart_max_size:
            return False

        stackable = self.check_stackable(item_info)
        if not stackable:
            cart[item] = amount
        else:
            items_array = cart.get(item, [])
            items_array.append(amount)
            items_array = list(set(items_array))
            cart[item] = items_array

        self.set_value(context, 'cart', cart)
        return True

    @return_false_on_error
    def del_from_cart(self, context, item, amount=None):
        cart = self.get_value(context, 'cart')
        if item in cart:
            if amount is not None:
                if isinstance(cart[item], list):
                    if amount not in cart[item]:
                        return False
                    cart[item].remove(amount)
                    if len(cart[item]) == 0:
                        cart.pop(item)
                    self.set_value(context, 'cart', cart)
                    return True
                else:
                    return False
            cart.pop(item)
            self.set_value(context, 'cart', cart)
            return True
        return False

    def clear_cart(self, context):
        self.set_value(context, 'cart', {})

    def get_bot_values(self, context):
        default_values = local_server.get_default_values()
        default_values = copy.deepcopy(default_values)
        boosts_ids = self.get_value(context, 'boosts')
        active_boosts = self.get_value(context, 'active_boosts')
        boosts_server = local_server.get_default_values()['boosts']
        passive_boosts = []

        for bid in boosts_ids:
            boost = boosts_server[bid]
            active = False
            if boost['type'] == 'passive':
                active = True
            if active:
                passive_boosts.append(bid)
        passive_boosts.extend(active_boosts)

        for bid in passive_boosts:
            local_server.mod_values(default_values, bid)

        categorized = local_server.categorize_items(default_values['items'])
        default_values['categorized'] = categorized
        return default_values


info_worker = DBInfoWorker()
