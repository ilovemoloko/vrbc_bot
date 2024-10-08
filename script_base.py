import re
import traceback

from db_worker import fsm_db


class MessageContext:
    def __init__(self, source):
        self.user_id = None
        self.peer_id = None
        self.text = None
        self.attached_photos = []
        self.src = source
        self.fsm = ""
        self.srcobj: BotScript = None
        self.fsm_full = ""
        self.userData = None
        self.rawAction = None

    def setPeerId(self, peerId):
        self.peer_id = peerId
        return self

    def setRawAction(self, obj):
        self.rawAction = obj
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

    def setSrcObject(self, obj):
        self.srcobj = obj

    def setUserData(self, obj):
        self.userData = obj
        return self


class ButtonsBuilder:
    def __init__(self):
        self.buttons = []
        self.peerId = None

    def insert(self, index, text, payload):
        self.buttons.insert(index, {"text": text, "payload": payload})
        return self

    def add(self, text, payload):
        self.buttons.append({"text": text, "payload": payload})
        return self


class MessageBuilder:
    def __init__(self):
        self.peerId = None
        self.text = ""
        self.buttons = None
        self.reply_func = None
        self.previewUrl = None
        self.context = None

    def setPeerId(self, peerId):
        self.peerId = peerId
        return self

    def setText(self, text):
        self.text = text
        return self

    def addText(self, text, start="\n"):
        self.text = self.text + start + text
        return self

    def setButtons(self, buttons: ButtonsBuilder):
        self.buttons = buttons
        return self

    def setReplyMode(self, context: MessageContext):
        self.reply_func = context.srcobj.send_message
        self.context = context
        self.peerId = context.peer_id
        return self

    def reply(self):
        if self.reply_func is not None:
            self.reply_func(self)
        return self

    def setPreviewUrl(self, url):
        self.previewUrl = url


class Mapper:
    def __init__(self, commands):
        self.commands = commands

    def map(self, func, pattern, level="*", weak=False, ignore_case=False, replace_newline=" "):
        if isinstance(pattern, str):
            pattern = [pattern]
        if level not in self.commands:
            self.commands[level] = {}
        for p in pattern:
            p = "^" + p + "$"
            self.commands[level][p] = {"func": func, "weak": weak, "ignore_case": ignore_case, "replace_newline": replace_newline}


class BotScript:
    TRACEBACK = True

    def __init__(self):
        self.commands = {}
        self.mapper = Mapper(self.commands)
        import bot_script
        self.bot_script = bot_script.bot
        for cmd in bot_script.commands:
            level = cmd[0]
            pattern = cmd[1]
            func = cmd[2]
            weak = cmd[3]
            ignore_case = cmd[4]
            replace_newline = cmd[5]
            self.mapper.map(func, pattern, level, weak, ignore_case, replace_newline)

    def send_message(self, message: MessageBuilder):
        pass

    def get_action(self):
        pass

    def get_name(self):
        return "none"

    def check_command(self, fsm_level, action):
        lowercase_text = action.text.lower()
        for pattern in self.commands[fsm_level]:
            check_text = action.text
            if self.commands[fsm_level][pattern]['ignore_case']:
                check_text = lowercase_text

            check_text = check_text.replace("\n", self.commands[fsm_level][pattern]['replace_newline'])
            if re.match(pattern, check_text):
                self.commands[fsm_level][pattern]['func'](action)
                return True
        return False

    def check_weak(self, fsm_level, action):
        lowercase_text = action.text.lower()
        for pattern in self.commands[fsm_level]:
            ignore_case = self.commands[fsm_level][pattern]['ignore_case']
            check_text = action.text
            if ignore_case:
                check_text = lowercase_text
            check_text = check_text.replace("\n", self.commands[fsm_level][pattern]['replace_newline'])
            if re.match(pattern, check_text):
                return self.commands[fsm_level][pattern]['weak']
        return None

    def _get_user_description(self, context: MessageContext):
        return {"name": None, "image_url": None}

    def get_user_description(self, context: MessageContext):
        return context.setUserData(self._get_user_description(context))

    def handle_action(self, action):
        try:
            if not self.bot_script.running:
                return
            if isinstance(action, MessageContext):
                if action.text is None:
                    action.text = ""
                if action.user_id != action.peer_id:
                    return
                fsm_level = fsm_db.get_state(action)
                action.fsm_full = fsm_level
                context = fsm_level.split(" ")[1:]
                fsm_level = fsm_level.split(" ")[0]
                action.setFSM(context)
                action.setSrcObject(self)

                weak = self.check_weak(fsm_level, action)

                if weak is None:
                    self.check_command("*", action)
                    return

                if weak:
                    if self.check_command("*", action):
                        return
                    if self.check_command(fsm_level, action):
                        return

                else:
                    if self.check_command(fsm_level, action):
                        return
                    if self.check_command("*", action):
                        return

        except Exception as e:
            print(f"[{self.get_name()}] {e}")
            if self.TRACEBACK:
                traceback.print_exc()

    def start(self):
        while True:
            self.handle_action(self.get_action())
