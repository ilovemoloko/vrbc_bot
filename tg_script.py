import script_base as sc
from config import token_tg
from script_base import MessageBuilder, MessageContext
import telebot


class TgBotScript(sc.BotScript):
    def __init__(self):
        super().__init__()
        self.bot = telebot.TeleBot(token_tg)

    def send_message(self, message: MessageBuilder):
        chat_id = message.peerId
        text = message.text
        buttons = message.buttons
        keyboard = None

        if buttons:
            keyboard = telebot.types.InlineKeyboardMarkup()
            for b in buttons.buttons:
                label = b["text"]
                payload = b["payload"]
                keyboard.add(telebot.types.InlineKeyboardButton(label, callback_data=payload))

        self.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

    def _handle_action(self, action):
        res = None
        peer_id = action.chat.id
        user_id = action.from_user.id

        if action.content_type == "text":
            text = action.text
            res = MessageContext(self.get_name()).setPeerId(peer_id).setUserId(user_id).setText(text)
        elif action.content_type == "photo":
            text = action.caption
            photo_url = self.bot.get_file_url(action.photo[-1].file_id)
            res = MessageContext(self.get_name()).setPeerId(peer_id).setUserId(user_id).setText(text).addPhoto(photo_url)

        self.handle_action(res)

    def get_actions(self, actions):
        for action in actions:
            self._handle_action(action)

    def start(self):
        self.bot.set_update_listener(self.get_actions)

        @self.bot.callback_query_handler(func=lambda call: True)
        def query_listener(call):
            user_id = call.from_user.id
            peer_id = call.message.chat.id
            text = call.data
            self.handle_action(MessageContext(self.get_name()).setPeerId(peer_id).setUserId(user_id).setText(text))

        self.bot.polling(none_stop=True)

    def get_name(self):
        return "tg"
