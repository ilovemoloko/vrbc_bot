from telebot import types
from db_worker import SingletonMeta, fsm_db
from script_base import MessageBuilder, MessageContext, ButtonsBuilder


class LittleContext:
    def __init__(self, chat_id, text, name, local_uid, photo_url, attachments, answer):
        self.chat_id = chat_id
        self.text = text
        self.name = name
        self.local_uid = local_uid
        self.photo_url = photo_url
        self.attachments = attachments
        self.answer: MessageBuilder = answer
        self.original_message = ""


def escape_markdown_v2(text: str) -> str:
    return (text.replace("(", "\\(")
            .replace(")", "\\)")
            .replace("_", "\\_")
            .replace("*", "\\*")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("|", "\\|")
            .replace(">", "\\>")
            .replace("<", "\\<")
            .replace("~", "\\~")
            .replace("`", "\\`"))


class Modbot(metaclass=SingletonMeta):
    def __init__(self):
        self.user_messages = None
        self.mod_channel_id = None
        self.bot = None

    def config(self, bot, mod_channel_id):
        self.bot = bot
        self.mod_channel_id = mod_channel_id
        self.user_messages = {}  # Для отслеживания сообщений пользователей

    def format_message(self, ctx: LittleContext):
        """
        Форматирует сообщение пользователя для отправки в канал модераторов.
        """
        answer: MessageBuilder = ctx.answer
        context: MessageContext = answer.context

        src_context = context.src
        user_id = context.user_id

        formatted_message = (
            f"Пользователь: {ctx.name}\n"
            f"LOCAL_ID: {ctx.local_uid}\n"
            f"Src Id: {src_context} {user_id}\n"
        )

        if ctx.attachments:
            formatted_message += f"Вложения: {', '.join(ctx.attachments)}\n"
        formatted_message = escape_markdown_v2(formatted_message)

        escaped_text = escape_markdown_v2(ctx.text)
        formatted_message += f"\n\n_Сообщение_"
        formatted_message += f"\n```\n{escaped_text}\n```"
        ctx.original_message = formatted_message
        return formatted_message

    def handle_message(self, ctx):
        """
        Обрабатывает входящие пользовательские сообщения и пересылает их в канал модераторов.
        """
        # Форматирование и отправка сообщения модераторам
        message = self.format_message(ctx)
        sent_message = self.bot.send_message(
            self.mod_channel_id,
            message,
            parse_mode='MarkdownV2',
            disable_web_page_preview=True
        )

        # Сохранение сообщения для отслеживания ответов
        self.user_messages[sent_message.message_id] = ctx

        # Добавление inline-кнопок для команд модераторов
        markup = types.InlineKeyboardMarkup()
        reply_button = types.InlineKeyboardButton("Ответить", callback_data=f"reply_{sent_message.message_id}")
        unban_button = types.InlineKeyboardButton("Разбанить", callback_data=f"unban_{ctx.local_uid}")
        markup.add(reply_button, unban_button)
        self.bot.edit_message_reply_markup(
            self.mod_channel_id,
            sent_message.message_id,
            reply_markup=markup
        )

    def handle_reply(self, call):
        """
        Обрабатывает ответы модераторов и пересылает их пользователю.
        """
        if call.data.startswith("reply_"):
            message_id = call.data.split("_")[1]
            ctx = self.user_messages.get(int(message_id))
            if ctx:
                # Отправка запроса на ввод ответа
                msg = self.bot.send_message(call.message.chat.id, f"Введите ответ для пользователя {ctx.name}:")
                self.bot.register_next_step_handler(msg, self.process_reply, ctx)
            else:
                self.bot.answer_callback_query(call.id, "Сообщение не найдено.")
        elif call.data.startswith("unban_"):
            local_uid = call.data.split("_")[1]
            self.unban_user(local_uid)
            self.bot.answer_callback_query(call.id, "Пользователь разбанен!")

    def process_reply(self, message, ctx: LittleContext):
        """
        Обрабатывает введённый модератором ответ и отправляет его пользователю.
        """
        reply_text = message.text
        answer: MessageBuilder = ctx.answer
        buttons = ButtonsBuilder()
        answer.setButtons(buttons)
        buttons.add("Написать снова", "letsgo")
        buttons.add("Главное меню", "first_msg")
        if reply_text:
            # Скрываем исходное сообщение в спойлере
            original_message = f"||{ctx.original_message}||"
            answer.setText(f"Вам пришел ответ от администратора:\n\n{reply_text}").reply()
            message_id_old = 0
            for mid in self.user_messages:
                if self.user_messages[mid] == ctx:
                    message_id_old = mid
                    break
            self.bot.edit_message_text(
                text=original_message,
                chat_id=self.mod_channel_id,
                message_id=message_id_old,
                parse_mode='MarkdownV2'
            )
            self.bot.send_message(
                self.mod_channel_id,
                f"Ответ отправлен пользователю {ctx.name}.",
                reply_to_message_id=message.message_id
            )
            fsm_db.set_brawl_data(ctx.answer.context, -1)
            # Удаление контекста после отправки ответа
            self.user_messages.pop(message.message_id, None)
        else:
            answer.setText("Пустой ответ не отправлен.").reply()

    def unban_user(self, local_uid):
        """
        Разбанивает пользователя по его локальному ID.
        """
        # Реализуйте логику разбана здесь (например, обновление базы данных)
        print(f"Пользователь с ID {local_uid} разбанен.")
