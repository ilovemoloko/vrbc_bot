import re


class MessageContext:
    def __init__(self):
        self.userId = None
        self.peerId = None
        self.text = None

    def setPeerId(self, peerId):
        self.peerId = peerId
        return self

    def setText(self, text):
        self.text = text
        return self

    def setUserId(self, userId):
        self.userId = userId
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

    def map(self, pattern, func):
        if isinstance(pattern, str):
            pattern = [pattern]
        for p in pattern:
            self.commands[p] = func


class BotScript:
    def __init__(self):
        self.commands = {}
        self.mapper = Mapper(self.commands)

    def send_message(self, message: MessageBuilder):
        pass

    def get_action(self):
        pass

    def get_name(self):
        return "BaseScript"

    def handle_action(self, action):
        if isinstance(action, MessageContext):
            for pattern in self.commands:
                if re.match(pattern, action.text):
                    self.commands[pattern](action)
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
