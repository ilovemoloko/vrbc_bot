from tg_script import TgBotScript
from vk_script import VkBotScript
import threading


def thread(func):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()

    return wrapper


script_vk = VkBotScript()
script_tg = TgBotScript()


@thread
def vk_bot_start():
    script_vk.start()


@thread
def tg_bot_start():
    script_tg.start()


vk_bot_start()
tg_bot_start()
