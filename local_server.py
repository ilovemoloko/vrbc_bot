import requests
import json

base_url = "http://127.0.0.1:5000"
api_url = base_url + "/api/hack"
wait_time_url = base_url + "/api/wait"
unban_url = base_url + "/api/ub"
list_backups_url = base_url + "/api/list_backups"
backup_account_url = base_url + "/api/backup_account"
change_code_url = base_url + "/api/change_code"
get_variables_url = base_url + "/api/get_variables"
get_cats_url = base_url + "/api/get_cats"
get_queue_url = base_url + "/api/get_queue"


bot_variables = {}

cats = {}
cats_ja = {}
cats_names = {}
cats_names_ja = {}
cats_icons = {}
cats_icons_ja = {}


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
    if values['default_user']['cooldown'] < 0:
        values['default_user']['cooldown'] = 0

    return values


def boost_change_cart_size(values, effect):
    size = effect['params'][0]
    values['default_user']['cart_size'] += size
    return values


def boost_add_value(values, effect):
    value, value_inc = effect['params']
    values['default_user'][value] += value_inc
    return values


boost_functions = {"change_limit": boost_change_limit,
                   "add_item": boost_add_item,
                   "change_catalog_limit": boost_change_catalog_limit,
                   "change_cooldown": boost_change_cooldown,
                   "change_cart_size": boost_change_cart_size,
                   "add_value": boost_add_value}


def mod_values(values, boost_id):
    boost = bot_variables['boosts'][boost_id]
    for effect in boost['effects']:
        boost_functions[effect['type']](values, effect)
    return values


def get_default_values():
    return bot_variables


def get_user_backups(user_id, vk_id = -1):
    retval = requests.get(list_backups_url, params={"user_id": user_id, "vk_id": vk_id}).content.decode("utf-8")
    json_data = json.loads(retval)
    if json_data['status'] == 0:
        return ["Ошибка сервера бота", "Попробуйте позже"]
    res = json_data['backups']
    res.sort()
    return res


def recovery_backup(user_id, inq):
    retval = requests.get(unban_url, params={"user_id": user_id, "inq": inq}).content.decode("utf-8")
    json_data = json.loads(retval)

    status = json_data['status']
    msg = json_data['msg']

    new_inq = json_data.get('new_inq', "")
    tc = json_data.get('tc', "")
    cc = json_data.get('cc', "")
    ver = json_data.get('ver', "")

    return status, new_inq, msg, tc, cc, ver


def backup_account(user_id, inq, data):
    r = requests.post(backup_account_url, params={"user_id": user_id, "inq": inq}, files=data)
    resp = json.loads(r.content.decode("utf-8"))
    status = resp.get("status")
    msg = resp.get("msg")
    return status, msg


def change_code(user_id, inq, new_inq):
    return requests.get(change_code_url, params={"user_id": user_id, "inq": inq, "new_inq": new_inq}).content.decode("utf-8")


def get_wait_time():
    return requests.get(wait_time_url).content.decode("utf-8")


def hack_account(files, headers):
    res = requests.post(api_url, files=files, headers=headers)
    return json.loads(res.content.decode("utf-8"))


def get_queue():
    res = requests.get(get_queue_url).content.decode("utf-8")
    return json.loads(res)


updated_cats = False

max_cat_en = 0
max_cat_ja = 0


def update_variables():
    global bot_variables, cats, cats_names, updated_cats, cats_icons, cats_names_ja, cats_icons_ja, cats_ja, max_cat_en, max_cat_ja
    r = requests.get(get_variables_url)
    bot_variables = r.json()

    int_keys = ['items', 'donate_rules', 'categories']

    for key in int_keys:
        items = list(bot_variables[key].items())
        for item in items:
            bot_variables[key][int(item[0])] = item[1]
            bot_variables[key].pop(item[0])

    r = requests.get(get_cats_url)
    cats_vars = r.json()

    cats = cats_vars['all_forms']
    cats_names = cats_vars['cat_names']
    cats_icons = cats_vars['icons']

    cats_ja = cats_vars['cats_ja']['all_forms']
    cats_names_ja = cats_vars['cats_ja']['cat_names']
    cats_icons_ja = cats_vars['icons_ja']

    for cat_icon_id in cats_icons:
        if int(cat_icon_id) > max_cat_en:
            max_cat_en = int(cat_icon_id)

    for cat_icon_id in cats_icons_ja:
        if int(cat_icon_id) > max_cat_ja:
            max_cat_ja = int(cat_icon_id)

    updated_cats = True

    return True


update_variables()


def get_cats_names(is_jp=False):
    if is_jp:
        return cats_names_ja
    return cats_names


def get_icons(is_jp=False):
    if is_jp:
        return cats_icons_ja
    return cats_icons
