import re
from functools import wraps


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


class BotScript:
    def __init__(self):
        self.commands = {}

    @staticmethod
    def mapping(regex):
        def decorator(func):
            @wraps(func)
            def wrapped_func(self, *args, **kwargs):
                for pattern in regex:
                    if pattern not in self.commands:
                        self.commands[pattern] = func
                    else:
                        raise ValueError(f"Pattern {pattern} is already in use.")
                return func(self, *args, **kwargs)
            return wrapped_func
        return decorator

    def send_message(self, message: MessageBuilder):
        pass

    @mapping(regex=["тест"])
    def main(self, context: MessageContext):
        peerId = context.peerId
        answer = MessageBuilder().setText("Тестовое сообщение").setPeerId(peerId)
        self.send_message(answer)
