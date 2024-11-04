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
        self.running = True

    def stop(self):
        self.running = False

    def command(self, pattern, level="*", weak=False, ignore_case=False, replace_newline=" "):
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            levels = level
            if isinstance(level, str):
                levels = [level]
            for lv in levels:
                self.commands.append((lv, pattern, wrapper, weak, ignore_case, replace_newline))
            return wrapper
        return decorator


def initialize_bot_commands():
    import vrbc_commands
    vrbc_commands.lets_go = True


bot = Bot(commands)


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

    message.addText(f"{boost_name}\nID: {boost_id}", start="")
    if desc:
        message.addText(f"Описание: {boost_desc}")
    if amount is not None:
        message.addText(f"Осталось использований: {amount}")


initialize_bot_commands()


@bot.command(".*", level="first_msg")
def start_message(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Увидеть каталог предметов", "cart").add("Меню функций", "menu")
    buttons.add("Помощь | Тех. поддержка", "help")
    MessageBuilder().setReplyMode(context).setText(
        f"Здравствуй! В этом боте ты можешь получить различные предметы в игре The Battle Cats бесплатно.\n"
        f"Ты всегда можешь вернуться к этому сообщению, написав Начать\n\n"
        f"Нажми \"Увидеть каталог предметов\", чтобы начать добавлять их в корзину").setButtons(buttons).reply()
    reg(context)
    fsm_db.update_state(context, "*")


@bot.command(["начать", "!начать", "почати", "start", '"начать"'], ignore_case=True)
def start_message_2(context: MessageContext):
    start_message(context)


@bot.command(".*")
def unknown_command(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    answer.setText('''Бот не понимает, что вы хотите. Пожалуйста, воспользуйтесь кнопками или отправьте "Начать" для возврата в меню.

Если нужна помощь админов, отправьте !отправить.''').reply()