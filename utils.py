import os.path
import numpy
import requests
from io import BytesIO
from PIL import Image
import pytesseract
import threading
import re
import struct
import local_server


# код хуйня
class SingletonMeta(type):
    _instances = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


tesPath = "D:/Tesseract/tesseract.exe"
if "yy986" in os.path.abspath(__file__):
    tesPath = "C:/Program Files/Tesseract-OCR/tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = tesPath


def get_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        return image
    else:
        raise Exception(f"Failed to retrieve image from URL. Status code: {response.status_code}")


def getText(image):
    return pytesseract.image_to_string(image)


def extract_codes(input_string):
    regex = r'([a-fA-F0-9]{9})[\s\S]*([0-9]{4})'
    pattern = re.compile(regex)

    hex_code, numeric_code = re.findall(pattern, input_string)[0]

    return hex_code, numeric_code


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

def get_codes_box(photo_size):
    x, y = photo_size
    center_x, center_y = x / 2, y / 2
    x_crop_1 = center_x * 0.75
    x_crop_2 = center_x * 1.25
    y_crop_1 = center_y * 0.9
    y_crop_2 = center_y * 1.15

    return x_crop_1, y_crop_1, x_crop_2, y_crop_2


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
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    result = ""
    if days > 0:
        result += f"{days} дн."
    if hours > 0:
        result += f"{hours} ч."
    if minutes > 0:
        result += f"{minutes} мин."
    if seconds > 0:
        result += f"{seconds} сек."
    return result


def get_donate_url(user_id, amount):
    return f"[ссылка]"
