items = {
    1: [35000, "CatFood", 1],
    2: [99999999, "XP", 1],
    3: [200, "Серебряные билеты", 1],
    4: [100, "Золотые билеты", 1],
    5: [8, "Платиновые билеты", 1],
    6: [200, "Ускорение", 2],
    7: [100, "Treasure Radar", 2],
    8: [200, "Rich Cat", 2],
    9: [100, "Cat CPU", 2],
    10: [200, "Cat Jobs", 2],
    11: [200, "Sniper Cat", 2],
    12: [20, "Фиолетовое семечко", 3],
    13: [20, "Красное семечко", 3],
    14: [20, "Синее семечко", 3],
    15: [20, "Зеленое семечко", 3],
    16: [20, "Желтое семечко", 3],
    17: [20, "Золотой фрукт", 3],
    18: [20, "Красный фрукт", 3],
    19: [20, "Синий фрукт", 3],
    20: [20, "Зеленый фрукт", 3],
    21: [20, "Желтый фрукт", 3],
    22: [20, "Эпический фрукт", 3],
    23: [20, "Elder семечко", 3],
    24: [20, "Elder фрукт", 3],
    25: [20, "Эпическое семечко", 3],
    26: [20, "Фиолетовый фрукт", 3],
    27: ["Нет", "Кот", 6, {"stackable": True}],
    28: [4000, "NP", 6],
    29: [150, "Special Кошачьи Глаза", 5],
    30: [150, "Rare Кошачьи Глаза", 5],
    31: [150, "Super Rare Кошачьи Глаза", 5],
    32: [150, "Uber Rare Кошачьи Глаза", 5],
    33: [70, "Legend Rare Кошачьи Глаза", 5],
    34: [500, "Флажки для перезарядки энергии", 6],
    35: [10, "Помощники Гаматото", 4],
    36: [20, "Aku Семечки", 3],
    37: [20, "Aku Фрукт", 3],
    38: [200, "Кирпичи", 4],
    39: [200, "Перья", 4],
    40: [200, "Уголь", 4],
    41: [200, "Шестеренки", 4],
    42: [200, "Золото", 4],
    43: [200, "Метеорит", 4],
    44: [200, "Кости", 4],
    45: [200, "Аммонит", 4],
    46: [4, "Легендарные билеты", 1],
    50: [20, "Фиолетовые Behemoth Stones", 3],
    51: [20, "Красные Behemoth Stones", 3],
    52: [20, "Синие Behemoth Stones", 3],
    53: [20, "Зеленые Behemoth Stones", 3],
    54: [20, "Радужные Behemoth Stones", 3],
    55: [20, "Фиолетовые Behemoth Crystals", 3],
    56: [20, "Красные Behemoth Crystals", 3],
    57: [20, "Синие Behemoth Crystals", 3],
    58: [20, "Зеленые Behemoth Crystals", 3],
    59: [20, "Желтые Behemoth Crystals", 3],
    60: [70, "Dark Кошачьи Глаза", 5],
    61: [200, "Кирпичи Z", 4],
    62: [200, "Перья Z", 4],
    63: [200, "Уголь Z", 4],
    64: [200, "Шестеренки Z", 4],
    65: [200, "Золото Z", 4],
    66: [200, "Метеорит Z", 4],
    67: [200, "Кости Z", 4],
    68: [200, "Аммонит Z", 4],
    69: [20, "Желтые Behemoth Stones", 3],
    70: [10, "Золотое семечко", 3],
}

categories = {
    1: "Валюты",
    2: "Боевые бонусы",
    3: "Фрукты и Behemoth Stones/Crystals",
    4: "Материалы Отото и помощники Гаматото",
    5: "Кошачьи Глаза",
    6: "Коты, флажки и NP"
}

default_user = {
    "cart": {},
    "last_use": 0,
    "cart_size": 7,
    "cooldown": 30*60*60,
    "donate": 170,
    "boosts": {"test_boost2": 2},
    "active_boosts": []
}

