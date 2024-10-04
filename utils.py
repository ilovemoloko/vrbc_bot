import os.path
import numpy
import requests
from io import BytesIO
from PIL import Image, ImageEnhance
import pytesseract
import re
import struct
import local_server
from fuzzywuzzy import process
from unidecode import unidecode
from translate import Translator
from db_worker import bca_db, info_worker, fsm_db, localuser_db
from script_base import MessageContext
import sys

tesPath = "D:/Tesseract/tesseract.exe"
if "yy986" in os.path.abspath(__file__):
    tesPath = "C:/Program Files/Tesseract-OCR/tesseract.exe"
if not (sys.platform == "linux" or sys.platform == "linux2"):
    pytesseract.pytesseract.tesseract_cmd = tesPath
else:
    print("Running on Linux")
custom_config = r'-c tessedit_char_whitelist=" :abcdefTransferCodeConfirmation0123456789€¢"'


def get_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        return image
    else:
        raise Exception(f"Failed to retrieve image from URL. Status code: {response.status_code}")


def getText(image):
    image = image.convert('L')
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)
    res = pytesseract.image_to_string(image, config=custom_config)
    return res


def extract_codes(input_string):
    input_string = input_string.replace("€", "e")
    input_string = input_string.replace("¢", "c")
    regex = r'([a-fA-F0-9]{9})[\s\S]*([0-9]{4})'
    pattern = re.compile(regex)
    hex_code, numeric_code = re.findall(pattern, input_string)[0]
    return hex_code, numeric_code


translator = None
try:
    translator = Translator(from_lang="ru", to_lang="en")
    translator.translate("тест")
except Exception as e:
    print("TRANSLATOR ERROR", e)
    translator = None


def get_translation(text):
    if translator is None:
        return unidecode(text)
    try:
        return translator.translate(text[:100])
    except Exception as e:
        print("TRANSLATOR ERROR", e)
        return unidecode(text)


def send_ds_message(channel_id, text):
    the_bot_token = local_server.discord_config()['token']
    json = {
        "content": text
    }
    headers = {
        "authorization": f"Bot {the_bot_token}",
        "Content-Type": "application/json"
    }
    return requests.post(f"https://discord.com/api/v10/channels/{channel_id}/messages", headers=headers, json=json)


def create_ds_channel(user, platform):
    discord_config = local_server.discord_config()
    the_bot_token = discord_config['token']
    discord_api = discord_config['api_base']
    guild_id = discord_config['guild_id']
    json = {"name": user,
            "permission_overwrites": [],
            "type": 0,
            "topic": f'{user} {platform}'
            }
    headers = {
        "authorization": f"Bot {the_bot_token}",
        "Content-Type": "application/json"
    }
    # я кстати не проверял его работоспособность. если что затролен
    req = requests.post(f"{discord_api}/guilds/{guild_id}/channels", json=json, headers=headers)
    return req


def randhex(len):
    return numpy.random.bytes(len).hex()


def getSave(t, c, ver='en'):  # Возвращает (инфо, успешно ли, версия)
    url = f"https://nyanko-save.ponosgames.com/v1/transfers/{t}/reception"
    jsonStr = "{\"clientInfo\":{\"client\":{\"countryCode\":\"" + ver + "\",\"version\":\"" + '120300' + "\"},\"device\":{\"model\":\"ASUS_Z01QD\"},\"os\":{\"type\":\"android\",\"version\":\"5.1.1\"}},\"nonce\":\"" + randhex(
        16) + "\",\"pin\":\"" + c + "\"}"
    byt = jsonStr.encode('utf-8')
    r = requests.post(url, headers={'Content-type': 'application/json'}, data=byt, stream=True)
    if r.status_code == 200 and len(r.content) > 400:
        return r.content, True, ver
    else:
        if ver == 'en':
            return getSave(t, c, 'ja')
        return "КОДГОВНО!aaabbbccc!АВТОРГЕНИЙ".encode("utf-8"), False, ver


def search(data, Pattern, startIndex):
    if startIndex > len(data) or len(Pattern) > (len(data) - startIndex):
        return -100
    index = startIndex
    limit = len(data) - len(Pattern)
    while index <= limit:
        j = len(Pattern) - 1
        while j >= 0 and Pattern[j] == data[index + j]:
            j -= 1
        if j < 0:
            return index
        index += 1
    return -100


def getInq(data):
    data = bytearray(data)
    try:
        CurrIdx = search(data, struct.pack("<I", 9), 300000) + 4
        if CurrIdx > 0:
            InqBytes = bytearray([0, 0, 0, 0, 0, 0, 0, 0, 0])
            for i in range(9):
                InqBytes[i] = data[CurrIdx + i]
            inq = ''.join(k for k in InqBytes.decode() if k in 'abcdef0123456789')
            if len(inq) == 9: return inq
        inq_pat = re.findall(r"(?:^|[^a-zA-Z\d])[a-f0-9]{9}(?:[^a-zA-Z\d]|$)", str(data))
        lololo = inq_pat[0]
        inq = ''.join(lol for lol in lololo if lol in 'abcdef0123456789')
        return inq

    except:
        return "LOL"


