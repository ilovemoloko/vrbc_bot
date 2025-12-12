from telebot import types
from db_worker import SingletonMeta, fsm_db
from script_base import MessageBuilder, MessageContext, ButtonsBuilder
import requests
import uuid  # Добавляем для генерации уникальных ID сессий


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
        self.src = None
        self.user_id = None


escape_characters = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

def escape_markdown_v2(text: str) -> str:
    for c in escape_characters:
        text = text.replace(c, f"\\{c}")
    return text


class Modbot(metaclass=SingletonMeta):
    def __init__(self):
        self.user_messages = None
        self.mod_channel_id = None
        self.bot = None
        self.reply_sessions = {}  # Словарь для хранения активных сессий ответов
        self.deposit_sessions = {}  # Словарь для хранения активных сессий пополнения

    def config(self, bot, mod_channel_id):
        self.bot = bot
        self.mod_channel_id = mod_channel_id
        self.user_messages = {}
        self.reply_sessions = {}
        self.deposit_sessions = {}

    def format_message(self, ctx: LittleContext):
        answer: MessageBuilder = ctx.answer
        context: MessageContext = answer.context

        src_context = context.src
        user_id = context.user_id

        ctx.src = src_context
        ctx.user_id = user_id

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
        message = self.format_message(ctx)
        sent_message = self.bot.send_message(
            self.mod_channel_id,
            message,
            parse_mode='MarkdownV2',
            disable_web_page_preview=True
        )

        self.user_messages[sent_message.message_id] = ctx

        markup = types.InlineKeyboardMarkup()
        # Добавляем уникальный идентификатор сессии в callback_data
        session_id = str(uuid.uuid4())
        reply_button = types.InlineKeyboardButton(
            "Ответить",
            callback_data=f"reply_{sent_message.message_id}_{session_id}"
        )
        deposit_button = types.InlineKeyboardButton(
            "Пополнить баланс",
            callback_data=f"deposit_{sent_message.message_id}_{session_id}"
        )
        markup.add(reply_button, deposit_button)

        # Сохраняем связь между session_id и ctx
        self.reply_sessions[session_id] = ctx
        self.deposit_sessions[session_id] = ctx

        self.bot.edit_message_reply_markup(
            self.mod_channel_id,
            sent_message.message_id,
            reply_markup=markup
        )

    def handle_reply(self, call):
        if call.data.startswith("reply_"):
            parts = call.data.split("_")
            message_id = parts[1]
            session_id = parts[2] if len(parts) > 2 else None

            # Получаем контекст либо из user_messages, либо из reply_sessions
            ctx = None
            if session_id and session_id in self.reply_sessions:
                ctx = self.reply_sessions[session_id]
            else:
                ctx = self.user_messages.get(int(message_id))

            if ctx:
                # Генерируем уникальный ID для этой сессии ответа
                unique_session_id = str(uuid.uuid4())
                # Сохраняем контекст для этой конкретной сессии
                self.reply_sessions[unique_session_id] = ctx

                msg = self.bot.send_message(
                    call.message.chat.id,
                    f"Введите ответ для пользователя {ctx.name} (ID сессии: {unique_session_id[-8:]}):"
                )
                # Регистрируем обработчик с уникальным ID сессии
                self.bot.register_next_step_handler(
                    msg,
                    lambda m: self.process_reply(m, unique_session_id)
                )
            else:
                self.bot.answer_callback_query(call.id, "Сообщение не найдено.")

        elif call.data.startswith("deposit_"):
            parts = call.data.split("_")
            message_id = parts[1]
            session_id = parts[2] if len(parts) > 2 else None

            ctx = None
            if session_id and session_id in self.deposit_sessions:
                ctx = self.deposit_sessions[session_id]
            else:
                ctx = self.user_messages.get(int(message_id))

            if ctx:
                unique_session_id = str(uuid.uuid4())
                self.deposit_sessions[unique_session_id] = ctx

                msg = self.bot.send_message(
                    call.message.chat.id,
                    f"Введите сумму для пополнения баланса пользователя {ctx.name} (ID сессии: {unique_session_id[-8:]}):"
                )
                self.bot.register_next_step_handler(
                    msg,
                    lambda m: self.process_deposit(m, unique_session_id)
                )
            else:
                self.bot.answer_callback_query(call.id, "Сообщение не найдено.")

    def process_reply(self, message, session_id):
        """
        Обрабатывает введённый модератором ответ с использованием session_id.
        """
        # Получаем контекст по session_id
        ctx = self.reply_sessions.pop(session_id, None)
        if not ctx:
            self.bot.send_message(message.chat.id, "Сессия ответа не найдена или истекла.")
            return

        reply_text = message.text
        answer: MessageBuilder = ctx.answer
        buttons = ButtonsBuilder()
        answer.setButtons(buttons)
        buttons.add("Написать снова", "letsgo")
        buttons.add("Главное меню", "start")

        if reply_text:
            original_message = f"||{ctx.original_message}||"
            answer.setText(f"Вам пришел ответ от администратора:\n\n{reply_text}").reply()

            # Находим message_id_old в user_messages
            message_id_old = 0
            for mid in list(self.user_messages.keys()):  # Используем list для безопасной итерации
                if self.user_messages[mid] == ctx:
                    message_id_old = mid
                    break

            if message_id_old:
                self.bot.edit_message_text(
                    text=original_message,
                    chat_id=self.mod_channel_id,
                    message_id=message_id_old,
                    parse_mode='MarkdownV2'
                )

                # Удаляем контекст из user_messages
                self.user_messages.pop(message_id_old, None)

                # Очищаем сессии для этого контекста
                self._cleanup_sessions_for_context(ctx)

                self.bot.send_message(
                    self.mod_channel_id,
                    f"Ответ отправлен пользователю {ctx.name}.",
                    reply_to_message_id=message.message_id
                )
                fsm_db.set_brawl_data(ctx.answer.context, -1)
            else:
                self.bot.send_message(message.chat.id, "Не удалось найти исходное сообщение.")
        else:
            answer.setText("Пустой ответ не отправлен.").reply()
            # Возвращаем контекст обратно в сессию для повторной попытки
            self.reply_sessions[session_id] = ctx

    def process_deposit(self, message, session_id):
        """
        Обрабатывает пополнение баланса пользователя с использованием session_id.
        """
        ctx = self.deposit_sessions.pop(session_id, None)
        if not ctx:
            self.bot.send_message(message.chat.id, "Сессия пополнения не найдена или истекла.")
            return

        try:
            amount = float(message.text)
            if amount <= 0:
                self.bot.send_message(message.chat.id, "Сумма должна быть положительным числом.")
                # Возвращаем контекст для повторной попытки
                self.deposit_sessions[session_id] = ctx
                return
        except ValueError:
            self.bot.send_message(message.chat.id, "Пожалуйста, введите корректную сумму (число).")
            self.deposit_sessions[session_id] = ctx
            return

        payload_data = {
            "currency": "RUB",
            "payload": f"{ctx.src}_{ctx.user_id}",
            "amount": amount,
            "type": "payment_success"
        }

        try:
            response = requests.post('http://localhost:8000', json=payload_data)

            if response.status_code == 200:
                self.bot.send_message(
                    message.chat.id,
                    f"Баланс пользователя {ctx.name} успешно пополнен на {amount} RUB."
                )
                # Удаляем контекст из user_messages и сессий
                self._cleanup_context(ctx)
            elif response.text == "-1":
                self.bot.send_message(
                    message.chat.id,
                    "Ошибка при обработке платежа: неверные данные."
                )
                self.deposit_sessions[session_id] = ctx
            else:
                self.bot.send_message(
                    message.chat.id,
                    f"Ошибка при обработке платежа. Статус: {response.status_code}"
                )
                self.deposit_sessions[session_id] = ctx
        except requests.exceptions.ConnectionError:
            self.bot.send_message(
                message.chat.id,
                "Не удалось подключиться к платежному сервису. Попробуйте позже."
            )
            self.deposit_sessions[session_id] = ctx
        except Exception as e:
            self.bot.send_message(
                message.chat.id,
                f"Произошла ошибка: {str(e)}"
            )
            self.deposit_sessions[session_id] = ctx

    def _cleanup_sessions_for_context(self, ctx):
        """Очищает все сессии для указанного контекста."""
        # Очищаем reply_sessions
        sessions_to_remove = []
        for session_id, session_ctx in self.reply_sessions.items():
            if session_ctx == ctx:
                sessions_to_remove.append(session_id)
        for session_id in sessions_to_remove:
            self.reply_sessions.pop(session_id, None)

        # Очищаем deposit_sessions
        sessions_to_remove = []
        for session_id, session_ctx in self.deposit_sessions.items():
            if session_ctx == ctx:
                sessions_to_remove.append(session_id)
        for session_id in sessions_to_remove:
            self.deposit_sessions.pop(session_id, None)

    def _cleanup_context(self, ctx):
        """Полностью очищает контекст из всех хранилищ."""
        # Удаляем из user_messages
        for mid in list(self.user_messages.keys()):
            if self.user_messages[mid] == ctx:
                self.user_messages.pop(mid, None)

        # Очищаем сессии
        self._cleanup_sessions_for_context(ctx)