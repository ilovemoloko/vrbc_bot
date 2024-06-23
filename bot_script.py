from script_base import MessageBuilder, ButtonsBuilder, MessageContext
import utils
from db_worker import FSMDatabase, LocalUsersDatabase

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
commands = []


def command(pattern, level="*"):
    def decorator(func):
        commands.append((level, pattern, func))
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
        answer = MessageBuilder().setText(f"Ваша информация об аккаунте:\n\n{user_info}").setPeerId(peerId)
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
        image.save("huh.png")
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
