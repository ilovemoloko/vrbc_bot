from bot_script import bot, addBoost
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB, MonthlyReportDatabase
import local_server
import utils
import re

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()
mrdb = MonthlyReportDatabase()


def give_boost(context: MessageContext, boost_id, amount=1):
    user_boosts = info_worker.get_value(context, 'boosts')
    if boost_id not in user_boosts:
        user_boosts[boost_id] = 0
    user_boosts[boost_id] += 1
    info_worker.set_value(context, 'boosts', user_boosts)


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
            answer.addText(f"Количество: {boosts[boost]}\n")
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

    boost_id = context.text.lower()
    if boost_id not in boosts or boosts[boost_id] <= 0:
        answer.addText("У вас нет этого буста в списке")
        answer.reply()
        return

    if boosts_server[boost_id]['type'] == "passive":
        answer.addText("Этот буст не является активируемым. Он и так всегда активен")
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


@bot.command("referral")
def referral(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Реферальная система пока что в разработке.").reply()


@bot.command("reducecd", level=["*", "first_msg"])
def reducecd(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Задержку можно уменьшить двумя способами:\n\n")
    buttons.add("1) Донат", "donate")
    buttons.add("2) Реферальная система", "referral")
    buttons.add("Перейти к выбору предметов", "cart")
    answer.reply()


@bot.command(["donate", "донат", "!донат"], level=["*", "first_msg"])
def donate(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    balance = info_worker.get_value(context, 'donate')
    boosts = info_worker.get_value(context, 'boosts')

    current_level = None
    for boost in boosts:
        if boost.startswith("donate"):
            current_level = boost.split("_")[1]
            break

    current_string = ""
    if current_level is not None:
        current_string = f"Текущий уровень: {current_level}\n"

    answer.addText(f"""Вы задонатили {balance}₽
{current_string}
    
Чтобы поддержать разработку бота, Вы можете приобрести бусты, добавляющие вам больше возможностей бота
 
Также можно приобрести следующие уровни привилегий:
1. 35 руб.: 8 предметов в корзине, 27 часов между использованием бота
2. 75 руб.: 10 предметов в корзине, 23 часа между использованиями бота
3. 125 руб.: 12 предметов в корзине, 19 часов между использованием бота
4. 175 руб.: 14 предметов в корзине, 17 часов между использованием бота
5. 250 руб.: 17 предметов в корзине, 9 часов между использованием бота

Количество бонусов от привилегий будет увеличиваться в будущем!""")
    buttons.add("Пожертвовать", "donate2")
    buttons.add("Купить уровень", "buy_dlevel")
    buttons.add("Магазин бустов", "boostshop")
    buttons.add("Главное меню", "start")
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

    donate_url = utils.get_donate_url(context.user_id, int(regex.group(0)), context.src)
    answer.addText("Этот сервис оплаты часто может выдавать техническую ошибку.\n"
                   "В первую очередь перепроверьте корректность ввода данных\n"
                   "Если вы убедились, что все данные правильные, но всё равно не можете перевести, "
                   "то обратитесь в поддержку бота с помощью команды !отправить\n"
                   "Вам отправят альтернативные способы оплаты (В том числе для тех, кто не живет в РФ)\n")
    answer.addText("Ссылка на пожертвование: " + donate_url).reply()
    fsm_db.update_state(context, "first_msg")


@bot.command("boostshop")
def boostshop(context: MessageContext):
    fsm_db.update_state(context, "*")
    buttons = ButtonsBuilder()
    buttons.add("Купить", "boostshop2")
    buttons.add("Бусты", "boosts")
    buttons.add("Пополнить баланс", "donate")
    buttons.add("Главное меню", "start")

    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    balance = info_worker.get_value(context, 'donate')
    answer.addText(f"Ваш баланс: {balance}₽")
    answer.addText("Список бустов для покупки:\n\n")
    boosts_server = local_server.get_default_values()['boosts']
    boosts_store = info_worker.get_bot_values(context)['boosts_store']

    for boost_id in boosts_store:
        if boost_id.startswith("donate"):
            continue
        addBoost(answer, boosts_server[boost_id], boost_id, desc=False)
        answer.addText(f"Цена: {boosts_store[boost_id]}₽\n\n")
    answer.reply()
    fsm_db.update_state(context, "boostshop2")


@bot.command("boostshop2")
def boostshop2(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "boostshop")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Введите ID буста из магазина").reply()
    fsm_db.update_state(context, "boostshop2")


@bot.command(r"buyboost .*", level=["boostshop2", "boostshop2cd", "boostshop2d"], weak=True)
def buyboost(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("В магазин бустов", "boostshop")
    boost_id = context.text.split(" ", 1)[1]
    boosts_store = info_worker.get_bot_values(context)['boosts_store']
    if boost_id not in boosts_store:
        return answer.addText("Такого буста нет в магазине").reply()

    boost_cost = boosts_store[boost_id]
    status = info_worker.add_donate(context, -boost_cost)
    if not status:
        return answer.addText(f"Произошла ошибка").reply()

    boosts = info_worker.get_value(context, 'boosts')
    if boost_id.startswith("donate"):
        to_delete = []
        for boost in boosts:
            if boost.startswith("donate"):
                to_delete.append(boost)

        if len(to_delete) > 0:
            for boost in to_delete:
                boosts.pop(boost)

            info_worker.set_value(context, 'boosts', boosts)

    give_boost(context, boost_id)

    buttons.insert(0, "Бусты", "boosts")
    boosts = local_server.get_default_values()['boosts']
    if boosts[boost_id]["type"] == "passive":
        answer.addText("Спасибо за покупку!\n\n"
                       "Этот буст работает всегда, поэтому его не нужно активировать").reply()
    else:
        answer.addText("Спасибо за покупку!\n\n"
                       "Теперь вы можете в любой момент "
                       "использовать этот буст в разделе \"Бусты\"").reply()
    fsm_db.update_state(context, "*")

    mrdb.add_boost_stat(boost_id)


@bot.command("buy_dlevel")
def boostshopd(context: MessageContext):
    fsm_db.update_state(context, "*")
    buttons = ButtonsBuilder()
    buttons.add("Купить", "boostshop2d")
    buttons.add("Пополнить баланс", "donate")
    buttons.add("Главное меню", "start")

    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    balance = info_worker.get_value(context, 'donate')
    answer.addText(f"Ваш баланс: {balance}₽")
    answer.addText("Список уровней для покупки:\n\n")
    boosts_server = local_server.get_default_values()['boosts']
    boosts_store = info_worker.get_bot_values(context)['boosts_store']

    for boost_id in boosts_store:
        if not boost_id.startswith("donate"):
            continue
        addBoost(answer, boosts_server[boost_id], boost_id, desc=False)
        answer.addText(f"Цена: {boosts_store[boost_id]}₽\n\n")
    answer.reply()
    fsm_db.update_state(context, "boostshop2d")


@bot.command("boostshop2d")
def boostshop2d(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "buy_dlevel")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Введите ID уровня из магазина").reply()
    fsm_db.update_state(context, "boostshop2d")


@bot.command(r".*", level="boostshop2d", weak=True)
def boostshop3d(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "buy_dlevel")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    boost_id = context.text.lower()

    if boost_id.isnumeric():
        boost_id = f"donate_{boost_id}"

    boosts_store = info_worker.get_bot_values(context)['boosts_store']
    if boost_id not in boosts_store:
        return answer.addText("Уровня с таким ID нет.\n"
                              "Пожалуйста, отправьте боту ID, указанный около названия в списке").reply()

    boost_cost = boosts_store[boost_id]
    balance = info_worker.get_value(context, 'donate')
    if balance < boost_cost:
        buttons.add("Пополнить баланс", "donate")
        return answer.addText(f"Недостаточно средств ({balance}₽, требуется {boost_cost}₽)").reply()

    buttons.insert(0, "Подтвердить покупку", f"buyboost {boost_id}")
    answer.addText(f"Вы точно хотите купить этот уровень за {boosts_store[boost_id]}₽?").reply()


@bot.command(r".*", level="boostshop2", weak=True)
def boostshop3(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "boostshop")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    boost_id = context.text.lower()

    boosts_store = info_worker.get_bot_values(context)['boosts_store']
    if boost_id not in boosts_store:
        return answer.addText("Буста с таким ID нет.\n"
                              "Пожалуйста, отправьте боту ID, указанный около названия в магазине").reply()

    boost_cost = boosts_store[boost_id]
    balance = info_worker.get_value(context, 'donate')
    if balance < boost_cost:
        buttons.add("Пополнить баланс", "donate")
        return answer.addText(f"Недостаточно средств ({balance}₽, требуется {boost_cost}₽)").reply()

    buttons.insert(0, "Подтвердить покупку", f"buyboost {boost_id}")
    answer.addText(f"Вы точно хотите купить этот буст за {boosts_store[boost_id]}₽?\n\n")
    boosts_server = local_server.get_default_values()['boosts']
    addBoost(answer, boosts_server[boost_id], boost_id, desc=True)
    answer.reply()


@bot.command(r"buy_slot")
def buy_slot(context: MessageContext):
    fsm_db.update_state(context, "boostshop2")
    context.text = "add_slot"
    boostshop3(context)


@bot.command([r"skip_cd", "!пропуск", "пропуск"], ignore_case=True)
def skip_cd(context: MessageContext):
    fsm_db.update_state(context, "*")
    buttons = ButtonsBuilder()
    buttons.add("Купить", "boostshop2cd")
    buttons.add("Полная версия магазина", "boostshop")
    buttons.add("Пополнить баланс", "donate")
    buttons.add("Вернуться в корзину", "viewcart")

    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    balance = info_worker.get_value(context, 'donate')
    answer.addText(f"Ваш баланс: {balance}₽")

    answer.addText("Список бустов для покупки:\n\n")
    boosts_server = local_server.get_default_values()['boosts']
    boosts_store = info_worker.get_bot_values(context)['boosts_store']

    for boost_id in boosts_store:
        if not boost_id.startswith("skip"):
            continue
        addBoost(answer, boosts_server[boost_id], boost_id, desc=False)
        answer.addText(f"Цена: {boosts_store[boost_id]}₽\n\n")
    answer.reply()
    fsm_db.update_state(context, "boostshop2cd")


@bot.command("boostshop2cd")
def boostshop2(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "skip_cd")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Введите ID буста из магазина").reply()
    fsm_db.update_state(context, "boostshop2cd")


@bot.command(r".*", level="boostshop2cd", weak=True)
def boostshop3(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "skip_cd")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    boost_id = context.text.lower()

    boosts_store = info_worker.get_bot_values(context)['boosts_store']
    if boost_id not in boosts_store:
        return answer.addText("Буста с таким ID нет.\n"
                              "Пожалуйста, отправьте боту ID, указанный около названия в магазине").reply()

    boost_cost = boosts_store[boost_id]
    balance = info_worker.get_value(context, 'donate')
    if balance < boost_cost:
        buttons.add("Пополнить баланс", "donate")
        return answer.addText(f"Недостаточно средств ({balance}₽, требуется {boost_cost}₽)").reply()

    buttons.insert(0, "Подтвердить покупку", f"buyboost {boost_id}")
    answer.addText(f"Вы точно хотите купить этот буст за {boosts_store[boost_id]}₽?\n\n")
    boosts_server = local_server.get_default_values()['boosts']
    addBoost(answer, boosts_server[boost_id], boost_id, desc=True)
    answer.reply()
