import utils
from tg_script import TgBotScript
from vk_script import VkBotScript
import threading
import logging
import time
import techsup
import config
import public_server
import traceback

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


if config.start_modbot:
    @script_tg.bot.callback_query_handler(func=lambda call: call.message.chat.id == config.mod_channel)
    def callback_query(call):
        modbot.handle_reply(call)


@thread
def vk_bot_start():
    while True:
        try:
            script_vk.start()
        except Exception as e:
            print("VK FAILED", e)
            traceback.print_exc()
            time.sleep(1)


@thread
def tg_bot_start():
    script_tg.start()


if config.start_vk:
    vk_bot_start()
if config.start_tg:
    tg_bot_start()
if config.start_public_server:
    public_server.start()
if config.start_mainprocess:
    utils.main_process_task_handler()
