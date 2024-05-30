import script_base as sc
from config import token_tg
from script_base import MessageBuilder, MessageContext
import telebot


def test(action):
    print(action)


class TgBotScript(sc.BotScript):
    def __init__(self):
        super().__init__()
        self.bot = telebot.TeleBot(token_tg)

    def send_message(self, message: MessageBuilder):
        chat_id = message.peerId
        text = message.text
        self.bot.send_message(chat_id=chat_id, text=text)

    def _handle_action(self, action):
        res = None
        if action.content_type == "text":
            peer_id = action.chat.id
            user_id = action.from_user.id
            text = action.text
            res = MessageContext().setPeerId(peer_id).setUserId(user_id).setText(text)
        self.handle_action(res)

    def get_actions(self, actions):
        for action in actions:
            self._handle_action(action)

    def start(self):
        self.bot.set_update_listener(self.get_actions)
        self.bot.polling(none_stop=True)

    def get_name(self):
        return "TgScript"


a = TgBotScript()
a.start()
