from telebot import types
from db_worker import SingletonMeta, fsm_db
from script_base import MessageBuilder, MessageContext, ButtonsBuilder
import config
import requests
import uuid
import io
import re


class LittleContext:
    def __init__(self, chat_id, text, name, local_uid, photo_url, attachments, answer):
        self.chat_id = chat_id
        self.text = text
        self.name = name
        self.local_uid = local_uid
        self.photo_url = photo_url
        self.attachments = attachments or []
        self.answer: MessageBuilder = answer
        self.original_message = ""
        self.src = None
        self.user_id = None

        self.sent_message_id = None


# Символы, которые нужно экранировать для MarkdownV2
escape_characters = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']


def escape_markdown_v2(text: str) -> str:
    if not isinstance(text, str):
        return text
    # Экранируем обратный слеш первым (чтобы не ломать уже экранированные символы)
    text = text.replace('\\', '\\\\')
    for c in escape_characters:
        text = text.replace(c, f"\\{c}")
    return text


class Modbot(metaclass=SingletonMeta):
    def __init__(self):
        self.user_messages = {}
        self.mod_channel_id = None
        self.bot = None
        self.reply_sessions = {}  # session_id -> ctx
        self.deposit_sessions = {}  # session_id -> ctx

    def _normalize_chat_id(self, cid):
        if cid is None:
            return cid
        if isinstance(cid, int):
            return cid
        try:
            return int(cid)
        except Exception:
            return cid

    def config(self, bot, mod_channel_id):
        self.bot = bot
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

        formatted_message = ""
        if ctx.text:
            escaped_text = escape_markdown_v2(ctx.text)
            # Используем тройные бектики внутри MarkdownV2 — они не интерпретируются как codefence,
            # поэтому оставляем как есть, но экранируем символы внутри.
            formatted_message = (
                f"_Сообщение_\n"
                f"```\n{escaped_text}\n```"
            )

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

    def _is_image_url(self, url: str) -> bool:
        if not isinstance(url, str):
            return False
        return bool(re.search(r"\.(jpe?g|png|webp|gif)(?:[?#].*)?$", url, re.I))

    def _download_image_bytes(self, url: str, timeout: int = 10):
        try:
            resp = requests.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()
            content_type = resp.headers.get('Content-Type', '')
            # допускать и по заголовку, и по расширению
            if not content_type.startswith('image') and not self._is_image_url(url):
                return None
            b = io.BytesIO(resp.content)
            fname = (url.split('/')[-1].split('?')[0]) or 'image.jpg'
            if not re.search(r"\.(jpe?g|png|webp|gif)$", fname, re.I):
                if 'jpeg' in content_type:
                    fname += '.jpg'
                elif 'png' in content_type:
                    fname += '.png'
                else:
                    fname += '.jpg'
            b.name = fname
            b.seek(0)
            return b
        except Exception:
            return None

    def handle_message(self, ctx: LittleContext):
        """
        Отправляем изображение (первое вложение) отдельно, затем отправляем полноценный текст
        с parse_mode='MarkdownV2' (без сокращений). Кнопки прикрепляем к текстовому сообщению.
        """
        message = self.format_message(ctx)

        sent_text_message = None

        # Попытка отправить изображение (если есть)
        if ctx.attachments and len(ctx.attachments) > 0:
            first = ctx.attachments[0]
            # Попробуем сначала дать Telegram скачать по URL (если это публичный URL)
            if isinstance(first, str):
                try:
                    # Не указываем parse_mode и не используем длинный caption
                    self.bot.send_photo(
                        chat_id=self.mod_channel_id,
                        photo=first,
                        caption=f"Вложение от пользователя {ctx.name}"
                    )
                except Exception:
                    # fallback: скачиваем и отправляем вручную
                    img_bytes = self._download_image_bytes(first)
                    if img_bytes:
                        try:
                            # Отправляем как photo; если хотим оригинал без сжатия, заменить на send_document
                            self.bot.send_photo(
                                chat_id=self.mod_channel_id,
                                photo=img_bytes,
                                caption=f"Вложение от пользователя {ctx.name}"
                            )
                        except Exception:
                            try:
                                img_bytes.seek(0)
                                self.bot.send_document(
                                    chat_id=self.mod_channel_id,
                                    data=img_bytes,
                                    caption=f"Вложение от пользователя {ctx.name}"
                                )
                            except Exception:
                                # если и это упало — просто продолжаем, главное — не ломать основную логику
                                pass

        # Теперь отправляем полноценный текст отдельно с MarkdownV2 — на нём будут кнопки
        try:
            sent_text_message = self.bot.send_message(
                chat_id=self.mod_channel_id,
                text=ctx.original_message,
                parse_mode='MarkdownV2',
                disable_web_page_preview=True
            )
        except Exception:
            # Если MarkdownV2 по какой-то причине ломается — отправим без парсинга (в крайнем случае)
            try:
                sent_text_message = self.bot.send_message(
                    chat_id=self.mod_channel_id,
                    text=ctx.original_message,
                    disable_web_page_preview=True
                )
            except Exception:
                # Ничего не делаем — чтобы не падать
                return

        # Сохраняем sent_message_id и регистрацию
        ctx.sent_message_id = sent_text_message.message_id
        self.user_messages[sent_text_message.message_id] = ctx

        # Inline-кнопки — привязываем к текстовому сообщению
        markup = types.InlineKeyboardMarkup()
        session_id = str(uuid.uuid4())
        reply_button = types.InlineKeyboardButton(
            "Ответить",
            callback_data=f"reply_{sent_text_message.message_id}_{session_id}"
        )
        deposit_button = types.InlineKeyboardButton(
            "Пополнить баланс",
            callback_data=f"deposit_{sent_text_message.message_id}_{session_id}"
        )
        markup.add(reply_button, deposit_button)

        self.reply_sessions[session_id] = ctx
        self.deposit_sessions[session_id] = ctx

        try:
            self.bot.edit_message_reply_markup(
                chat_id=self.mod_channel_id,
                message_id=sent_text_message.message_id,
                reply_markup=markup
            )
        except Exception:
            # Игнорируем — иногда телеграм не позволяет редактировать
            pass

    def _parse_callback(self, data: str):
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
            ctx = None
            if session_id and session_id in self.reply_sessions:
                ctx = self.reply_sessions[session_id]
            else:
                if message_id is not None:
                    ctx = self.user_messages.get(message_id)

            if not ctx:
                self.bot.answer_callback_query(call.id, "Сообщение не найдено.")
                return

            # Создаём новую уникальную сессию для реального ввода и сохраняем контекст
            unique_session_id = str(uuid.uuid4())
            self.reply_sessions[unique_session_id] = ctx

            # Просим модератора ввести ответ (мы не требуем reply_to — используем register_next_step_handler)
            prompt = f"Введите ответ для пользователя {ctx.name}"
            try:
                # Добавим подсказку в исходное сообщение (не критично — если нельзя редактировать, игнорируем)
                if ctx.sent_message_id:
                    self.bot.edit_message_text(
                        chat_id=self.mod_channel_id,
                        message_id=ctx.sent_message_id,
                        text=ctx.original_message + "\n\n" + escape_markdown_v2(prompt),
                        parse_mode='MarkdownV2',
                        disable_web_page_preview=True
                    )
            except Exception:
                try:
                    self.bot.send_message(chat_id=call.message.chat.id,
                                          text="Не удалось добавить подсказку в оригинальное сообщение. Введите ответ в чат.")
                except Exception:
                    pass

            # Регистрируем next step handler
            self.bot.register_next_step_handler(
                call.message,
                lambda m: self.process_reply(m, unique_session_id, call.message)
            )

        elif action == "deposit":
            ctx = None
            if session_id and session_id in self.deposit_sessions:
                ctx = self.deposit_sessions[session_id]
            else:
                if message_id is not None:
                    ctx = self.user_messages.get(message_id)

            if not ctx:
                self.bot.answer_callback_query(call.id, "Сообщение не найдено.")
                return

            unique_session_id = str(uuid.uuid4())
            self.deposit_sessions[unique_session_id] = ctx

            prompt = f"Введите сумму для пополнения баланса пользователя {ctx.name}"
            try:
                if ctx.sent_message_id:
                    self.bot.edit_message_text(
                        chat_id=self.mod_channel_id,
                        message_id=ctx.sent_message_id,
                        text=ctx.original_message + "\n\n" + escape_markdown_v2(prompt),
                        parse_mode='MarkdownV2',
                        disable_web_page_preview=True
                    )
            except Exception:
                try:
                    self.bot.send_message(chat_id=call.message.chat.id,
                                          text="Не удалось добавить подсказку в оригинальное сообщение. Введите сумму в чат.")
                except Exception:
                    pass

            self.bot.register_next_step_handler(
                call.message,
                lambda m: self.process_deposit(m, unique_session_id, call.message)
            )

    def process_reply(self, message, session_id, anchor):
        # Получаем контекст и удаляем сессию
        ctx = self.reply_sessions.pop(session_id, None)
        if not ctx:
            try:
                self.bot.send_message(chat_id=message.chat.id, text="Сессия ответа не найдена или истекла.")
            except Exception:
                pass
            return

        reply_text = message.text
        if not reply_text:
            try:
                self.bot.send_message(chat_id=message.chat.id, text="Пустой ответ не отправлен.")
            except Exception:
                pass
            # можно восстановить сессию, если нужно
            self.reply_sessions[session_id] = ctx
            return

        # Отправляем ответ пользователю (через MessageBuilder)
        answer: MessageBuilder = ctx.answer
        buttons = ButtonsBuilder()
        answer.setButtons(buttons)
        buttons.add("Написать снова", "letsgo")
        buttons.add("Главное меню", "start")

        original_message = f"||{ctx.original_message}||"
        answer.setText(f"Вам пришел ответ от администратора:\n\n{reply_text}").reply()

        # Найдём и удалим модерационное сообщение
        message_id_old = None
        for mid, stored_ctx in list(self.user_messages.items()):
            if stored_ctx == ctx:
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
                try:
                    self.bot.send_message(chat_id=message.chat.id,
                                          text="Не удалось обновить сообщение модерационной панели (редактирование).")
                except Exception:
                    pass

            # удаляем контекст
            self.user_messages.pop(message_id_old, None)

            # чистим все сессии для этого контекста
            self._cleanup_sessions_for_context(ctx)

            try:
                self.bot.send_message(
                    chat_id=self.mod_channel_id,
                    text=f"Ответ отправлен пользователю {ctx.name}.",
                    reply_to_message_id=message.message_id
                )
            except Exception:
                pass

            fsm_db.set_brawl_data(ctx.answer.context, -1)
        else:
            try:
                self.bot.send_message(chat_id=message.chat.id, text="Не удалось найти исходное сообщение.")
            except Exception:
                pass

    def process_deposit(self, message, session_id, anchor):
        ctx = self.deposit_sessions.pop(session_id, None)
        if not ctx:
            try:
                self.bot.send_message(chat_id=message.chat.id, text="Сессия пополнения не найдена или истекла.")
            except Exception:
                pass
            return

        try:
            amount = float(message.text)
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
            response = requests.post(config.PUBLIC_SERVER_URL, json=payload_data)

            if response.status_code == 200:
                message_id_old = None
                for mid, stored_ctx in list(self.user_messages.items()):
                    if stored_ctx == ctx:
                        message_id_old = mid
                        break

                if message_id_old:
                    deposit_message = f"||{ctx.original_message}||"
                    try:
                        self.bot.edit_message_text(
                            text=deposit_message,
                            chat_id=self.mod_channel_id,
                            message_id=message_id_old,
                            parse_mode='MarkdownV2'
                        )
                    except Exception:
                        try:
                            self.bot.send_message(chat_id=message.chat.id,
                                                  text="Не удалось обновить сообщение модерационной панели (редактирование).")
                        except Exception:
                            pass

                    self.user_messages.pop(message_id_old, None)

                self._cleanup_sessions_for_context(ctx)

                try:
                    self.bot.send_message(
                        chat_id=self.mod_channel_id,
                        text=f"Баланс пользователя {ctx.name} пополнен на {amount} RUB.",
                        reply_to_message_id=message.message_id
                    )
                except Exception:
                    pass

                fsm_db.set_brawl_data(ctx.answer.context, -1)

            elif response.text == "-1":
                self.bot.send_message(chat_id=message.chat.id, text="Ошибка при обработке платежа: неверные данные.")
                self.deposit_sessions[session_id] = ctx
            else:
                self.bot.send_message(chat_id=message.chat.id, text=f"Ошибка при обработке платежа. Статус: {response.status_code}")
                self.deposit_sessions[session_id] = ctx
        except requests.exceptions.ConnectionError:
            self.bot.send_message(chat_id=message.chat.id, text="Не удалось подключиться к платежному сервису. Попробуйте позже.")
            self.deposit_sessions[session_id] = ctx
        except Exception as e:
            self.bot.send_message(chat_id=message.chat.id, text=f"Произошла ошибка: {str(e)}")
            self.deposit_sessions[session_id] = ctx

    def _cleanup_sessions_for_context(self, ctx):
        sessions_to_remove = [sid for sid, sctx in self.reply_sessions.items() if sctx == ctx]
        for sid in sessions_to_remove:
            self.reply_sessions.pop(sid, None)

        sessions_to_remove = [sid for sid, sctx in self.deposit_sessions.items() if sctx == ctx]
        for sid in sessions_to_remove:
            self.deposit_sessions.pop(sid, None)

    def _cleanup_context(self, ctx):
        for mid in list(self.user_messages.keys()):
            if self.user_messages[mid] == ctx:
                self.user_messages.pop(mid, None)
        self._cleanup_sessions_for_context(ctx)
