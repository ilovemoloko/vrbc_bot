import os.path
import numpy
import requests
from io import BytesIO
from PIL import Image, ImageEnhance
import pytesseract
import re
import struct

import db_worker
import local_server
from fuzzywuzzy import process
from unidecode import unidecode
from translate import Translator
from db_worker import bca_db, info_worker, fsm_db, localuser_db
from script_base import MessageContext, MessageBuilder, ButtonsBuilder
import sys
import logging
import threading

tesPath = "D:/Tesseract/tesseract.exe"
if "yy986" in os.path.abspath(__file__):
    tesPath = "C:/Program Files/Tesseract-OCR/tesseract.exe"
if not (sys.platform == "linux" or sys.platform == "linux2"):
    pytesseract.pytesseract.tesseract_cmd = tesPath
else:
    print("Running on Linux")
custom_config = r'-c tessedit_char_whitelist=" :abcdefABCDEFTransferCodeConfirmation0123456789€¢Oo"'

lock = threading.RLock()
mass_msg_cache = {}
hack_locked = "lock" in sys.argv


def locked(func):
    def wrapper(*args, **kwargs):
        with lock:
            return func(*args, **kwargs)

    return wrapper


@locked
def add_mass_msg(context: MessageContext, msg: MessageBuilder):
    global mass_msg_cache
    mass_msg_cache[f"{context.src}_{context.user_id}"] = msg


@locked
def mass_msg(text=None):
    global mass_msg_cache
    users = list(mass_msg_cache.values())
    if text is None:
        text = "Снято ограничение на взлом. Попробуйте использовать бота"
    for msg in users:
        msg: MessageBuilder
        msg.setText(text)
        msg.setButtons(ButtonsBuilder().add("Перейти в корзину", "viewcart"))
        msg.reply()
    mass_msg_cache = {}


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
    res = pytesseract.image_to_string(image, config=custom_config).lower()
    return res


def extract_codes(input_string):
    input_string = input_string.replace("€", "e")
    input_string = input_string.replace("¢", "c")
    input_string = input_string.replace("o", "0")
    input_string = input_string.replace("s", "5")

    regex = r'([a-fA-F0-9]{9})[\s\S]*?([0-9]{4})'
    pattern = re.compile(regex)
    matches = re.findall(pattern, input_string)

    closest_match = min(matches, key=lambda x: input_string.find(x[1]) - input_string.find(x[0]))
    return closest_match


translator = None
try:
    translator = Translator(from_lang="ru", to_lang="en")
    translator.translate("тест")
except Exception as e:
    print("TRANSLATOR ERROR", e)
    translator = None


def get_translation(text):
    text = text.title()
    if translator is None:
        return unidecode(text)
    try:
        res = translator.translate(text[:100])
        return res
    except Exception as e:
        print("TRANSLATOR ERROR", e)
        return unidecode(text)


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


class DataSearcher:
    def __init__(self, data):
        self.sBytes = data
        self.Offsets = {}
        self.inq = "LOL"

    def getInq(self):
        inqIdx = 0
        try:
            inqIdx = self.search(struct.pack("<I", 9), 300000) + 4
        except:
            sBytes = self.sBytes
            str_from_bytes = sBytes.decode('utf-8', errors='ignore')

            lololo = re.findall(
                r"(?:^|[^a-zA-Z\d])[a-f0-9]{9}(?:[^a-zA-Z\d]|$)", str_from_bytes)
            if len(lololo) > 0:
                lololo = lololo[0]
                k = ''.join(
                    lol for lol in lololo if lol in 'abcdef0123456789')
                inqIdx = self.sBytes.index(k.encode())
            else:
                possibleinq = re.findall(
                    r'(?<![0-9a-f])[0-9a-fA-F]{11}(?![0-9a-fA-F]{2})', str(self.sBytes))
                probablyinq = list(filter(lambda t: str(t).startswith(
                    '00') and str(t).lower() == str(t), possibleinq))[0][2:11]
                inqIdx = self.sBytes.index(probablyinq.encode())

        InqBytes = bytearray([0, 0, 0, 0, 0, 0, 0, 0, 0])
        for i in range(9):
            InqBytes[i] = self.sBytes[inqIdx + i]

        self.inq = InqBytes.decode()
        if not ''.join(k for k in self.inq if k in 'abcdef0123456789'):
            sBytes = self.sBytes
            str_from_bytes = sBytes.decode('utf-8', errors='ignore')

            lololo = re.findall(
                r"(?:^|[^a-zA-Z\d])[a-f0-9]{9}(?:[^a-zA-Z\d]|$)", str_from_bytes)

            if len(lololo) > 0:
                lololo = lololo[0]
                k = ''.join(
                    lol for lol in lololo if lol in 'abcdef0123456789')
                inqIdx = self.sBytes.index(k.encode())
            else:
                possibleinq = re.findall(
                    r'(?<![0-9a-f])[0-9a-fA-F]{11}(?![0-9a-fA-F]{2})', str(self.sBytes))
                probablyinq = list(filter(lambda t: str(t).startswith(
                    '00') and str(t).lower() == str(t), possibleinq))[0][2:11]
                inqIdx = self.sBytes.index(probablyinq.encode())
            InqBytes = bytearray([0, 0, 0, 0, 0, 0, 0, 0, 0])
            for i in range(9):
                InqBytes[i] = self.sBytes[inqIdx + i]
            self.inq = InqBytes.decode()

        return self.inq

    def search(self, Pattern: list, startIndex: int):
        if startIndex > len(self.sBytes) or len(Pattern) > (len(self.sBytes) - startIndex):
            raise IndexError('Something went wrong')
        index = startIndex
        limit = len(self.sBytes) - len(Pattern)
        while index <= limit:
            j = len(Pattern) - 1
            while j >= 0 and Pattern[j] == self.sBytes[index + j]:
                j -= 1
            if j < 0:
                return index
            index += 1
        return -1


