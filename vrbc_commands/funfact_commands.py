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
    "В боте есть функция восстановления аккаунта. Она поможет вам вернуть доступ к аккаунту, если вы его потеряли, если он был заблокирован, или даже если вы его случайно удалили. Для этого используйте команду !восстановить",
    "Кнопка \"Добавить предмет\" на самом деле почти что декоративная.\nЕсли прошлое сообщение бота это список предметов или сообщение об успешном добавлении, то вы можете просто отправить ID следующего предмета, который вы хотите добавить, не нажимая каждый раз на кнопку.",
    "Когда-то давно бот работал по расписанию. Вы могли выдавать себе предметы примерно с обеда до 21 часа...",
    "Когда-то бот был сделан для игры в Китай. Там было много других ботов, но весьма сильно различных.\n\n(я вообще не знаю что это значит, этот текст случайно сгенерировала нейросеть, помогающая разработчику с кодом)",
    "Лет 5 назад в группе был пост с текстом что-то вроде \"Автоматизации заказов не будет, не просите\".\nДа, раньше все ваши заказы делались нами вручную!",
    "Раньше вы мало что могли добавить в бота, не откалибровав его под свой аккаунт. Каждый раз перед выдачей вы должны были выписывать сколько у вас было билетов или фруктов, чтобы он мог работать",
    "Иногда бот выдает редкий факт, шанс появления которого примерно 1%"
]

for _ in range(3):
    facts += facts

facts.append("Вам выпал редкий факт! Шанс на него крайне мал, но, несмотря на это, он абсолютно бесполезен!")


@bot.command("funfact", level=["*", "hack_process"])
def funfact(context: MessageContext):
    buttons = ButtonsBuilder().add("Другой факт", "funfact")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.setText(random.choice(facts)).reply()


@bot.command("huh_whatisthat", level=["*", "hack_process", "first_msg"])
def huh_whatisthat(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Первый раз пользуюсь", "huh_whatisthat_frst")
    buttons.add("Уже пользовался", "huh_whatisthat_alrdy")
    answer.setText("Вы никогда раньше не пользовались ботом?").reply()


@bot.command("huh_whatisthat_frst", level=["*", "hack_process", "first_msg"])
def huh_whatisthat_frst(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Написать администрации", "startfight 1")
    answer.setText("Если вы действительно не пользовались ботом на этом аккаунте игры, то кто-то другой получил доступ к вашему аккаунту.")
    answer.addText("Обратитесь в администрацию, чтобы у вас не было проблем с дальнейшим использованием бота").reply()


@bot.command("huh_whatisthat_alrdy", level=["*", "hack_process", "first_msg"])
def huh_whatisthat_alrdy(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Да", "huh_whatisthat_alrdy_yes")
    buttons.add("Нет", "huh_whatisthat_alrdy_no")
    answer.setText("Вы первый раз пользуетесь ботом на ЭТОМ аккаунте игры?").reply()


@bot.command("huh_whatisthat_alrdy_yes", level=["*", "hack_process", "first_msg"])
def huh_whatisthat_alrdy_yes(context: MessageContext):
    huh_whatisthat_frst(context)


@bot.command("huh_whatisthat_alrdy_no", level=["*", "hack_process", "first_msg"])
def huh_whatisthat_alrdy_no(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("У меня остались вопросы", "startfight 1")
    answer.setText("В таком случае, теперь этот аккаунт игры привязан к нескольким страницам, с которых вы писали.").reply()


@bot.command(".*", level="hack_process")
def hack_process(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Случайный факт о боте", "funfact")
    MessageBuilder().setReplyMode(context).setButtons(buttons).setText("Пожалуйста, подождите...").reply()
