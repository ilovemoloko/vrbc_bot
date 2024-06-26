import re
import time

import requests

from script_base import MessageBuilder, ButtonsBuilder, MessageContext
import utils
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker
import local_server as ls

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
commands = []
debug = False

if not debug:
    base_url = "http://127.0.0.1:5000"
else:
    base_url = "https://lolidk111.pythonanywhere.com"

api_url = base_url + "/api/hack"
wait_time_url = base_url + "/wait"


def command(pattern, level="*", weak=False):
    def decorator(func):
        commands.append((level, pattern, func, weak))
        return func

    return decorator


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
    answer = MessageBuilder().setReplyMode(context).setText("выбирай че хочешь ну из каталогов").setButtons(buttons)

    categories = ls.get_values(context)['categories']
    for i in categories:
        buttons.add(categories[i], f"selectcategory {i}")
    answer.reply()


@command("selectcategory \\d+")
def selectcategory(context: MessageContext):
    fsm_db.update_state(context, "*")

    category_id = int(context.text.split()[1])
    category_items = ls.get_values(context)['categorized'][category_id]
    category_name = ls.get_values(context)['categories'][category_id]

    buttons = ButtonsBuilder()
    buttons.add("Добавить предмет", f"chooseitem {category_id}")
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

    cart_size = info_worker.get_cart_size(context)
    if cart_size >= info_worker.get_value(context, 'cart_size'):
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
    items_data = ls.get_values(context)['items']

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
    items_data = ls.get_values(context)['items'][item_id]

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
                answer.addText(f"{j} {item_name} {id_text}", start="\n --- ")
                changed = True
        else:
            answer.addText(f"{cart[i]} {item_name} {id_text}", start="\n --- ")
            changed = True
    return changed


@command("viewcart")
def viewcart(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Смотреть категории предметов", "cart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    cart = info_worker.get_value(context, 'cart')
    items_info = ls.get_values(context)['items']
    cart_size = info_worker.get_cart_size(context)
    max_cart_size = info_worker.get_value(context, 'cart_size')

    if len(cart) == 0:
        answer.addText("Корзина пуста")
    else:
        buttons.add("Убрать предмет", "removeitem")
        buttons.add("Начать взлом", "starthack")
        answer.addText("Ваша корзина:\n")
        addCart(answer, cart, items_info)

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

    items_info = ls.get_values(context)['items']
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
    items_info = ls.get_values(context)['items']

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
def starthack(context: MessageContext):
    attachments = context.attached_photos
    msg = context.text
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    current_time = int(time.time())
    user_last_use = info_worker.get_value(context, 'last_use')
    user_cooldown = info_worker.get_value(context, 'cooldown')
    next_use = user_cooldown - (current_time - user_last_use)

    if next_use > 0:
        buttons.add("Вернуться в корзину", "viewcart")
        return answer.addText(f"Пожалуйста, подождите ещё {utils.humanize_time(next_use)}").reply()

    fsm_db.update_state(context, "hack_process")

    if len(attachments) > 0:
        url = attachments[0]
        image = utils.get_image(url)
        msg = utils.getText(image)

    codes = None
    try:
        codes = utils.extract_codes(msg)
        res = "Коды получены. Начинаем процесс взлома..."
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
    else:
        inq = utils.getInq(data)

        if inq == "LOL":
            fsm_db.update_state(context, "starthack")
            return answer.setText("Ошибка обработки аккаунта.").reply()
        wait_time = requests.get(wait_time_url).content.decode("utf-8")
        answer.setText(f"Ваш аккаунт ({inq}) отправлен в очередь.")
        answer.addText(f"Примерное время ожидания до получения кодов: {wait_time} сек.").reply()

        cart = info_worker.get_value(context, 'cart')
        files = {"save": data}
        headers = {"cart": str(cart),
                   "ver": version,
                   "inq": inq,
                   "user": str(fsm_db.get_local_user_id(context))}
        hack_request = requests.post(api_url, files=files, headers=headers)
        hack_result = eval(hack_request.content.decode("utf-8"))

        if hack_result['status'] == 1:
            transfer, confirmation = hack_result['codes']
            answer.setText("Взлом успешен. Ваши коды:").reply()
            answer.setText(transfer).reply()
            answer.setText(confirmation).reply()

            info_worker.clear_cart(context)
            info_worker.set_value(context, 'last_use', current_time)
            fsm_db.update_state(context, "first_msg")
            answer.setText(f"Следующее использование бота будет возможно через {utils.humanize_time(user_cooldown)}")
        else:
            fsm_db.update_state(context, "starthack")
            answer.setText(f"Произошла ошибка. Причина: {hack_result['message']}").setButtons(buttons)

        return answer.reply()


@command(".*", level="hack_process")
def hack_process(context: MessageContext):
    MessageBuilder().setReplyMode(context).setText("Пожалуйста, подождите...").reply()
    fsm_db.update_state(context, "starthack")


def reg(context: MessageContext):
    local_user_id = fsm_db.get_local_user_id(context)
    if local_user_id is None:
        local_user_id = local_user_db.create_user()
        fsm_db.set_local_user_id(context, local_user_id)


@command(".*", level="first_msg")
def not_baza(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Корзина", "cart")
    MessageBuilder().setReplyMode(context).setText(f"здарова").setButtons(buttons).reply()
    reg(context)
    fsm_db.update_state(context, "*")