def humanize_time(seconds):
    if seconds == 0:
        return "0 сек."
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    result = ""
    if days > 0:
        result += f"{days} дн. "
    if hours > 0:
        result += f"{hours} ч. "
    if minutes > 0:
        result += f"{minutes} мин. "
    if seconds > 0:
        result += f"{seconds} сек. "
    return result


def get_donate_url(user_id, amount):
    return f"[ссылка]"


def to_latin(text):
    return unidecode(text)


latinized_cats = {}


def get_latinized_cats():
    global latinized_cats
    if local_server.updated_cats:
        latinized_cats = {to_latin(key): value for key, value in local_server.cats.items()}
        local_server.updated_cats = False
    return latinized_cats


def fuzzy_search(query, data, threshold=70, limit=1):
    query_latin = to_latin(query)
    if query_latin != query:
        query_latin = get_translation(query)
    keys = list(data.keys())
    results = process.extract(query_latin, keys, limit=limit)
    best_matches = [result for result in results if result[1] >= threshold]
    return [(key, data[key]) for key, score in best_matches]


def search_cat(query):
    return fuzzy_search(query, get_latinized_cats())


def add_account(context, user_id, account):
    inq, is_jp = account

    user_bot_values = info_worker.get_bot_values(context)['default_user']
    accounts_limit = info_worker.get_value(context, 'accounts_limit', src=user_bot_values)
    user_accounts_number = bca_db.count_accounts(user_id)

    if user_accounts_number >= accounts_limit:
        return False, "Вы достигли лимита аккаунтов"

    bca_db.add_account(user_id, inq, is_jp, "")

    return "success", f"Аккаунт ({inq}) привязан к вашему профилю ({user_accounts_number + 1} из {accounts_limit} аккаунтов)\n"


def merge_accounts(context: MessageContext, uid, uid_fin):
    # src = context.src
    # fin_userids = fsm_db.get_all_by_local_user_id(uid_fin)
    # for fin_userid in fin_userids:
    #     if fin_userid[0].startswith(src):
    #         return False, "Вы не можете использовать аккаунт, принадлежащий другому пользователю"

    info_fin = eval(localuser_db.get_info_by_lid(uid_fin))
    info = eval(localuser_db.get_info_by_lid(uid))

    if "cart" in info:
        info_fin["cart"] = info["cart"]

    if "donate" in info:
        if "donate" not in info_fin:
            info_fin["donate"] = 0
        info_fin["donate"] += info["donate"]

    if "use_count" in info:
        if "use_count" not in info_fin:
            info_fin["use_count"] = 0
        info_fin["use_count"] += info["use_count"]

    if "boosts" in info:
        if "boosts" not in info_fin:
            info_fin["boosts"] = {}
        for boost in info["boosts"]:
            if boost not in info_fin["boosts"]:
                info_fin["boost"][boost] = info["boosts"][boost]
            else:
                info_fin["boosts"][boost] += info["boosts"][boost]

    if "active_boosts" in info:
        if "active_boosts" not in info_fin:
            info_fin["active_boosts"] = []

        info_fin["active_boosts"].extend(info["active_boosts"])

    if "is_admin" in info:
        info_fin["is_admin"] = False

    localuser_db.update_info_by_lid(uid_fin, info_fin)
    fsm_db.set_local_user_id(context, uid_fin)

    return "retry", "Теперь этот профиль привязан к аккаунту, на котором вы ранее использовали бота."


def inq_checker(account, context: MessageContext):
    inq, is_jp = account
    user_id = fsm_db.get_local_user_id(context)

    accinfo = bca_db.get_account_info(inq)
    if accinfo is not None:
        a_user_id, a_isjp, a_originalcode, disabled = accinfo
        if disabled:
            return False, "Аккаунт отключен. Используйте его восстановленную версию."
        if a_user_id == user_id:
            return True, f"Ваш аккаунт {inq} сохранён"
        if len(bca_db.get_user_accounts(user_id)) != 0:
            return False, f"Вы не можете использовать аккаунт, принадлежащий другому пользователю"

        return merge_accounts(context, user_id, a_user_id)

    else:
        return add_account(context, user_id, account)


def recovery_rite(context: MessageContext, old_inq, new_inq):
    account = bca_db.get_account_info(old_inq)
    if account is None:
        return
    user_id, isjp, originalcode, disabled = account
    bca_db.add_account(user_id, new_inq, isjp, old_inq)
    bca_db.set_disabled(old_inq, True)
    local_server.change_code(user_id, old_inq, new_inq)


def exec_and_return(context, expression):
    exec("def __ex(context):" + ''.join('\n {0}'.format(l) for l in expression.split('\n')))
    return locals()["__ex"](context)
