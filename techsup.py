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

        self.sent_message_id = None


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

    def _normalize_chat_id(self, cid):
        """
        Попытка привести переданный мод-чат к int если это возможно.
        Если это строка вида "@name" — возвращаем строку, иначе int.
        """
        if cid is None:
            return cid
        # если уже int — вернуть
        if isinstance(cid, int):
            return cid
        # попытка привести к int (поддержит "-100123..." и т.д.)
        try:
            return int(cid)
        except Exception:
            return cid

    def config(self, bot, mod_channel_id):
        self.bot = bot
        # сохраняем нормализованный мод-чат
        self.mod_channel_id = self._normalize_chat_id(mod_channel_id)
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

        # Тело сообщения
        escaped_text = escape_markdown_v2(ctx.text)
        formatted_message = (
            f"_Сообщение_\n"
            f"```\n{escaped_text}\n```"
        )

        # Заголовок
        header = (
            f"Пользователь: {ctx.name}\n"
            f"LOCAL_ID: {ctx.local_uid}\n"
            f"Src Id: {src_context} {user_id}\n"
        )

        if ctx.attachments:
            header += f"Вложения: {', '.join(ctx.attachments)}\n"

        header = escape_markdown_v2(header)

        formatted_message += f"\n\n{header}"

        ctx.original_message = formatted_message
        return formatted_message


    def handle_message(self, ctx):
        message = self.format_message(ctx)
        # используем именованные аргументы для стабильности с разными типами chat_id
        sent_message = self.bot.send_message(
            chat_id=self.mod_channel_id,
            text=message,
            parse_mode='MarkdownV2',
            disable_web_page_preview=True
        )
        ctx.sent_message_id = sent_message.message_id

        # ключ — message_id (как раньше)
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

        # используем именованные аргументы при редактировании разметки
        try:
            self.bot.edit_message_reply_markup(
                chat_id=self.mod_channel_id,
                message_id=sent_message.message_id,
                reply_markup=markup
            )
        except Exception:
            # на некоторых версиях/ситуациях можно просто игнорировать ошибку редактирования разметки
            pass

    def _parse_callback(self, data: str):
        """
        Безопасно разбирает callback_data вида:
        reply_<message_id>_<session_id>
        deposit_<message_id>_<session_id>
        Использует maxsplit=2 чтобы session_id (UUID с дефисами) не ломал разбор.
        Возвращает (action, message_id_or_None(int), session_id_or_None(str))
        """
        parts = data.split("_", 2)
        action = parts[0] if len(parts) > 0 else None
        message_id = None
        session_id = None
        if len(parts) > 1:
            try:
                message_id = int(parts[1])
            except Exception:
                message_id = None
        if len(parts) > 2:
            session_id = parts[2]
        return action, message_id, session_id

    def handle_reply(self, call):
        action, message_id, session_id = self._parse_callback(call.data)

        if action == "reply":
            # Получаем контекст либо из reply_sessions, либо из user_messages по message_id
            ctx = None
            if session_id and session_id in self.reply_sessions:
                ctx = self.reply_sessions[session_id]
            else:
                if message_id is not None:
                    ctx = self.user_messages.get(message_id)

            if ctx:
                # Генерируем уникальный ID для этой сессии ответа
                unique_session_id = str(uuid.uuid4())
                # Сохраняем контекст для этой конкретной сессии
                self.reply_sessions[unique_session_id] = ctx

                # Формируем текст подсказки и добавляем в конец оригинального модерационного сообщения
                prompt = f"Введите ответ для пользователя {ctx.name}"
                # ctx.original_message уже содержит escaped текст (используется при отправке в handle_message)
                new_text = ctx.original_message + "\n\n" + escape_markdown_v2(prompt)

                # Пытаемся отредактировать оригинальное модерационное сообщение (чтобы туда добавилась подсказка)
                try:
                    # используем ctx.sent_message_id (тот же message, что и в user_messages)
                    if ctx.sent_message_id:
                        self.bot.edit_message_text(
                            chat_id=self.mod_channel_id,
                            message_id=ctx.sent_message_id,
                            text=new_text,
                            parse_mode='MarkdownV2',
                            disable_web_page_preview=True
                        )
                    else:
                        # fallback: если по какой-то причине sent_message_id нет — редактируем call.message
                        self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=new_text,
                            parse_mode='MarkdownV2',
                            disable_web_page_preview=True
                        )
                except Exception:
                    # не ломаем логику на ошибке редактирования — уведомим модератора в чате
                    try:
                        self.bot.send_message(chat_id=call.message.chat.id,
                                              text="Не удалось добавить подсказку в оригинальное сообщение. Введите ответ в чат.")
                    except Exception:
                        pass

                # Регистрируем обработчик следующего сообщения модератора, используя call.message (существующее сообщение)
                # Так нам не нужно создавать новое сообщение-промпт видимое в чате
                self.bot.register_next_step_handler(
                    call.message,
                    lambda m: self.process_reply(m, unique_session_id, call.message)
                )
            else:
                self.bot.answer_callback_query(call.id, "Сообщение не найдено.")

        if action == "deposit":
            ctx = None
            if session_id and session_id in self.deposit_sessions:
                ctx = self.deposit_sessions[session_id]
            else:
                if message_id is not None:
                    ctx = self.user_messages.get(message_id)

            if ctx:
                unique_session_id = str(uuid.uuid4())
                self.deposit_sessions[unique_session_id] = ctx

                # Формируем подсказку и добавляем её в конец оригинального модерационного сообщения
                prompt = f"Введите сумму для пополнения баланса пользователя {ctx.name}"
                new_text = ctx.original_message + "\n\n" + escape_markdown_v2(prompt)

                try:
                    if ctx.sent_message_id:
                        self.bot.edit_message_text(
                            chat_id=self.mod_channel_id,
                            message_id=ctx.sent_message_id,
                            text=new_text,
                            parse_mode='MarkdownV2',
                            disable_web_page_preview=True
                        )
                    else:
                        self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=new_text,
                            parse_mode='MarkdownV2',
                            disable_web_page_preview=True
                        )
                except Exception:
                    try:
                        self.bot.send_message(chat_id=call.message.chat.id,
                                              text="Не удалось добавить подсказку в оригинальное сообщение. Введите сумму в чат.")
                    except Exception:
                        pass

                # Регистрируем обработчик следующего сообщения модератора
                self.bot.register_next_step_handler(
                    call.message,
                    lambda m: self.process_deposit(m, unique_session_id, call.message)
                )
            else:
                self.bot.answer_callback_query(call.id, "Сообщение не найдено.")


    def process_reply(self, message, session_id, anchor):
        """
        Обрабатывает введённый модератором ответ с использованием session_id.
        """
        # Получаем контекст по session_id

        reply_message_id = message.reply_to_message.message_id
        selected_message_id = self.reply_sessions[session_id].sent_message_id

        if reply_message_id != selected_message_id:
            return self.bot.register_next_step_handler(
                anchor,
                lambda m: self.process_reply(m, session_id, anchor)
            )


        ctx = self.reply_sessions.pop(session_id, None)
        if not ctx:
            self.bot.send_message(chat_id=message.chat.id, text="Сессия ответа не найдена или истекла.")
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
                try:
                    self.bot.edit_message_text(
                        text=original_message,
                        chat_id=self.mod_channel_id,
                        message_id=message_id_old,
                        parse_mode='MarkdownV2'
                    )
                except Exception:
                    # если редактирование не удалось — не ломаем логику; просто уведомим модератора
                    self.bot.send_message(
                        chat_id=message.chat.id,
                        text="Не удалось обновить сообщение модерационной панели (редактирование)."
                    )

                # Удаляем контекст из user_messages
                self.user_messages.pop(message_id_old, None)

                # Очищаем сессии для этого контекста
                self._cleanup_sessions_for_context(ctx)

                self.bot.send_message(
                    chat_id=self.mod_channel_id,
                    text=f"Ответ отправлен пользователю {ctx.name}.",
                    reply_to_message_id=message.message_id
                )
                fsm_db.set_brawl_data(ctx.answer.context, -1)
            else:
                self.bot.send_message(chat_id=message.chat.id, text="Не удалось найти исходное сообщение.")
        else:
            answer.setText("Пустой ответ не отправлен.").reply()
            # Возвращаем контекст обратно в сессию для повторной попытки
            self.reply_sessions[session_id] = ctx

    def process_deposit(self, message, session_id, anchor):
        """
        Обрабатывает пополнение баланса пользователя с использованием session_id.
        """

        reply_message_id = message.reply_to_message.message_id
        selected_message_id = self.reply_sessions[session_id].sent_message_id

        if reply_message_id != selected_message_id:
            return self.bot.register_next_step_handler(
                anchor,
                lambda m: self.process_reply(m, session_id, anchor)
            )

        ctx = self.deposit_sessions.pop(session_id, None)
        if not ctx:
            self.bot.send_message(chat_id=message.chat.id, text="Сессия пополнения не найдена или истекла.")
            return

        try:
            amount = float(message.text)
            if amount <= 0:
                self.bot.send_message(chat_id=message.chat.id, text="Сумма должна быть положительным числом.")
                # Возвращаем контекст для повторной попытки
                self.deposit_sessions[session_id] = ctx
                return
        except ValueError:
            self.bot.send_message(chat_id=message.chat.id, text="Пожалуйста, введите корректную сумму (число).")
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
                # Находим message_id_old в user_messages
                message_id_old = 0
                for mid in list(self.user_messages.keys()):
                    if self.user_messages[mid] == ctx:
                        message_id_old = mid
                        break

                if message_id_old:
                    # Формируем обновленное сообщение с пометкой о пополнении
                    deposit_message = f"||{ctx.original_message}||"
                    try:
                        self.bot.edit_message_text(
                            text=deposit_message,
                            chat_id=self.mod_channel_id,
                            message_id=message_id_old,
                            parse_mode='MarkdownV2'
                        )
                    except Exception:
                        # если редактирование не удалось — просто уведомим
                        self.bot.send_message(
                            chat_id=message.chat.id,
                            text="Не удалось обновить сообщение модерационной панели (редактирование)."
                        )

                    # Удаляем контекст из user_messages
                    self.user_messages.pop(message_id_old, None)

                # Очищаем сессии для этого контекста
                self._cleanup_sessions_for_context(ctx)

                self.bot.send_message(
                    chat_id=self.mod_channel_id,
                    text=f"Баланс пользователя {ctx.name} пополнен на {amount} RUB.",
                    reply_to_message_id=message.message_id
                )
                fsm_db.set_brawl_data(ctx.answer.context, -1)

            elif response.text == "-1":
                self.bot.send_message(
                    chat_id=message.chat.id,
                    text="Ошибка при обработке платежа: неверные данные."
                )
                self.deposit_sessions[session_id] = ctx
            else:
                self.bot.send_message(
                    chat_id=message.chat.id,
                    text=f"Ошибка при обработке платежа. Статус: {response.status_code}"
                )
                self.deposit_sessions[session_id] = ctx
        except requests.exceptions.ConnectionError:
            self.bot.send_message(
                chat_id=message.chat.id,
                text="Не удалось подключиться к платежному сервису. Попробуйте позже."
            )
            self.deposit_sessions[session_id] = ctx
        except Exception as e:
            self.bot.send_message(
                chat_id=message.chat.id,
                text=f"Произошла ошибка: {str(e)}"
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
