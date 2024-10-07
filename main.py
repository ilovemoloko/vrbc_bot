from tg_script import TgBotScript
from vk_script import VkBotScript
import threading
import logging
import time

logging.basicConfig(filename='app.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def thread(func):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()
    return wrapper


script_vk = VkBotScript()
script_tg = TgBotScript()


@thread
def vk_bot_start():
    while True:
        try:
            script_vk.start()
        except:
            time.sleep(60)
            print("vk polling...")


@thread
def tg_bot_start():
    script_tg.start()


vk_bot_start()
tg_bot_start()
