import os


def _env_int(name, default=0):
    value = os.environ.get(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


is_AVTOMOIKA = 0

if is_AVTOMOIKA:
    token_vk = os.environ.get("VK_TOKEN_AVTOMOIKA", "")
    id_vk = _env_int("VK_GROUP_ID_AVTOMOIKA")

    token_tg = os.environ.get("TG_TOKEN_AVTOMOIKA", "")

    mod_channel = _env_int("MOD_CHANNEL_AVTOMOIKA")
else:
    token_vk = os.environ.get("VK_TOKEN", "")
    id_vk = _env_int("VK_GROUP_ID")

    token_tg = os.environ.get("TG_TOKEN", "")

    mod_channel = _env_int("MOD_CHANNEL")

min_version = 130600

ADMIN_VK_ID = _env_int("ADMIN_VK_ID")

start_vk = True
start_tg = True
start_massmsg = True
start_public_server = True
start_mainprocess = True
start_modbot = True

initialize_server_data = True


localserver_url = os.environ.get("LOCALSERVER_URL", "http://127.0.0.1:5000")

PAY_API_URL = os.environ.get("PAY_API_URL", "")
PAY_API_TOKEN = os.environ.get("PAY_API_TOKEN", "")

DONATE_PHONE = os.environ.get("DONATE_PHONE", "")
DONATE_CARD = os.environ.get("DONATE_CARD", "")

GAME_API_URL = os.environ.get("GAME_API_URL", "https://nyanko-save.ponosgames.com")

PUBLIC_SERVER_HOST = os.environ.get("PUBLIC_SERVER_HOST", "0.0.0.0")
PUBLIC_SERVER_PORT = _env_int("PUBLIC_SERVER_PORT", 8000)
PUBLIC_SERVER_URL = os.environ.get("PUBLIC_SERVER_URL", "http://localhost:8000")

DB_PATH = os.environ.get("DB_PATH", "db/userdata.db")
BOT_WORKDIR = os.environ.get("BOT_WORKDIR", ".")

PROXY = os.environ.get("PROXY", "")
