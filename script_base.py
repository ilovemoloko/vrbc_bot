import re
import traceback
import utils

from db_worker import fsm_db, localuser_db


class MessageContext:
    def __init__(self, source):
        self.user_id = None
        self.peer_id = None
        self.text = None
        self.attached_photos = []
        self.src = source
        self.fsm = ""

    def setPeerId(self, peerId):
        self.peer_id = peerId
        return self

    def setText(self, text):
        self.text = text
        return self

    def setUserId(self, userId):
        self.user_id = userId
        return self

    def addPhoto(self, photo):
        self.attached_photos.append(photo)
        return self

    def setFSM(self, fsm):
        self.fsm = fsm


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

    def map(self, func, pattern, level="*"):
        if isinstance(pattern, str):
            pattern = [pattern]
        if level not in self.commands:
            self.commands[level] = {}
        for p in pattern:
            p = "^" + p + "$"
            self.commands[level][p] = func

    def command(self, func):
        def wrapper(*args, **kwargs):
            self.map(func, *args, **kwargs)
        return wrapper


class BotScript:
    def __init__(self):
        self.commands = {}
        self.mapper = Mapper(self.commands)
        import bot_script
        for cmd in bot_script.commands:
            level = cmd[0]
            pattern = cmd[1]
            func = cmd[2]
            self.mapper.map(func, pattern, level)

    def send_message(self, message: MessageBuilder):
        pass

    def get_action(self):
        pass

    def get_name(self):
        return "none"

    def handle_action(self, action):
        if isinstance(action, MessageContext):
            if action.text is None:
                action.text = ""
            fsm_level = fsm_db.get_state(action)
            context = fsm_level.split(" ")[1:]
            fsm_level = fsm_level.split(" ")[0]
            action.setFSM(context)
            for pattern in self.commands[fsm_level]:
                if re.match(pattern, action.text):
                    self.commands[fsm_level][pattern](self, action)
                    return
            for pattern in self.commands["*"]:
                if re.match(pattern, action.text):
                    self.commands["*"][pattern](action)
                    return

    def start(self):
        while True:
            try:
                self.handle_action(self.get_action())
            except Exception as e:
                print(f"[{self.get_name()}] {e}")
                traceback.print_exc()
                continue
