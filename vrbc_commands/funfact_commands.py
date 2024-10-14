from bot_script import bot
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
import random

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


facts = [
    "Вы можете скопировать свою прошлую корзину. Функция доступна по команде !пресеты",
    "В боте существует система пресетов, что позволяет сохранить набор предметов, чтобы быстро добавлять их в корзину. Функция доступна по команде !пресеты",
    "Если у вас возникли проблемы или вопросы, вы можете обратиться к администрации бота с помощью команды !отправить",
    "Вы можете сохранить свой аккаунт не только во время накрутки, но и в специальном меню. Для этого используйте команду !сохранить",
    "Этот бот поддерживает накрутку как для глобальной, так и для японской версии игры",
    "В боте есть функция восстановления аккаунта. Она поможет вам вернуть доступ к аккаунту, если вы его потеряли, если он был заблокирован, или даже если вы его случайно удалили. Для этого используйте команду !восстановить"
]


@bot.command("funfact", level=[".*", "hack_process"])
def funfact(context: MessageContext):
    buttons = ButtonsBuilder().add("Другой факт", "funfact")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.setText(random.choice(facts)).reply()


@bot.command(".*", level="hack_process")
def hack_process(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Случайный факт о боте", "funfact")
    MessageBuilder().setReplyMode(context).setButtons(buttons).setText("Пожалуйста, подождите...").reply()
