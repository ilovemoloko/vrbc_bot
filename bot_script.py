import re
import time
import threading
import local_server
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
import utils
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, bca_db, SingletonMeta

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
commands = []
debug = False


class Bot(metaclass=SingletonMeta):
    def __init__(self, commands):
        self.commands = commands

    def command(self, pattern, level="*", weak=False, ignore_case=False, replace_newline=" ", dont_wait=False):
        def decorator(func):
            self.commands.append((level, pattern, func, weak, ignore_case, replace_newline))

            def wrapper(*args, **kwargs):
                if not dont_wait:
                    th_name = f"botcmd"
                    threading.current_thread().name = th_name
                return func(*args, **kwargs)
            return wrapper
        return decorator


bot = Bot(commands)

import vrbc_commands


def level_on_error(level):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                fsm_db.update_state(args[0], level)
                raise e

        return wrapper

    return decorator


def check_admin(context: MessageContext):
    is_admin = info_worker.get_value(context, 'is_admin')
    if not is_admin:
        if not (context.user_id == ***REMOVED*** and context.src == "vk"):
            return False
    return True


def generate_cart_str(cart_dict):
    cart_str = ""
    for item_id in cart_dict:
        amount = cart_dict[item_id]
        if isinstance(amount, list):
            for i in amount:
                cart_str += f"{item_id} {i}\n"
        else:
            cart_str += f"{item_id} {amount}\n"

    return cart_str


def reg(context: MessageContext):
    local_user_id = fsm_db.get_local_user_id(context)
    if local_user_id is None:
        local_user_id = local_user_db.create_user()
        fsm_db.set_local_user_id(context, local_user_id)


def addBoost(message: MessageBuilder, boost, boost_id, amount=None, desc=False):
    boost_name = boost['name']
    boost_desc = boost['desc']

    message.addText(f"{boost_name} (ID: {boost_id})", start="")
    if desc:
        message.addText(f"Описание: {boost_desc}")
    if amount is not None:
        message.addText(f"Осталось использований: {amount}")


@bot.command(".*", level="first_msg")
def start_message(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Увидеть каталог предметов", "cart").add("Меню функций", "menu")
    MessageBuilder().setReplyMode(context).setText(
        f"Здравствуй! В этом боте ты можешь получить различные предметы в игре The Battle Cats бесплатно.\n"
        f"Ты всегда можешь вернуться к этому сообщению, написав Начать\n\n"
        f"Если вам нужна помощь/техническая поддержка, то нажмите кнопку Меню").setButtons(buttons).reply()
    reg(context)
    fsm_db.update_state(context, "*")


@bot.command("начать", ignore_case=True)
def start_message_2(context: MessageContext):
    start_message(context)


@bot.command(r"find .*")
def find_cat(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    query = context.text.split(" ", 1)[1]
    answer.setText(str(utils.search_cat(query))).reply()


@bot.command(r".*",
         level="fight")  # интересно а как сделать так чтоб любое сообщение не принадлежащее к основному протоколу шло в дискорд
def complain(context: MessageContext):
    # я подозреваю что нужно подобную ноунейм команду просто в конец пихнуть
    # я не очень хочу тебе весь код сносить и менять как мне удобно и понятно потому что он сука твой
    # поэтому если что просто подправь я думаю это не так сложно и думаю это можно отдельно вынести
    if "ты не общаешься с админами еблан" * 0: return
    answer = MessageBuilder().setReplyMode(context)
    attempt = utils.send_ds_message("тут должен быть айди канала дискорда из дб", context.text)
    if attempt.status_code == 200:
        return answer.setText("Отправлено.").reply()
    return answer.setText("завались").reply()