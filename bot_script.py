import re

import requests

from script_base import MessageBuilder, ButtonsBuilder, MessageContext
import utils
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker
import local_server as ls

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
commands = []

api_url = "http://127.0.0.1:5000/api/hack"


def command(pattern, level="*", weak=False):
    def decorator(func):
        commands.append((level, pattern, func, weak))
        return func

    return decorator


@command("инфо")
def info(self, context: MessageContext):
    peerId = context.peer_id
    local_user_id = fsm_db.get_local_user_id(context)
    if local_user_id is None:
        answer = MessageBuilder().setText("У вас пока что нет аккаунта!").setPeerId(peerId)
    else:
        user_info = local_user_db.get_info(context)
        fsm_level = fsm_db.get_state(context)
        answer = MessageBuilder().setText(f"Ваша информация об аккаунте:\n\n{user_info}").setPeerId(peerId).addText(
            f"fsmstate = {fsm_level}")
    self.send_message(answer)


@command(["корзина", "cart"])
def cart(self, context: MessageContext):
    peerId = context.peer_id
    fsm_db.update_state(context, "*")

    answer = MessageBuilder().setText("выбирай че хочешь ну из каталогов").setPeerId(peerId)
    buttons = ButtonsBuilder()
    categories = ls.get_values()['categories']
    for i in categories:
        buttons.add(categories[i], f"selectcategory {i}")
    answer.setButtons(buttons)
    self.send_message(answer)


@command("selectcategory \\d+")
def selectcategory(self, context: MessageContext):
    peerId = context.peer_id
    fsm_db.update_state(context, "*")

    category_id = int(context.text.split()[1])
    category_items = ls.get_values()['categorized'][category_id]
    category_name = ls.get_values()['categories'][category_id]

    buttons = ButtonsBuilder()
    buttons.add("Добавить предмет", f"chooseitem {category_id}")
    buttons.add("Назад", "cart")

    answer = MessageBuilder().setPeerId(peerId).setButtons(buttons)
    answer.addText(f"Категория \"{category_name}\"\n", start="")
    for i in category_items:
        answer.addText(f"{category_items[i][1]} (ID: {i})")

    self.send_message(answer)


@command("chooseitem \\d+")
def chooseitem(self, context: MessageContext):
    peerId = context.peer_id
    cart_size = info_worker.get_cart_size(context)
    answer = MessageBuilder().setPeerId(peerId)

    if cart_size >= info_worker.get_value(context, 'cart_size'):
        answer.addText("Корзина переполнена")
        buttons = ButtonsBuilder()
        buttons.add("Начать взлом", "starthack")
        buttons.add("Убрать предмет из корзины", "removeitem")
        buttons.add("Назад", "cart")
        answer.setButtons(buttons)
        return self.send_message(answer)

    answer.addText("Напишите ID нужного вам предмета")

    fsm_db.update_state(context, context.text)
    self.send_message(answer)


@command(".*", level="chooseitem", weak=True)
def chooseitem2(self, context: MessageContext):
    peerId = context.peer_id
    text = context.text
    category_id = context.fsm[0]

    buttons = ButtonsBuilder()
    buttons.add("Назад", f"selectcategory {category_id}")
    answer = MessageBuilder().setPeerId(peerId).setButtons(buttons)

    result = re.search(r"\d+", text)
    if not result:
        answer.addText("Неправильно введено ID. Пожалуйста, напишите целое число.")
        self.send_message(answer)
        return

    item_id = int(result.group(0))
    items_data = ls.get_values()['items']

    if item_id not in items_data:
        answer.addText("Такого предмета нет в каталоге. Попробуйте еще раз.")
        self.send_message(answer)
        return

    limit_amount = items_data[item_id][0]

    if limit_amount != "Нет":
        buttons.insert(0, "Добавить максимальное количество", f"{limit_amount}")
    answer.addText(f"Введите количество предмета, которое вы хотите добавить на аккаунт")
    answer.addText(f"(Лимит: {limit_amount})")
    fsm_db.update_state(context, f"additem {item_id}")
    self.send_message(answer)


@command(".*", level="additem", weak=True)
def additem(self, context: MessageContext):
    peerId = context.peer_id
    text = context.text
    item_id = int(context.fsm[0])
    items_data = ls.get_values()['items'][item_id]

    buttons = ButtonsBuilder()
    buttons.add("Смотреть предметы", f"selectcategory {items_data[2]}")
    answer = MessageBuilder().setPeerId(peerId).setButtons(buttons)

    result = re.search(r"\d+", text)
    if not result:
        answer.addText("Неправильно введено количество. Пожалуйста, напишите целое число.")
        self.send_message(answer)
        return

    amount = int(result.group(0))

    if items_data[0] != "Нет":
        if amount > items_data[0]:
            amount = items_data[0]
            answer.addText("Вы превысили лимит, поэтому в корзину будет добавлено максимальное количество\n")

    info_worker.add_to_cart(context, item_id, amount)
    fsm_db.update_state(context, "*")
    answer.addText(f"Предмет {items_data[1]} ({amount}) добавлен в корзину")
    buttons.insert(0, "Начать взлом", "starthack")
    buttons.insert(0, "Посмотреть корзину", "viewcart")
    self.send_message(answer)


def addCart(answer, cart, items_info, only_item=None, show_id=True):
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
        else:
            answer.addText(f"{cart[i]} {item_name} {id_text}", start="\n --- ")


