import re
import time
import local_server
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
import utils
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
commands = []
debug = False


def command(pattern, level="*", weak=False, ignore_case=False):
    def decorator(func):
        commands.append((level, pattern, func, weak, ignore_case))
        return func

    return decorator


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


@command(r"сукорз [\s\S]*")
def sucart(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться в корзину", "viewcart")
    newcart_str = context.text.split("сукорз", 1)[1]
    for item in newcart_str.splitlines():
        item_id, amount = item.split()
        info_worker.add_to_cart(context, int(item_id), int(amount), ignore_max=True)
    answer.addText("Корзина обновлена").reply()


@command("инфо")
def info(context: MessageContext):
    local_user_id = fsm_db.get_local_user_id(context)
    answer = MessageBuilder().setReplyMode(context)
    if local_user_id is None:
        answer.setText("У вас пока что нет аккаунта!")
    else:
        user_info = local_user_db.get_info(context)
        fsm_level = fsm_db.get_state(context)
        answer.setText(f"Ваша информация об аккаунте:\n\n{user_info}").addText(f"fsmstate = {fsm_level}")
    answer.reply()


@command(["корзина", "cart"])
def cart(context: MessageContext):
    fsm_db.update_state(context, "*")
    buttons = ButtonsBuilder()
    answer = (MessageBuilder().setReplyMode(context)
              .setText("Вы можете выбрать предметы из представленных категорий").setButtons(buttons))

    categories = info_worker.get_bot_values(context)['categories']
    for i in categories:
        buttons.add(categories[i], f"selectcategory {i}")
    answer.reply()


@command("selectcategory \\d+")
def selectcategory(context: MessageContext):
    fsm_db.update_state(context, "*")

    category_id = int(context.text.split()[1])
    category_items = info_worker.get_bot_values(context)['categorized'][category_id]
    category_name = info_worker.get_bot_values(context)['categories'][category_id]

    buttons = ButtonsBuilder()
    buttons.add("Добавить предмет", f"chooseitem {category_id}")
    buttons.add("Корзина", "viewcart")
    buttons.add("Назад", "cart")

    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText(f"Категория \"{category_name}\"\n", start="")
    for i in category_items:
        answer.addText(f"{category_items[i][1]} (ID: {i})")

    answer.reply()


@command("chooseitem \\d+")
def chooseitem(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    user_bot_values = info_worker.get_bot_values(context)['default_user']

    cart_size = info_worker.get_cart_size(context)
    if cart_size >= info_worker.get_value(context, 'cart_size', src=user_bot_values):
        answer.addText("Корзина переполнена")
        buttons.add("Начать взлом", "starthack").add("Убрать предмет из корзины", "removeitem").add("Назад", "cart")
        return answer.reply()

    answer.addText("Напишите ID нужного вам предмета").reply()
    fsm_db.update_state(context, context.text)


@command(".*", level="chooseitem", weak=True)
def chooseitem2(context: MessageContext):
    text = context.text
    category_id = context.fsm[0]

    buttons = ButtonsBuilder()
    buttons.add("Назад", f"selectcategory {category_id}")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    result = re.search(r"\d+", text)
    if not result:
        return answer.addText("Неправильно введено ID. Пожалуйста, напишите целое число.").reply()

    item_id = int(result.group(0))
    items_data = info_worker.get_bot_values(context)['items']

    if item_id not in items_data:
        return answer.addText("Такого предмета нет в каталоге. Попробуйте еще раз.").reply()

    limit_amount = items_data[item_id][0]
    if limit_amount != "Нет":
        buttons.insert(0, "Добавить максимальное количество", f"{limit_amount}")
    fsm_db.update_state(context, f"additem {item_id}")
    answer.addText(f"Введите количество предмета, которое вы хотите добавить на аккаунт\n")
    answer.addText(f"Лимит: {limit_amount}").reply()


@command(".*", level="additem", weak=True)
def additem(context: MessageContext):
    text = context.text
    item_id = int(context.fsm[0])
    items_data = info_worker.get_bot_values(context)['items'][item_id]

    buttons = ButtonsBuilder()
    buttons.add("Смотреть предметы", f"selectcategory {items_data[2]}")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    result = re.search(r"\d+", text)
    if not result:
        return answer.addText("Неправильно введено количество. Пожалуйста, напишите целое число.").reply()

    amount = int(result.group(0))
    if items_data[0] != "Нет":
        if amount > items_data[0]:
            amount = items_data[0]
            answer.addText("Вы превысили лимит, поэтому в корзину будет добавлено максимальное количество\n")

    info_worker.add_to_cart(context, item_id, amount)
    fsm_db.update_state(context, "*")
    buttons.insert(0, "Начать взлом", "starthack")
    buttons.insert(0, "Посмотреть корзину", "viewcart")

    answer.addText(f"Предмет {items_data[1]} ({amount}) добавлен в корзину").reply()


def addCart(answer, cart, items_info, only_item=None, show_id=True):
    changed = False
    for i in cart:
        item_info = items_info[i]
        item_name = item_info[1]
        item_id = i
        id_text = f" (ID: {item_id})" if show_id else ""
        if not (item_id == only_item or only_item is None):
            continue
        if isinstance(cart[i], list):
            for j in cart[i]:
                answer.addText(f"{j} {item_name} {id_text}", start="\n -- ")
                changed = True
        else:
            answer.addText(f"{cart[i]} {item_name} {id_text}", start="\n -- ")
            changed = True
    return changed


@command("viewcart")
def viewcart(context: MessageContext):
    fsm_db.update_state(context, "*")
    buttons = ButtonsBuilder()
    buttons.add("Смотреть категории предметов", "cart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    user_bot_values = info_worker.get_bot_values(context)['default_user']

    cart = info_worker.get_value(context, 'cart')
    items_info = info_worker.get_bot_values(context)['items']
    cart_size = info_worker.get_cart_size(context)
    max_cart_size = info_worker.get_value(context, 'cart_size', src=user_bot_values)

    if len(cart) == 0:
        answer.addText("Корзина пуста")
    else:
        buttons.add("Начать взлом", "starthack")
        buttons.add("Убрать предмет", "removeitem")
        answer.addText("Ваша корзина:\n")
        addCart(answer, cart, items_info)

    buttons.add("Бусты", "boosts")
    buttons.add("Главное меню", "начать")
    answer.addText(f"\nЗаполненность корзины: {cart_size} из {max_cart_size} предметов").reply()


@command("removeitem")
def removeitem(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    if info_worker.get_cart_size(context) == 0:
        answer.addText("Корзина пуста")
    else:
        answer.addText("Напишите ID нужного вам предмета")
        fsm_db.update_state(context, context.text)
    answer.reply()


@command(".*", level="removeitem", weak=True)
def removeitem(context: MessageContext):
    regex = re.search(r"\d+", context.text)
    buttons = ButtonsBuilder().add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    if not regex:
        return answer.addText("Неправильно введен ID предмета").reply()

    item_id = int(regex.group(0))
    if item_id not in info_worker.get_value(context, 'cart'):
        return answer.addText("Такого предмета нет в корзине").reply()

    items_info = info_worker.get_bot_values(context)['items']
    stackable = info_worker.check_stackable(items_info[item_id])

    if stackable:
        if len(info_worker.get_value(context, 'cart')[item_id]) > 1:
            answer.addText("Пожалуйста, уточните какой именно предмет вы хотите удалить из корзины (Укажите число)\n")
            addCart(answer, info_worker.get_value(context, 'cart'), items_info, item_id, show_id=False)
            fsm_db.update_state(context, f"removeitem2 {item_id}")
            return answer.reply()

    info_worker.del_from_cart(context, item_id)
    fsm_db.update_state(context, "*")
    answer.addText("Предмет удален из корзины").reply()


@command(".*", level="removeitem2", weak=True)
def removeitem2(context: MessageContext):
    regex = re.search(r"\d+", context.text)
    buttons = ButtonsBuilder().add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    if not regex:
        return answer.addText("Пожалуйста, введите число").reply()

    item_id = int(context.fsm[0])

    res = info_worker.del_from_cart(context, item_id, int(regex.group(0)))
    if res:
        fsm_db.update_state(context, "*")
        answer.addText("Предмет удален из корзины")
    else:
        answer.addText("Такого предмета нет в корзине")
    answer.reply()


@command("starthack")
def starthack(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    answer.setText("Ваша корзина:\n")
    cart = info_worker.get_value(context, 'cart')
    items_info = info_worker.get_bot_values(context)['items']

    changed = addCart(answer, cart, items_info)
    if not changed:
        answer.addText("Корзина пуста")
        buttons.buttons = []
        buttons.add("Выбрать предметы", "cart")
        return answer.reply()
    buttons.add("Обратно к выбору предметов", "cart")
    answer.reply().setButtons(None)

    answer.setText("Пожалуйста, пришлите коды от аккаунта (текстом или скриншотом)").reply()
    fsm_db.update_state(context, context.text)


@command(".*", level="starthack", weak=True)
@level_on_error("starthack")
def starthack(context: MessageContext, retry=False):
    fsm_db.update_state(context, "hack_process")
    attachments = context.attached_photos
    msg = context.text
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    user_bot_values = info_worker.get_bot_values(context)['default_user']

    current_time = int(time.time())
    user_last_use = info_worker.get_value(context, 'last_use')
    user_cooldown = info_worker.get_value(context, 'cooldown', src=user_bot_values)
    next_use = user_cooldown - (current_time - user_last_use)

    if next_use > 0:
        buttons.add("Вернуться в корзину", "viewcart")
        fsm_db.update_state(context, "starthack")
        return answer.addText(f"Пожалуйста, подождите ещё {utils.humanize_time(next_use)}").reply()

    if len(attachments) > 0:
        url = attachments[0]
        image = utils.get_image(url)
        msg = utils.getText(image)

    codes = None
    try:
        codes = utils.extract_codes(msg)
        res = "Коды получены. Начинаем процесс взлома..."
        if not retry:
            answer.setText(res).reply()
    except:
        buttons.add("Вернуться в корзину", "viewcart")
        res = "Бот не нашел кодов в сообщении. Пожалуйста, пришлите коды от аккаунта (текстом или скриншотом)"
        answer.setText(res).reply()

    if not codes:
        fsm_db.update_state(context, "starthack")
        return

    transfer, pin = codes
    data, success, version = utils.getSave(transfer, pin)
    if not success and not debug:
        fsm_db.update_state(context, "starthack")
        buttons.add("Вернуться в корзину", "viewcart")
        return answer.setText("Не удалось получить сохранение. Убедитесь в правильности кодов.").reply()

    inq = utils.getInq(data)

    if inq == "LOL":
        fsm_db.update_state(context, "starthack")
        return answer.setText("Ошибка обработки аккаунта.").reply()

    status, msg = utils.inq_checker((inq, version), context)
    answer.setText(msg)
    if not status or status == "retry":
        fsm_db.update_state(context, "starthack")
        if status == "retry":
            answer.reply()
            return starthack(context, retry=True)
        buttons.add("Вернуться в корзину", "viewcart")
        return answer.reply()

    wait_time = local_server.get_wait_time()
    answer.addText(f"Примерное время ожидания до получения кодов: {wait_time} сек.").reply()

    cart = info_worker.get_value(context, 'cart')
    files = {"save": data}
    headers = {"cart": str(cart),
               "ver": version,
               "inq": inq,
               "user": str(fsm_db.get_local_user_id(context))}

    hack_request = local_server.hack_account(files, headers)
    hack_result = eval(hack_request.content.decode("utf-8"))

    if hack_result['status'] == 1:
        transfer, confirmation = hack_result['codes']
        answer.setText("Взлом успешен. Ваши коды:").reply()
        answer.setText(transfer).reply()
        answer.setText(confirmation).reply()

        info_worker.clear_cart(context)
        info_worker.clear_boosts(context)
        info_worker.set_value(context, 'last_use', current_time)
        fsm_db.update_state(context, "first_msg")
        buttons.add("Уменьшить время ожидания", "reducecd")
        answer.setText(f"Следующее использование бота будет возможно через {utils.humanize_time(user_cooldown)}")
    else:
        fsm_db.update_state(context, "starthack")
        answer.setText(f"Произошла ошибка. Причина: {hack_result['message']}").setButtons(buttons)

    return answer.reply()


@command(".*", level="hack_process")
def hack_process(context: MessageContext):
    MessageBuilder().setReplyMode(context).setText("Пожалуйста, подождите...").reply()


@command("save_account")
def save_account(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.setText("Пожалуйста, пришлите коды от аккаунта (текстом или скриншотом)").reply()
    fsm_db.update_state(context, "save_account")


@command(".*", level="save_account", weak=True)
def save_account_input(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    attachments = context.attached_photos
    msg = context.text

    answer.setText("Начинаем сохранять ваш аккаунт").reply().setText("")

    buttons.add("Перейти в главное меню", "начать")

    if len(attachments) > 0:
        url = attachments[0]
        image = utils.get_image(url)
        msg = utils.getText(image)

    try:
        codes = utils.extract_codes(msg)
    except:
        res = "Бот не нашел кодов в сообщении. Пожалуйста, пришлите коды от аккаунта (текстом или скриншотом)"
        return answer.setText(res).reply()

    transfer, pin = codes
    data, success, version = utils.getSave(transfer, pin)
    if not success and not debug:
        return answer.setText("Не удалось получить сохранение. Убедитесь в правильности кодов.").reply()

    inq = utils.getInq(data)
    if inq == "LOL":
        return answer.setText("Ошибка обработки аккаунта.").reply()

    status, msg = utils.inq_checker((inq, version), context)
    if status is not True:
        answer.setText(msg)
    if not status:
        fsm_db.update_state(context, "first_msg")
        return answer.reply()

    user_id = fsm_db.get_local_user_id(context)
    files = {"save": data}
    status, msg = local_server.backup_account(user_id, inq, files)
    answer.addText(f"Ваш код аккаунта: {inq}")
    answer.addText(msg).reply()
    fsm_db.update_state(context, "first_msg")


@command("recovery_account")
def recovery_account(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Перейти в главное меню", "начать")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    user_id = fsm_db.get_local_user_id(context)
    accounts = local_server.get_user_backups(user_id)

    if len(accounts) == 0:
        return answer.setText("У вас еще нет сохранений.").reply()
    elif len(accounts) == 1:
        old_inq = accounts[0]
        answer.setText(f"Восстанавливаем аккаунт {old_inq}").reply().setButtons(None)
        status, new_inq, msg, tc, cc = local_server.recovery_backup(user_id, old_inq)
        if not status:
            return answer.setText(msg).reply()
        utils.recovery_rite(context, old_inq, new_inq)
        answer.setText("Ваши коды: ").reply().setText(tc).reply().setText(cc).reply()
    else:
        text = "Выберите аккаунт для восстановления\n"
        for account in accounts:
            text += f" - - {account}\n"
        answer.setText(text).reply()
        fsm_db.update_state(context, "select_account")


@command(".*", level="select_account", weak=True)
def select_account(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.setText("Сейчас бот отправит коды аккаунта...").reply()
    buttons.add("Посмотреть список аккаунтов", "recovery_account")
    inq_regex = r"([\da-fA-F]{9})"
    result = re.search(inq_regex, context.text)

    if not result:
        return answer.setText("Вам нужно ввести 9-значный код из списка").reply()

    user_id = fsm_db.get_local_user_id(context)
    old_inq = result.group(0)
    status, new_inq, msg, tc, cc = local_server.recovery_backup(user_id, old_inq)
    if not status:
        return answer.setText(msg).reply()
    utils.recovery_rite(context, old_inq, new_inq)
    answer.setButtons(None)
    answer.setText("Ваши коды: ").reply().setText(tc).reply().setText(cc).reply()
    fsm_db.update_state(context, "first_msg")


def reg(context: MessageContext):
    local_user_id = fsm_db.get_local_user_id(context)
    if local_user_id is None:
        local_user_id = local_user_db.create_user()
        fsm_db.set_local_user_id(context, local_user_id)


@command(".*", level="first_msg")
def start_message(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Увидеть каталог предметов", "cart").add("Меню функций", "menu")
    MessageBuilder().setReplyMode(context).setText(
        f"Здравствуй! В этом боте ты можешь получить различные предметы в игре The Battle Cats бесплатно.\n"
        f"Ты всегда можешь вернуться к этому сообщению, написав Начать\n\n"
        f"Если вам нужна помощь/техническая поддержка, то нажмите кнопку Меню").setButtons(buttons).reply()
    reg(context)
    fsm_db.update_state(context, "*")


@command("начать", ignore_case=True)
def start_message_2(context: MessageContext):
    start_message(context)


@command("menu")
def menu_message(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Бусты", "boosts")
    buttons.add("Донаты", "donate")
    buttons.add("Пресеты", "presets")
    buttons.add("Восстановление/Сохранение аккаунтов", "recovery_menu")
    buttons.add("Помощь", "help")

    MessageBuilder().setText("Выберите пункт меню").setReplyMode(context).setButtons(buttons).reply()


@command("recovery_menu")
def recovery_menu(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Восстановить аккаунт", "recovery_account")
    buttons.add("Сохранить аккаунт", "save_account")
    buttons.add("Вернуться в меню", "menu")
    MessageBuilder().setText("Выберите пункт меню").setReplyMode(context).setButtons(buttons).reply()


def addBoost(message: MessageBuilder, boost, boost_id, amount=None, desc=False):
    boost_name = boost['name']
    boost_desc = boost['desc']

    message.addText(f"{boost_name} (ID: {boost_id})", start="")
    if desc:
        message.addText(f"Описание: {boost_desc}")
    if amount is not None:
        message.addText(f"Осталось использований: {amount}")


@command("boosts")
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


@command("passiveboosts")
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


@command("selectboost")
def selectboost(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Вернуться", "boosts")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Напишите ID нужного буста").reply()
    fsm_db.update_state(context, context.text)


@command(".*", level="selectboost", weak=True)
def selectboost2(context: MessageContext):
    boosts = info_worker.get_value(context, 'boosts')
    boosts_server = local_server.get_default_values()['boosts']

    buttons = ButtonsBuilder()
    buttons.add("Вернуться", "boosts")
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


@command("useboost .*")
def useboost(context: MessageContext):
    boost_id = context.text.split(" ", 1)[1]
    status = info_worker.use_boost(context, boost_id)
    answer = MessageBuilder().setReplyMode(context)
    if status:
        answer.addText("Буст использован!")
    else:
        answer.addText("Ошибка при использовании буста. Возможно, вы уже его используете")
    fsm_db.update_state(context, "first_msg")
    answer.reply()


@command("reducecd")
def reducecd(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Задержку можно уменьшить двумя способами:\n\n")
    buttons.add("1) Донат", "donate")
    buttons.add("2) Реферальная система", "referral")
    buttons.add("Перейти к выбору предметов", "cart")
    answer.reply()


@command("donate")
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
    buttons.add("Назад", "reducecd")
    answer.reply()


@command("donate2")
def donate2(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "reducecd")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Напишите сумму пожертвования").reply()
    fsm_db.update_state(context, context.text)


@command(r"\d+", level="donate2", weak=True)
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


@command("boostshop")
def boostshop(context: MessageContext):
    fsm_db.update_state(context, "*")
    buttons = ButtonsBuilder()
    buttons.add("Купить", "boostshop2")
    buttons.add("Назад", "reducecd")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Список бустов для покупки:\n\n")
    boosts_server = local_server.get_default_values()['boosts']
    boosts_store = local_server.get_default_values()['boosts_store']

    for boost_id in boosts_store:
        addBoost(answer, boosts_server[boost_id], boost_id, desc=False)
        answer.addText(f"Цена: {boosts_store[boost_id]}₽\n")
    answer.reply()


@command("boostshop2")
def boostshop2(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "boostshop")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Введите ID буста из магазина").reply()
    fsm_db.update_state(context, context.text)


@command(r"buyboost .*", level="boostshop2", weak=True)
def buyboost(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    boost_id = context.text.split(" ", 1)[1]
    fsm_db.update_state(context, "first_msg")
    boosts_store = local_server.get_default_values()['boosts_store']
    if boost_id not in boosts_store:
        return answer.addText("Такого буста нет в магазине").reply()

    boost_cost = boosts_store[boost_id]
    status = info_worker.add_donate(context, -boost_cost)
    if not status:
        return answer.addText(f"Произошла ошибка").reply()

    user_boosts = info_worker.get_value(context, 'boosts')
    if boost_id not in user_boosts:
        user_boosts[boost_id] = 0
    user_boosts[boost_id] += 1
    info_worker.set_value(context, 'boosts', user_boosts)
    answer.addText("Спасибо за покупку!").reply()


@command(r".*", level="boostshop2", weak=True)
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


@command(r"startfight .*")
def start_fight(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    message = "я не хочу пока тестировать как у тебя работает внедрение новых команд с тз синтаксиса"
    user = str(fsm_db.get_local_user_id(context))

    # если спор уже начат хз аезир сам сделай дб штуки
    if answer:
        return answer.setText("У Вас уже ведется диалог с админчиками. Пожалуйста, дождитесь ответа.").reply()
    req = utils.create_ds_channel(user, "PLATFORM")
    if req.status_code == 200:
        discord_channel_id = eval(req.text)['id']
        if message:
            utils.send_ds_message(discord_channel_id, message)
            return answer.setText("Ваше сообщение было передано администрации. уйди отсюда сука").reply()
        return answer.setText("Был начат спор с администрацией (вы выбрали смерть.)").reply()
    return answer.setText("Я НЕ МОГУ ОТПРАВИТЬ ПОЖАЛУЙСТА УЙДИ").reply()
    # тебе кстати возможно интересно как же так вышло что я начал работать
    # я обнаружил что нужно просто сесть за кодинг ночью под бедфингер-бейби блю
    #код дс бота кстати полностью готов нужно просто чут чут поиграться с изображениями (и здесь тоже)


@command(r"find .*")
def find_cat(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    query = context.text.split(" ", 1)[1]
    answer.setText(str(utils.search_cat(query))).reply()


@command(r".*",
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