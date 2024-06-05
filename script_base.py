import re
import utils


class MessageContext:
    def __init__(self, source):
        self.userId = None
        self.peerId = None
        self.text = None
        self.attached_photos = []

        self.fsm_level = utils.getFSMLevel(f"{source}{self.userId}")

    def setPeerId(self, peerId):
        self.peerId = peerId
        return self

    def setFSMLevel(self, level):
        self.fsm_level = level
        return self

    def setText(self, text):
        self.text = text
        return self

    def setUserId(self, userId):
        self.userId = userId
        return self

    def addPhoto(self, photo):
        self.attached_photos.append(photo)
        return self


class ButtonsBuilder:
    def __init__(self):
        self.buttons = []
        self.peerId = None

    def add(self, text, payload):
        self.buttons.append({"text": text, "payload": payload})
        return self


class MessageBuilder:
    def __init__(self):
        self.peerId = None
        self.text = None
        self.buttons = None

    def setPeerId(self, peerId):
        self.peerId = peerId
        return self

    def setText(self, text):
        self.text = text
        return self

    def setButtons(self, buttons: ButtonsBuilder):
        self.buttons = buttons
        return self


class Mapper:
    def __init__(self, commands):
        self.commands = commands

    def map(self, pattern, func, level="*"):
        if isinstance(pattern, str):
            pattern = [pattern]
        if level not in self.commands:
            self.commands[level] = {}
        for p in pattern:
            self.commands[level][p] = func


class BotScript:
    def __init__(self):
        self.commands = {}
        self.mapper = Mapper(self.commands)
        self.mapper.map("img", self.get_codes)
        self.mapper.map("test", self.test_message)
        self.mapper.map("payload2", self.testbutton)

    def send_message(self, message: MessageBuilder):
        pass

    def get_action(self):
        pass

    def get_name(self):
        return "none"

    def handle_action(self, action):
        if isinstance(action, MessageContext):
            fsm_level = action.fsm_level
            for pattern in self.commands[fsm_level]:
                if re.match(pattern, action.text):
                    self.commands[fsm_level][pattern](action)
                    break

    def start(self):
        while True:
            try:
                self.handle_action(self.get_action())
            except Exception as e:
                print(f"[{self.get_name()}] {e}")
                continue

    def test_message(self, context: MessageContext):
        peerId = context.peerId
        buttons = ButtonsBuilder().add("Кнопка 1", "payload1").add("Тест кнопки", "payload2")
        answer = MessageBuilder().setText("Тестовое сообщение").setPeerId(peerId).setButtons(buttons)
        self.send_message(answer)

    def testbutton(self, context: MessageContext):
        peerId = context.peerId
        answer = MessageBuilder().setText("Тестовое сообщение с нажатия кнопки").setPeerId(peerId)
        self.send_message(answer)

    def get_codes(self, context: MessageContext):
        peerId = context.peerId
        attachments = context.attached_photos
        if len(attachments) == 0:
            answer = MessageBuilder().setText("Не нашлось картинок").setPeerId(peerId)
        else:
            url = attachments[0]
            image = utils.get_image(url)
            image = image.crop((235, 130, 235+135, 130+30))
            res = utils.getText(image)
            res = utils.extract_codes(res)
            res = f"Ваши коды: {res}"
            answer = MessageBuilder().setPeerId(peerId).setText(res)

        self.send_message(answer)