@command("viewcart")
def viewcart(self, context: MessageContext):
    peerId = context.peer_id
    cart = info_worker.get_value(context, 'cart')
    items_info = ls.get_values()['items']
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setPeerId(peerId).setButtons(buttons)
    cart_size = info_worker.get_cart_size(context)
    max_cart_size = info_worker.get_value(context, 'cart_size')

    buttons.add("Смотреть категории предметов", "cart")
    if len(cart) == 0:
        answer.addText("Корзина пуста")
    else:
        buttons.add("Убрать предмет", "removeitem")
        buttons.add("Начать взлом", "starthack")
        answer.addText("Ваша корзина:\n")
        addCart(answer, cart, items_info)

    answer.addText(f"\nЗаполненность корзины: {cart_size} из {max_cart_size} предметов")
    self.send_message(answer)


@command("removeitem")
def removeitem(self, context: MessageContext):
    peerId = context.peer_id
    answer = MessageBuilder().setPeerId(peerId)
    buttons = ButtonsBuilder()
    buttons.add("Вернуться в корзину", "viewcart")

    if info_worker.get_cart_size(context) == 0:
        answer.addText("Корзина пуста")
    else:
        answer.addText("Напишите ID нужного вам предмета")
        fsm_db.update_state(context, context.text)
    self.send_message(answer)


@command(".*", level="removeitem")
def removeitem(self, context: MessageContext):
    peerId = context.peer_id
    regex = re.search(r"\d+", context.text)
    buttons = ButtonsBuilder().add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setPeerId(peerId).setButtons(buttons)

    if not regex:
        answer.addText("Неправильно введен ID предмета")
        self.send_message(answer)
        return

    item_id = int(regex.group(0))
    if item_id not in info_worker.get_value(context, 'cart'):
        answer.addText("Такого предмета нет в корзине")
        self.send_message(answer)
        return

    items_info = ls.get_values()['items']
    stackable = info_worker.check_stackable(item_id)

    if stackable:
        if len(info_worker.get_value(context, 'cart')[item_id]) > 1:
            info_worker.del_from_cart(context, item_id, 1)
            fsm_db.update_state(context, f"removeitem2 {item_id}")
            answer.addText("Пожалуйста, уточните какой именно предмет вы хотите удалить из корзины (Укажите число)\n")
            addCart(answer, info_worker.get_value(context, 'cart'), items_info, item_id, show_id=False)
            self.send_message(answer)
            return

    info_worker.del_from_cart(context, item_id)
    fsm_db.update_state(context, "*")
    answer.addText("Предмет удален из корзины")
    self.send_message(answer)


@command(".*", level="removeitem2")
def removeitem2(self, context: MessageContext):
    peerId = context.peer_id
    regex = re.search(r"\d+", context.text)
    buttons = ButtonsBuilder().add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setPeerId(peerId).setButtons(buttons)

    if not regex:
        answer.addText("Пожалуйста, введите число")
        self.send_message(answer)
        return

    item_id = int(context.fsm[0])

    res = info_worker.del_from_cart(context, item_id, int(regex.group(0)))
    if res:
        fsm_db.update_state(context, "*")
        answer.addText("Предмет удален из корзины")
    else:
        answer.addText("Такого предмета нет в корзине")
    self.send_message(answer)


@command("starthack")
def starthack(self, context: MessageContext):
    peerId = context.peer_id
    answer = MessageBuilder().setPeerId(peerId)
    buttons = ButtonsBuilder()
    buttons.add("Вернуться в корзину", "viewcart")
    answer.addText("Пожалуйста, пришлите коды от аккаунта (текстом или скриншотом)").setButtons(buttons)
    fsm_db.update_state(context, context.text)
    self.send_message(answer)


@command(".*", level="starthack", weak=True)
def starthack(self, context: MessageContext):
    peerId = context.peer_id
    buttons = ButtonsBuilder()
    buttons.add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setPeerId(peerId).setButtons(buttons)
    attachments = context.attached_photos
    msg = context.text
    codes = None
    if len(attachments) > 0:
        url = attachments[0]
        image = utils.get_image(url)
        image = image.crop(utils.get_codes_box(image.size))
        msg = utils.getText(image)
    try:
        codes = utils.extract_codes(msg)
        res = f"Ваши коды: {codes}"
    except:
        res = "Не удалось получить коды. отправь по нормальному дебил"
    answer.setText(res)
    self.send_message(answer)
    if not codes: return
    transfer, pin = codes
    data, success, version = utils.getSave(transfer, pin)
    if not success:
        res = "Не удалось получить сохранение. Убедитесь в правильности кодов."
        answer.setText(res)
        return self.send_message(answer)
    else:
        res = "Ваше сохранение было отправлено в очередь на взлом. Примерное время ожидания: вечность"
        answer.setText(res)
        self.send_message(answer)
        answer.setText(f"Брат твой инкури {utils.getInq(data)}")
        self.send_message(answer)
        files = {"save": data}
        headers = {"cart": "123", "ver": version}
        hack_request = requests.post(api_url, files=files, headers=headers)
        answer.setText(str(hack_request.content))
        self.send_message(answer)


def reg(context: MessageContext):
    local_user_id = fsm_db.get_local_user_id(context)
    if local_user_id is None:
        local_user_id = local_user_db.create_user()
        fsm_db.set_local_user_id(context, local_user_id)


@command(".*", level="first_msg")
def not_baza(self, context: MessageContext):
    peerId = context.peer_id
    answer = MessageBuilder().setText(f"здарова").setPeerId(peerId)
    buttons = ButtonsBuilder()
    buttons.add("Корзина", "cart")
    answer.setButtons(buttons)
    self.send_message(answer)
    reg(context)
    fsm_db.update_state(context, "*")
