import requests
from io import BytesIO
from PIL import Image
import pytesseract
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

def getFSMLevel(uid):
    return "*"