boosts = {
    "test_boost": {
        "name": "Тестовый буст",
        "desc": """Снимает 5 секунд задержки
Добавляет 2 слота в корзину
Добавляет в каталог 6 русскийбот (Лимит 2, айди 100)
Добавляет к лимиту предмета 1 ещё 5000 единиц
Добавляет к лимиту второго каталога ещё 100 единиц""",
        "type": "passive",
        "effects": [
            {"type": "change_cooldown", "params": [-5]},
            {"type": "change_cart_size", "params": [2]},
            {"type": "add_item", "params": [100, [2, "русскийбот", 6]]},
            {"type": "change_limit", "params": [1, 5000]},
            {"type": "change_catalog_limit", "params": [2, 100]}
        ]
    },
    "skip_cooldown": {
        "name": "Пропуск задержки",
        "desc": "Мгновенно снимает 30 часов задержки",
        "type": "usable",
        "effects": [
            {"type": "change_cooldown", "params": [-30*60*60]}
        ]
    },
    "test_boost2": {
        "name": "Тестовый буст 2",
        "desc": "Тестовый буст 2",
        "type": "usable",
        "effects": [
            {"type": "change_cart_size", "params": [4]},
        ]
    },
    "test_boost3": {
        "name": "Тестовый буст 3",
        "desc": "Тестовый буст 2",
        "type": "usable",
        "effects": [
            {"type": "change_cart_size", "params": [6]},
        ]
    },
    "donate_1": {
        "name": "Donate1",
        "desc": "Donate1",
        "type": "passive",
        "effects": [
            {"type": "change_cooldown", "params": [-3 * 60 * 60]},
            {"type": "change_cart_size", "params": [1]},
        ]
    },
    "donate_2": {
        "name": "Donate2",
        "desc": "Donate2",
        "type": "passive",
        "effects": [
            {"type": "change_cooldown", "params": [-7 * 60 * 60]},
            {"type": "change_cart_size", "params": [3]},
        ]
    },
    "donate_3": {
        "name": "Donate3",
        "desc": "Donate3",
        "type": "passive",
        "effects": [
            {"type": "change_cooldown", "params": [-11 * 60 * 60]},
            {"type": "change_cart_size", "params": [5]},
        ]
    },
    "donate_4": {
        "name": "Donate4",
        "desc": "Donate4",
        "type": "passive",
        "effects": [
            {"type": "change_cooldown", "params": [-13 * 60 * 60]},
            {"type": "change_cart_size", "params": [7]},
        ]
    },
    "donate_5": {
        "name": "Donate5",
        "desc": "Donate5",
        "type": "passive",
        "effects": [
            {"type": "change_cooldown", "params": [-21 * 60 * 60]},
            {"type": "change_cart_size", "params": [10]},
        ]
    }
}

donate_rules = {
    35: "donate_1",
    75: "donate_2",
    125: "donate_3",
    175: "donate_4",
    250: "donate_5"
}

boosts_store = {
    "skip_cooldown": 50
}


def categorize_items(items):
    res = {}
    for iid in items:
        cat = items[iid][2]
        if cat not in res:
            res[cat] = {}
        res[cat][iid] = items[iid]
    return res


def boost_change_limit(values, effect):
    item_id, add_limit = effect['params']
    values['items'][item_id][0] += add_limit
    return values


def boost_add_item(values, effect):
    item_id, params = effect['params']
    values['items'][item_id] = params
    return values


def boost_change_catalog_limit(values, effect):
    catalog_id, add_limit = effect['params']
    category_items = categorize_items(values['items'])[catalog_id]
    for iid in category_items:
        values['items'][iid][0] += add_limit

    return values


def boost_change_cooldown(values, effect):
    time = effect['params'][0]
    values['default_user']['cooldown'] += time
    return values


def boost_change_cart_size(values, effect):
    size = effect['params'][0]
    values['default_user']['cart_size'] += size
    return values


boost_functions = {"change_limit": boost_change_limit,
                   "add_item": boost_add_item,
                   "change_catalog_limit": boost_change_catalog_limit,
                   "change_cooldown": boost_change_cooldown,
                   "change_cart_size": boost_change_cart_size}


def mod_values(values, boost_id):
    boost = boosts[boost_id]
    for effect in boost['effects']:
        boost_functions[effect['type']](values, effect)
    return values


def get_default_values():
    return {"categories": categories,
            "items": items,
            "default_user": default_user,
            "boosts": boosts,
            "donate_rules": donate_rules,
            "boosts_store": boosts_store}


def discord_config():
    # я сука этот токен печатал вручную с пк потому что не хочу 100 раз обновлять
    return {"token": "***REMOVED***",
            "guild_id": "670612631849009162",
            "api_base": "https://discord.com/api/v10"}