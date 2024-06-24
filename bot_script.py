import re

from script_base import MessageBuilder, ButtonsBuilder, MessageContext
import utils
from db_worker import FSMDatabase, LocalUsersDatabase
import local_server as ls

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
commands = []


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
        answer = MessageBuilder().setText(f"Ваша информация об аккаунте:\n\n{user_info}").setPeerId(peerId).addText(f"fsmstate = {fsm_level}")
    self.send_message(answer)


@command(["корзина", "cart"])
def cart(self, context: MessageContext):
    peerId = context.peer_id
    fsm_db.update_state(context, "*")

    answer = MessageBuilder().setText("выбирай че хочешь ну из каталогов").setPeerId(peerId)
    buttons = ButtonsBuilder()
    categories = ls.get_catalog()['categories']
    for i in categories:
        buttons.add(categories[i], f"selectcategory {i}")
    answer.setButtons(buttons)
    self.send_message(answer)


@command("selectcategory \\d+")
def selectcategory(self, context: MessageContext):
    peerId = context.peer_id
    fsm_db.update_state(context, "*")

    category_id = int(context.text.split()[1])
    category_items = ls.get_catalog()['categorized'][category_id]
    category_name = ls.get_catalog()['categories'][category_id]

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

    answer = MessageBuilder().setPeerId(peerId)
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
    items_data = ls.get_catalog()['items']

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
    items_data = ls.get_catalog()['items'][int(context.fsm[0])]

    buttons = ButtonsBuilder()
    buttons.add("Назад", f"chooseitem {items_data[2]}")
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
            utils.add_to_cart(items_data[1], amount, context)

    fsm_db.update_state(context, "*")
    answer.addText(f"Предмет {items_data[1]} ({amount}) добавлен в корзину")
    self.send_message(answer)


@command("рег")
def reg(self, context: MessageContext):
    peerId = context.peer_id
    local_user_id = fsm_db.get_local_user_id(context)
    if local_user_id is not None:
        answer = MessageBuilder().setText("У вас уже есть аккаунт").setPeerId(peerId)
    else:
        local_user_id = local_user_db.create_user()
        fsm_db.set_local_user_id(context, local_user_id)
        answer = MessageBuilder().setText("Ваш аккаунт создан").setPeerId(peerId)
    self.send_message(answer)


@command("setvalue")
def setvalue(self, context: MessageContext):
    peerId = context.peer_id
    fsm_db.update_state(context, "setvalue")
    answer = MessageBuilder().setText("Введите число").setPeerId(peerId)
    self.send_message(answer)


@command("\\d+", level="setvalue")
def setvalue2(self, context: MessageContext):
    peerId = context.peer_id
    value = context.text
    local_user_db.update_info(context, value)
    fsm_db.update_state(context, "*")
    answer = MessageBuilder().setText(context.text).setPeerId(peerId)
    self.send_message(answer)


@command(".*", level="setvalue")
def setvalue3(self, context: MessageContext):
    peerId = context.peer_id
    answer = MessageBuilder().setText("Неверное значение. Введите число!").setPeerId(peerId)
    self.send_message(answer)


@command(["test", "тест"])
def test_message(self, context: MessageContext):
    peerId = context.peer_id
    buttons = ButtonsBuilder().add("Кнопка 1", "payload1").add("Тест кнопки", "payload2")
    answer = MessageBuilder().setText("Тестовое сообщение").setPeerId(peerId).setButtons(buttons)
    self.send_message(answer)


@command("img")
def get_codes(self, context: MessageContext):
    peerId = context.peer_id
    attachments = context.attached_photos
    if len(attachments) == 0:
        answer = MessageBuilder().setText("Не нашлось картинок").setPeerId(peerId)
    else:
        url = attachments[0]
        image = utils.get_image(url)
        image = image.crop(utils.get_codes_box(image.size))
        res = utils.getText(image)
        try:
            res = utils.extract_codes(res)
            res = f"Ваши коды: {res}"
        except:
            res = "Нет кодов"
        answer = MessageBuilder().setPeerId(peerId).setText(res)

    self.send_message(answer)


@command("fsmtest", level="test")
def fsmtest(self, context: MessageContext):
    peerId = context.peer_id
    answer = MessageBuilder().setText(f"Тест FSM - {context.fsm}").setPeerId(peerId)
    self.send_message(answer)


@command("payload2")
def testbutton(self, context: MessageContext):
    peerId = context.peer_id
    answer = MessageBuilder().setText("Тестовое сообщение с нажатия кнопки").setPeerId(peerId)
    self.send_message(answer)


@command(["test", "тест"], level="first_msg")
def megabaza(self, context: MessageContext):
    peerId = context.peer_id
    answer = MessageBuilder().setText(f"лан").setPeerId(peerId)
    fsm_db.update_state(context, "*")
    self.send_message(answer)


@command(".*", level="first_msg")
def not_baza(self, context: MessageContext):
    peerId = context.peer_id
    answer = MessageBuilder().setText(f"иди нахуй потому что - {context.fsm}").setPeerId(peerId)
    self.send_message(answer)


@command("вернись")
def backto(self, context: MessageContext):
    peerId = context.peer_id
    fsm_db.update_state(context, "first_msg false")
    answer = MessageBuilder().setText(f"как скажешь").setPeerId(peerId)
    self.send_message(answer)


@command("вернисьTRUE")
def backto2(self, context: MessageContext):
    peerId = context.peer_id
    fsm_db.update_state(context, "first_msg true")
    answer = MessageBuilder().setText(f"как скажешь").setPeerId(peerId)
    self.send_message(answer)
