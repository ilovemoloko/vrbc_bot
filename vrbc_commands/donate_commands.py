from bot_script import bot, addBoost, give_boost
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
import local_server
import utils
import re

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


@bot.command("boosts")
def boosts(context: MessageContext):
    boosts = info_worker.get_value(context, 'boosts')
    boosts_server = local_server.get_default_values()['boosts']
    passive_boosts = []
    usable_boosts = []

    for boost_id in boosts:
        if boosts_server[boost_id]['type'] == "passive":
            passive_boosts.append(boost_id)
        else:
            usable_boosts.append(boost_id)

    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText(f"Список ваших бустов:\n\n")
    for boost in usable_boosts:
        amount = boosts[boost]
        if amount <= 0:
            continue
        addBoost(answer, boosts_server[boost], boost, amount)
        answer.addText("\n")
    if len(usable_boosts) == 0:
        answer.addText("У вас пока нет активируемых бустов")

    buttons.add("Использовать буст", "selectboost")
    if len(passive_boosts) > 0:
        buttons.add("Посмотреть пассивные бусты", "passiveboosts")
    buttons.add("Магазин бустов", "boostshop")
    buttons.add("Перейти в корзину", "viewcart")
    answer.reply()


@bot.command("passiveboosts")
def passiveboosts(context: MessageContext):
    boosts = info_worker.get_value(context, 'boosts')
    boosts_server = local_server.get_default_values()['boosts']

    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText(f"Список пассивных бустов:\n\n")
    for boost in boosts:
        if boosts_server[boost]['type'] == "passive":
            addBoost(answer, boosts_server[boost], boost, desc=True)
            answer.addText("\n")
    if len(boosts) == 0:
        answer.addText("У вас пока нет активируемых бустов")

    buttons.add("Назад", "boosts")
    answer.reply()


@bot.command("selectboost")
def selectboost(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Вернуться", "boosts")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Напишите ID нужного буста").reply()
    fsm_db.update_state(context, context.text)


@bot.command(".*", level="selectboost", weak=True)
def selectboost2(context: MessageContext):
    boosts = info_worker.get_value(context, 'boosts')
    boosts_server = local_server.get_default_values()['boosts']

    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    boost_id = context.text
    if boost_id not in boosts or boosts[boost_id] <= 0:
        answer.addText("У вас нет этого буста в списке")
        answer.reply()
        return

    buttons.add("Да, это нужный буст", f"useboost {boost_id}")
    buttons.add("Нет, вернуться назад", "boosts")

    answer.addText(f"Вы хотите использовать этот буст?\n\n")
    addBoost(answer, boosts_server[boost_id], boost_id, desc=True)
    answer.reply()


@bot.command("useboost .*")
def useboost(context: MessageContext):
    boost_id = context.text.split(" ", 1)[1]
    status = info_worker.use_boost(context, boost_id)
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться", "boosts")
    buttons.add("Перейти в корзину", "viewcart")
    if status:
        answer.addText("Буст использован!")
    else:
        answer.addText("Ошибка при использовании буста. Возможно, вы уже его используете")
    answer.reply()


@bot.command("reducecd")
def reducecd(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Задержку можно уменьшить двумя способами:\n\n")
    buttons.add("1) Донат", "donate")
    buttons.add("2) Реферальная система", "referral")
    buttons.add("Перейти к выбору предметов", "cart")
    answer.reply()


@bot.command("donate")
def donate(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    balance = info_worker.get_value(context, 'donate')
    answer.addText(f"""Вы задонатили {balance}₽
    
Чтобы поддержать разработку бота, Вы можете пожертвовать любую сумму. 
Сумма пожертвований может использоваться для покупки бустов.
 
У донатеров есть следующие преимущества:
1. От 35 руб.: 8 предметов в корзине, 27 часов между использованием бота
2. От 75 руб.: 10 предметов в корзине, 23 часа между использованиями бота
3. От 125 руб.: 12 предметов в корзине, 19 часов между использованием бота
4. От 175 руб.: 14 предметов в корзине, 17 часов между использованием бота
5. От 250 руб.: 17 предметов в корзине, 9 часов между использованием бота""")
    buttons.add("Пожертвовать", "donate2")
    buttons.add("Магазин бустов", "boostshop")
    buttons.add("Меню", "menu")
    answer.reply()


@bot.command("donate2")
def donate2(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "reducecd")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Напишите сумму пожертвования").reply()
    fsm_db.update_state(context, context.text)


@bot.command(r"\d+", level="donate2", weak=True)
def donate3(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "reducecd")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    regex = re.search(r"\d+", context.text)
    if not regex:
        return answer.addText("Введите число").reply()

    local_user_id = fsm_db.get_local_user_id(context)
    donate_url = utils.get_donate_url(local_user_id, int(regex.group(0)))
    answer.addText("Ссылка на пожертвование: " + donate_url).reply()
    fsm_db.update_state(context, "first_msg")


@bot.command("boostshop")
def boostshop(context: MessageContext):
    fsm_db.update_state(context, "*")
    buttons = ButtonsBuilder()
    buttons.add("Купить", "boostshop2")
    buttons.add("Бусты", "boosts")
    buttons.add("Главное меню", "начать")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    balance = info_worker.get_value(context, 'donate')
    answer.addText(f"Ваш баланс: {balance}₽")
    answer.addText("Список бустов для покупки:\n\n")
    boosts_server = local_server.get_default_values()['boosts']
    boosts_store = local_server.get_default_values()['boosts_store']

    for boost_id in boosts_store:
        addBoost(answer, boosts_server[boost_id], boost_id, desc=False)
        answer.addText(f"Цена: {boosts_store[boost_id]}₽\n\n")
    answer.reply()


@bot.command("boostshop2")
def boostshop2(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "boostshop")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Введите ID буста из магазина").reply()
    fsm_db.update_state(context, context.text)


@bot.command(r"buyboost .*", level="boostshop2", weak=True)
def buyboost(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Назад", "boostshop")
    boost_id = context.text.split(" ", 1)[1]
    boosts_store = local_server.get_default_values()['boosts_store']
    if boost_id not in boosts_store:
        return answer.addText("Такого буста нет в магазине").reply()

    boost_cost = boosts_store[boost_id]
    status = info_worker.add_donate(context, -boost_cost)
    if not status:
        return answer.addText(f"Произошла ошибка").reply()

    give_boost(context, boost_id)

    buttons.insert(0, "Бусты", "boosts")
    answer.addText("Спасибо за покупку!\n\n"
                   "Теперь вы можете в любой момент "
                   "использовать этот буст во разделе \"Бусты\"").reply()


@bot.command(r".*", level="boostshop2", weak=True)
def boostshop3(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "boostshop")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    boost_id = context.text

    boosts_store = local_server.get_default_values()['boosts_store']
    if boost_id not in boosts_store:
        return answer.addText("Такого буста нет в магазине").reply()

    boost_cost = boosts_store[boost_id]
    balance = info_worker.get_value(context, 'donate')
    if balance < boost_cost:
        return answer.addText(f"Недостаточно средств ({balance}₽)").reply()

    buttons.insert(0, "Подтвердить покупку", f"buyboost {boost_id}")
    answer.addText(f"Вы точно хотите купить этот буст за {boosts_store[boost_id]}₽?").reply()
