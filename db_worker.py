import copy
import sqlite3
import local_server
import os
import threading

db_path = 'db/userdata.db'
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = sqlite3.connect(db_path, check_same_thread=False)
lock = threading.RLock()


class SingletonMeta(type):
    _instances = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


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
                local_uid INTEGER,
                brawl_data INTEGER
            )
        ''')
        self.conn.commit()

    @locked
    @connected
    def delete_by_userid(self, user_id, src="vk"):
        user_id_combined = f"{src}_{user_id}"
        self.conn.execute('''
            DELETE FROM users WHERE user_id = ?
        ''', (user_id_combined,))
        self.conn.commit()

    @locked
    @connected
    def get_by_userid(self, user_id, src="vk"):
        user_id_combined = f"{src}_{user_id}"
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, state, local_uid, brawl_data FROM users WHERE user_id = ?
        ''', (user_id_combined,))
        result = cursor.fetchone()
        if result is None:
            return -1
        return result

    @locked
    @connected
    def add_user(self, context, state):
        user_id_combined = f"{context.src}_{context.user_id}"
        self.conn.execute('''
            INSERT INTO users (user_id, state, local_uid, brawl_data) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET state=excluded.state
        ''', (user_id_combined, state, None, -1))
        self.conn.commit()

    @locked
    @connected
    def set_brawl_data(self, context, brawl_data):
        user_id_combined = f"{context.src}_{context.user_id}"
        self.conn.execute('''
            UPDATE users SET brawl_data = ? WHERE user_id = ?
        ''', (brawl_data, user_id_combined))
        self.conn.commit()

    @locked
    def get_brawl_data(self, context):
        user_id_combined = f"{context.src}_{context.user_id}"
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT brawl_data FROM users WHERE user_id = ?
        ''', (user_id_combined,))
        result = cursor.fetchone()
        if result is None:
            return -1
        return result[0]

    @locked
    @connected
    def update_state(self, context, new_state):
        user_id_combined = f"{context.src}_{context.user_id}"
        self.conn.execute('''
            UPDATE users SET state = ? WHERE user_id = ?
        ''', (new_state, user_id_combined))
        self.conn.commit()

    @locked
    @connected
    def hack_reset(self):
        self.conn.execute('''
            UPDATE users SET state = 'first_msg' WHERE state = 'hack_process'
        ''')
        self.conn.commit()

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
        self.conn.commit()

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
    def get_all_by_local_user_id(self, local_user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, state FROM users WHERE local_uid = ?
        ''', (local_user_id,))
        result = cursor.fetchall()
        return result

    @locked
    def close(self):
        self.conn.close()


fsm_db = FSMDatabase()


def give_boost(context, boost_id, amount=1):
    user_boosts = info_worker.get_value(context, 'boosts')
    if boost_id not in user_boosts:
        user_boosts[boost_id] = 0
    user_boosts[boost_id] += 1
    info_worker.set_value(context, 'boosts', user_boosts)

