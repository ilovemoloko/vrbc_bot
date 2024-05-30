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


class MessageBuilder:
    def __init__(self):
        self.peerId = None
        self.text = None

    def setPeerId(self, peerId):
        self.peerId = peerId
        return self

    def setText(self, text):
        self.text = text
        return self


class Mapper:
    def __init__(self, commands):
        self.commands = commands

    def map(self, pattern, func):
        self.commands[pattern] = func


class BotScript:
    def __init__(self):
        self.commands = {}
        self.mapper = Mapper(self.commands)
        self.mapper.map("тест", self.test_message)

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
        answer = MessageBuilder().setText("Тестовое сообщение").setPeerId(peerId)
        self.send_message(answer)
