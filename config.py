import os

is_AVTOMOIKA = 0

if is_AVTOMOIKA:
    token_vk = os.environ.get("VK_TOKEN_AVTOMOIKA", "")
    id_vk = ***REMOVED***

    token_tg = os.environ.get("TG_TOKEN_AVTOMOIKA", "")

    mod_channel = -***REMOVED***
else:
    token_vk = os.environ.get("VK_TOKEN", "")
    id_vk = ***REMOVED***

    token_tg = os.environ.get("TG_TOKEN", "")

    mod_channel = -***REMOVED***

min_version = 130600

start_vk = True
start_tg = True
start_massmsg = True
start_public_server = True
start_mainprocess = True
start_modbot = True

initialize_server_data = True


localserver_url = "http://127.0.0.1:5000"

PAY_API_URL = "http://pay.***REMOVED***:8080/payments/link"
PAY_API_TOKEN = os.environ.get("PAY_API_TOKEN", "")

DONATE_PHONE = os.environ.get("DONATE_PHONE", "")
DONATE_CARD = os.environ.get("DONATE_CARD", "")

PROXY = os.environ.get("PROXY", "")
