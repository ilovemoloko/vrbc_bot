from script_base import MessageBuilder, ButtonsBuilder, MessageContext
import utils
from db_worker import FSMDatabase

db = FSMDatabase()
commands = []


def command(pattern, level="*"):
    def decorator(func):
        commands.append((level, pattern, func))
        return func

    return decorator


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
        res = utils.extract_codes(res)
        res = f"Ваши коды: {res}"
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
    db.update_state(context, "*")
    self.send_message(answer)


@command(".*", level="first_msg")
def not_baza(self, context: MessageContext):
    peerId = context.peer_id
    answer = MessageBuilder().setText(f"иди нахуй потому что - {context.fsm}").setPeerId(peerId)
    self.send_message(answer)


@command("вернись")
def backto(self, context: MessageContext):
    peerId = context.peer_id
    db.update_state(context, "first_msg false")
    answer = MessageBuilder().setText(f"как скажешь").setPeerId(peerId)
    self.send_message(answer)


@command("вернисьTRUE")
def backto2(self, context: MessageContext):
    peerId = context.peer_id
    db.update_state(context, "first_msg true")
    answer = MessageBuilder().setText(f"как скажешь").setPeerId(peerId)
    self.send_message(answer)
