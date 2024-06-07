import requests
from io import BytesIO
from PIL import Image
import pytesseract
import threading
import re

tesPath = "D:/Tesseract/tesseract.exe"
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
    lines = input_string.split('\n')

    hex_pattern = re.compile(r'\b[a-fA-F0-9]{9}\b')
    numeric_pattern = re.compile(r'\b\d{4}\b')

    hex_code = hex_pattern.findall(lines[0])[0]
    numeric_code = numeric_pattern.findall(lines[1])[0]

    return hex_code, numeric_code


def get_codes_box(photo_size):
    x, y = photo_size
    center_x, center_y = x / 2, y / 2
    x_crop_1 = center_x * 0.75
    x_crop_2 = center_x * 1.25
    y_crop_1 = center_y * 0.9
    y_crop_2 = center_y * 1.15

    return x_crop_1, y_crop_1, x_crop_2, y_crop_2


class SingletonMeta(type):
    _instances = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


def getFSMLevel(uid):
    print(uid)
    return "test 20"

