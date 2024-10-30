import time

import script_base as sc
from config import token_tg
from script_base import MessageBuilder, MessageContext
import telebot


class TgBotScript(sc.BotScript):
    def __init__(self):
        super().__init__()
        self.started_sent = {}
        self.start_time = None
        self.bot = telebot.TeleBot(token_tg)

    def _send_message(self, message: MessageBuilder):
        chat_id = message.peerId
        text = message.text
        buttons = message.buttons
        keyboard = None
        url_preview = None
        if message.previewUrl:
            url_preview = message.previewUrl

        if buttons:
            keyboard = telebot.types.InlineKeyboardMarkup()
            for b in buttons.buttons:
                label = b["text"]
                payload = b["payload"]
                keyboard.add(telebot.types.InlineKeyboardButton(label, callback_data=payload))
        if url_preview:
            return self.bot.send_photo(chat_id=chat_id, caption=text, reply_markup=keyboard, photo=url_preview[1])
        self.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

    def handle_action(self, action):
        message = action.rawAction
        peer_id = message.chat.id
        time_now = time.time()
        call_time = message.date

        if time_now - self.start_time < 10:
            if call_time - self.start_time < 0:
                if peer_id in self.started_sent:
                    if time_now - self.started_sent[peer_id] < 2:
                        return
                else:
                    self.started_sent[peer_id] = time_now
                    return self.bot.send_message(peer_id, "Бот перезапущен. Вы можете попробовать снова.")

        super().handle_action(action)

    def _handle_action(self, action):
        peer_id = action.chat.id
        user_id = action.from_user.id

        res = MessageContext(self.get_name()).setPeerId(peer_id).setUserId(user_id).setRawAction(action)

        if action.content_type == "text":
            text = action.text
            res.setText(text)
        elif action.content_type == "photo":
            text = action.caption
            photo_url = self.bot.get_file_url(action.photo[-1].file_id)
            res.setText(text).addPhoto(photo_url)

        self.handle_action(res)

    def get_actions(self, actions):
        for action in actions:
            self._handle_action(action)

    def _get_user_description(self, context: MessageContext):
        userdata = self.bot.get_chat(context.user_id)

        first_name = userdata.first_name or ""
        last_name = userdata.last_name or ""
        username = userdata.username or ""

        user_name = " ".join(filter(None, [first_name, last_name, f"(@{username})"]))
        try:
            photo_url = self.bot.get_file_url(userdata.photo.small_file_id)
        except:
            photo_url = None

        return {"name": user_name, "image_url": photo_url}

    def start(self):
        self.bot.set_update_listener(self.get_actions)
        self.start_time = time.time()
        self.started_sent = {}

        @self.bot.callback_query_handler(func=lambda call: True)
        def query_listener(call):
            user_id = call.from_user.id
            peer_id = call.message.chat.id
            text = call.data

            self.handle_action(MessageContext(self.get_name()).setPeerId(peer_id)
                               .setUserId(user_id).setText(text).setRawAction(call.message))

        while True:
            print("tg polling...")
            try:
                self.bot.polling(none_stop=True)
            except Exception as e:
                print(e)

    def get_name(self):
        return "tg"