def getInq(data):
    try:
        ds = DataSearcher(data)
        inq = ds.getInq()
    except Exception as e:
        logging.error(e)
        inq = "LOL"
    return inq


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


def get_donate_url(user_id, amount, src):
    # return f"https://yoomoney.ru/quickpay/confirm?receiver=***REMOVED***&quickpay-form=shop&targets=a&sum={amount}&label={src}_{user_id}"
    return "[ссылки пока что нет]"


def to_latin(text):
    return unidecode(text).title()


latinized_cats = {}
latinized_cats_ja = {}


def get_latinized_cats(is_jp=False):
    global latinized_cats, latinized_cats_ja
    if local_server.updated_cats:
        latinized_cats = {to_latin(key): value for key, value in local_server.cats.items()}
        latinized_cats_ja = {to_latin(key): value for key, value in local_server.cats_ja.items()}
        local_server.updated_cats = False
    if is_jp:
        return latinized_cats_ja
    return latinized_cats


def fuzzy_search(query, data, threshold=70, limit=8):
    query_latin = to_latin(query)
    ql = query_latin
    if query_latin != query:
        query_latin = get_translation(query)

    keys = list(data.keys())
    results1 = process.extract(query_latin, keys, limit=limit)
    results2 = process.extract(ql, keys, limit=limit)

    results = results1 + results2
    results = list(set(results))
    results.sort(key=lambda x: x[1], reverse=True)
    results = results[:limit]

    best_matches = [result for result in results if result[1] >= threshold]
    return [(key, data[key]) for key, score in best_matches]


def search_cat(query, is_jp=False):
    data = get_latinized_cats(is_jp=is_jp)
    if query.isnumeric():
        res = []
        for key, value in data.items():
            if value == int(query):
                res.append((key, value))
        if len(res) == 0:
            res = fuzzy_search(query, data)
    else:
        res = fuzzy_search(query, data)

    return res


def add_account(context, user_id, account):
    inq, is_jp = account

    user_bot_values = info_worker.get_bot_values(context)['default_user']
    accounts_limit = info_worker.get_value(context, 'accounts_limit', src=user_bot_values)
    user_accounts_number = bca_db.count_accounts(user_id)

    bca_db.add_account(user_id, inq, is_jp, "")

    if user_accounts_number >= accounts_limit:
        bca_db.set_disabled(inq, 2)
        return False, "Вы достигли лимита аккаунтов"

    return "success", f"Аккаунт ({inq}) привязан к вашему профилю\n"


def merge_accounts(context: MessageContext, uid, uid_fin):
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

    if "is_admin" in info_fin:
        info_fin["is_admin"] = False

    localuser_db.update_info_by_lid(uid_fin, info_fin)
    localuser_db.delete_user(uid)
    fsm_db.set_local_user_id(context, uid_fin)

    return "retry", "Теперь этот профиль привязан к аккаунту, на котором вы ранее использовали бота."


def inq_checker(account, context: MessageContext):
    inq, is_jp = account
    user_id = fsm_db.get_local_user_id(context)
    accinfo = bca_db.get_account_info(inq)

    if accinfo is not None:
        a_user_id, a_isjp, a_originalcode, disabled = accinfo
        if disabled == 1:
            return False, ("Аккаунт отключен. Используйте его восстановленную версию.\n\n"
                           "У вас 2 варианта:\n"
                           "1) Зайти на восстановленный аккаунт, который вам выдавал бот\n"
                           "2) Восстановить аккаунт ещё раз (для этого напишите !восстановить)")
        elif disabled == 2:
            if a_user_id == user_id:
                user_bot_values = info_worker.get_bot_values(context)['default_user']
                accounts_limit = info_worker.get_value(context, 'accounts_limit', src=user_bot_values)
                user_accounts_number = bca_db.count_accounts(user_id)

                if accounts_limit - user_accounts_number > 0:
                    bca_db.set_disabled(inq, 0)
                    return True, f"Ваш аккаунт {inq} сохранён"
                else:
                    return False, "Вы достигли лимита аккаунтов"

            if len(bca_db.get_user_accounts(user_id)) != 0:
                return False, f"Вы не можете использовать аккаунт, принадлежащий другому пользователю"

            return merge_accounts(context, user_id, a_user_id)
        if a_user_id == user_id:
            return True, f"Ваш аккаунт {inq} сохранён"
        if len(bca_db.get_user_accounts(user_id)) != 0:
            return False, f"Вы не можете использовать аккаунт, принадлежащий другому пользователю"

        return merge_accounts(context, user_id, a_user_id)

    else:
        return add_account(context, user_id, account)


def recovery_rite(context: MessageContext, old_inq, new_inq):
    user_id = fsm_db.get_local_user_id(context)
    local_server.change_code(user_id, old_inq, new_inq)
    account = bca_db.get_account_info(old_inq)
    if account is None:
        return
    user_id, isjp, originalcode, disabled = account
    bca_db.add_account(user_id, new_inq, isjp, old_inq)
    bca_db.set_disabled(old_inq, True)


def exec_and_return(context, expression):
    exec("def __ex(context):" + ''.join('\n {0}'.format(l) for l in expression.split('\n')))
    return locals()["__ex"](context)


def sendmsg(src, user, content, buttons=None):
    bot_object = db_worker.bot_objects
    if src not in bot_object:
        return
    bot_object = bot_object[src]
    msg = MessageBuilder().setText(content).setPeerId(user).setButtons(buttons)
    bot_object.send_message(msg)