class CouponDB(metaclass=SingletonMeta):
    def __init__(self):
        self.conn = conn
        self.create_table()

    @locked
    @connected
    def create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS coupon (
                coup_name TEXT PRIMARY KEY,
                uses_left INTEGER,
                id TEXT,
                users TEXT
            )
        ''')
        self.conn.commit()

    @locked
    @connected
    def add_coup(self, cname, uses, cId):
        self.conn.execute('''
            INSERT INTO coupon (coup_name, uses_left, id, users) VALUES (?, ?, ?, ?)
        ''', (cname, uses, cId, ""))
        self.conn.commit()

    @locked
    def get_coup_info(self, coupName):
        cursor = self.conn.cursor()
        cursor.execute('''
                    SELECT uses_left, id, users FROM coupon WHERE coup_name = ?
                ''', (coupName,))
        result = cursor.fetchone()
        return result

    @locked
    def hasUsed(self, coupName, context):
        data = self.get_coup_info(coupName)
        return str(fsm_db.get_local_user_id(context)) in data[2].split(" ")

    @locked
    @connected
    def removeCoup(self, coupName):
        cursor = self.conn.cursor()
        cursor.execute('''
        DELETE FROM coupon WHERE coup_name = ?
        ''', (coupName,))

    @locked
    @connected
    def useCoup(self, coupName, context):
        local_id = str(fsm_db.get_local_user_id(context))
        cursor = self.conn.cursor()
        data = self.get_coup_info(coupName)
        if not data:
            return 0
        uses_left, coupon_id, all_used = data
        if local_id in all_used.split(' '):
            return -1

        give_boost(context, coupon_id)

        uses_left -= 1
        all_used = all_used + local_id + ' '
        if uses_left == 0:
            self.removeCoup(coupName)
        else:
            cursor.execute('''
            UPDATE coupon SET uses_left = ?, users = ? WHERE coup_name = ?
            ''', (uses_left, all_used, coupName))
        return 1


coupon_db = CouponDB()


class BCAccountDB(metaclass=SingletonMeta):
    def __init__(self):
        self.conn = conn
        self.create_table()

    @locked
    @connected
    def create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                account_code TEXT PRIMARY KEY,
                user_id INTEGER,
                isjp BOOLEAN,
                originalcode TEXT,
                disabled INTEGER
            )
        ''')
        self.conn.commit()

    @locked
    @connected
    def add_account(self, user_id, account_code, isjp, originalcode):
        self.conn.execute('''
            INSERT INTO accounts (account_code, user_id, isjp, originalcode, disabled) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(account_code) DO UPDATE SET user_id=excluded.user_id, isjp=excluded.isjp, originalcode=excluded.originalcode, disabled=excluded.disabled
        ''', (account_code, user_id, isjp, originalcode, False))
        self.conn.commit()

    @locked
    @connected
    def set_disabled(self, account_code, disabled):
        self.conn.execute('''
            UPDATE accounts SET disabled = ? WHERE account_code = ?
        ''', (disabled, account_code))
        self.conn.commit()

    @locked
    def get_user_id(self, account_code):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id FROM accounts WHERE account_code = ?
        ''', (account_code,))
        result = cursor.fetchone()
        if result is None:
            return None
        return result[0]

    @locked
    def get_account_info(self, account_code):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, isjp, originalcode, disabled FROM accounts WHERE account_code = ?
        ''', (account_code,))
        result = cursor.fetchone()
        if result is None:
            return None
        return result

    @locked
    def count_accounts(self, user_id):
        user_accounts = bca_db.get_user_accounts(user_id)
        c = 0
        for a in user_accounts:
            if a[-1] == 0:
                c += 1
        return c

    @locked
    def get_user_accounts(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT account_code, isjp, originalcode, disabled FROM accounts WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchall()
        return result

    @locked
    def close(self):
        self.conn.close()


bca_db = BCAccountDB()


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
        self.conn.commit()

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
        return localuser_db.get_info_by_lid(local_user_id)

    @locked
    def get_info_by_lid(self, local_user_id):
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
        self.update_info_by_lid(local_user_id, new_info)

    @locked
    @connected
    def update_info_by_lid(self, local_user_id, new_info):
        self.conn.execute('''
            UPDATE localusers SET info = ? WHERE local_user_id = ?
        ''', (str(new_info), local_user_id))
        self.conn.commit()

    @locked
    @connected
    def delete_user(self, local_uid):
        self.conn.execute('''
            DELETE FROM localusers WHERE local_user_id = ?
        ''', (local_uid,))
        self.conn.commit()

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
                pool_src = copy.deepcopy(local_server.get_default_values()['default_user'])
            value = pool_src[key]
        return value

    def set_value(self, context, key, value):
        info = self.get_info(context)
        info[key] = value
        if local_server.get_default_values()['default_user'][key] == value:
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

    @return_false_on_error
    def set_preset(self, context, preset_id, preset_str):
        if preset_id == "last_cart":
            self.set_value(context, preset_id, preset_str)
        else:
            presets = self.get_bot_values(context)['presets']
            if preset_id in presets:
                presets[preset_id] = preset_str
                self.set_value(context, 'presets', presets)
            else:
                return False

    @staticmethod
    def check_stackable(item_info):
        stackable = False
        if isinstance(item_info[-1], dict):
            stackable = item_info[-1].get('stackable', False)
        return stackable

    @return_false_on_error
    def add_to_cart(self, context, item, amount, ignore_max=False):
        user_bot_values = self.get_bot_values(context)
        cart_size = self.get_cart_size(context)
        cart_max_size = self.get_value(context, 'cart_size', src=user_bot_values['default_user'])
        cart = self.get_value(context, 'cart')
        item_info = user_bot_values['items'][item]
        if cart_size >= cart_max_size:
            if not ignore_max:
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
    def mass_add_to_cart(self, context, queries, ignore_max=False):
        user_bot_values = self.get_bot_values(context)
        cart_size = self.get_cart_size(context)
        cart_max_size = self.get_value(context, 'cart_size', src=user_bot_values['default_user'])
        cart = self.get_value(context, 'cart')

        added = 0
        for item_id, amount in queries:
            if cart_size >= cart_max_size:
                if not ignore_max:
                    break

            item_info = user_bot_values['items'][item_id]
            stackable = self.check_stackable(item_info)
            if not stackable:
                cart[item_id] = amount
            else:
                items_array = cart.get(item_id, [])
                items_array.append(amount)
                items_array = list(set(items_array))
                cart[item_id] = items_array

            cart_size += 1
            added += 1

        self.set_value(context, 'cart', cart)
        return added

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

    @return_false_on_error
    def add_uses(self, context):
        self.set_value(context, 'use_count', self.get_value(context, 'use_count') + 1)

    @return_false_on_error
    def get_uses(self, context):
        return self.get_value(context, 'use_count')

    def clear_cart(self, context):
        self.set_value(context, 'cart', {})

    def clear_boosts(self, context):
        self.set_value(context, 'active_boosts', [])

    @staticmethod
    def get_donate_boost_id(donate_amount, donate_server):
        msq = 0
        min_distance = float('inf')
        for k in donate_server:
            distance = donate_amount - k
            if distance < 0:
                continue
            if distance < min_distance:
                msq = k
                min_distance = distance
        if msq == 0:
            return None
        return donate_server[msq]

    def generate_shop(self, context, user_values):
        boosts = info_worker.get_value(context, 'boosts')
        boosts_store = local_server.get_default_values()['boosts_store']
        donate_rules = local_server.get_default_values()['donate_rules']

        # Определение цены на слот аккаунта
        slot_count = user_values['accounts_limit']

        price_account = 0
        if slot_count <= 5:
            mult = slot_count - 1
        else:
            mult = 4

        price_account += 50 * mult
        boosts_store['add_slot'] = price_account

        # Определение цены донатов
        current_level = 0
        for boost_id in boosts:
            if boost_id.startswith("donate"):
                current_level = boost_id.split("_")[1]
                current_level = int(current_level)
                break

        donate_available = []
        donate_boosts = {}
        for rule in donate_rules:
            price = rule
            boost_id = donate_rules[rule]
            donate_boosts[boost_id] = price

            donate_level = boost_id.split("_")[1]
            donate_level = int(donate_level)

            if donate_level > current_level:
                continue
            else:
                donate_available.append(boost_id)
        donate_available.sort(key=lambda x: int(x.split("_")[1]))

        for boost_id in donate_available:
            minus_price = 0
            if current_level:
                minus_price = donate_boosts[f"donate_{current_level}"]
            price = donate_boosts[boost_id]
            boosts_store[boost_id] = price - minus_price

        return boosts_store

    def get_bot_values(self, context):
        default_values = local_server.get_default_values()
        default_values = copy.deepcopy(default_values)
        boosts_ids = self.get_value(context, 'boosts')
        active_boosts = self.get_value(context, 'active_boosts')
        boosts_server = default_values['boosts']
        passive_boosts = []

        for bid in boosts_ids:
            boost = boosts_server[bid]
            active = False
            count = boosts_ids[bid]
            if boost['type'] == 'passive':
                active = True
            if 'stackable' in boost:
                if not boost['stackable']:
                    if bid in passive_boosts:
                        continue
            if active:
                for i in range(count):
                    passive_boosts.append(bid)
        passive_boosts.extend(active_boosts)

        for bid in passive_boosts:
            local_server.mod_values(default_values, bid)

        default_values["boosts_store"] = self.generate_shop(context, default_values["default_user"])

        categorized = local_server.categorize_items(default_values['items'])
        default_values['categorized'] = categorized
        return default_values

    def use_boost(self, context, boost_id):
        boosts = self.get_value(context, 'boosts')
        active_boosts = self.get_value(context, 'active_boosts')
        amount = boosts[boost_id]
        if amount > 0:
            if boost_id in active_boosts:
                return False
            boosts[boost_id] -= 1
            active_boosts.append(boost_id)
            self.set_value(context, 'boosts', boosts)
            self.set_value(context, 'active_boosts', active_boosts)
            return True
        return False

    def add_donate(self, context, amount):
        donate = self.get_value(context, 'donate')
        donate += amount
        if donate < 0:
            return False
        self.set_value(context, 'donate', donate)
        return True


info_worker = DBInfoWorker()
