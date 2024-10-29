from tg_script import TgBotScript
from vk_script import VkBotScript
import threading
import logging
import time
import techsup
import config
# import public_server

logging.basicConfig(filename='app.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def thread(func):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()

    return wrapper


script_vk = VkBotScript()
script_tg = TgBotScript()
modbot = techsup.Modbot()
modbot.config(script_tg.bot, config.mod_channel)


@script_tg.bot.callback_query_handler(func=lambda call: call.message.chat.id == config.mod_channel)
def callback_query(call):
    modbot.handle_reply(call)


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
# public_server.start()
