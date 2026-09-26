# Voron TBC

Это репозиторий для клиентской стороны бота Voron TBC. Это бот, способный самостоятельно изменять данные файлов сохранения в игре The Battle Cats.

Клиентская часть принимает сообщения пользователей во ВКонтакте и Telegram, ведёт каталог предметов и корзину, а также общается с сервером, который непосредственно изменяет сохранения игры.

## Возможности

- Выдача предметов The Battle Cats (глобальная и японская версии).
- Каталог предметов, поиск по названию и корзина с поддержкой пресетов.
- Сохранение и восстановление аккаунтов по кодам переноса.
- Система донатов, бустов и купонов.
- Панель администратора, техподдержка и рассылки.
- Обработка скриншотов кодов через OCR.

## Структура проекта

| Файл | Назначение |
| --- | --- |
| `main.py` | Точка входа, запуск ботов и сервисов согласно `config.py`. |
| `config.py` | Настройки и загрузка секретов из переменных окружения. |
| `bot_script.py` | Общая логика бота, регистрация команд, FSM. |
| `script_base.py` | Базовые классы сообщений, кнопок и обработчиков. |
| `tg_script.py` | Обработка сообщений Telegram. |
| `vk_script.py` | Обработка сообщений ВКонтакте. |
| `db_worker.py` | Работа с базой данных (пользователи, состояния, заказы). |
| `local_server.py` | Клиент взаимодействия с сервером изменения аккаунтов. |
| `public_server.py` | Flask-сервер для приёма платежей. |
| `utils.py` | Утилиты: OCR, прокси, очередь задач, отправка сообщений. |
| `techsup.py` | Логика технической поддержки и модерации. |
| `vrbc_commands/` | Модули с командами бота. |

## Требования

- Python 3.10+ (используются моржовые операторы и `match`-совместимый синтаксис в отдельных местах).
- Tesseract OCR (для распознавания скриншотов с кодами).
- Доступ к серверу изменения аккаунтов (URL задаётся в `config.py`).

Основные зависимости:

```
pyTelegramBotAPI
vk_api
flask
requests
Pillow
pytesseract
numpy
fuzzywuzzy
translate
unidecode
```

## Настройка

Секреты, идентификаторы и инфраструктурные адреса не хранятся в репозитории и читаются из переменных окружения (см. `config.py`):

| Переменная | Описание |
| --- | --- |
| `TG_TOKEN` | Токен Telegram-бота. |
| `VK_TOKEN` | Токен ВКонтакте. |
| `VK_GROUP_ID` | ID сообщества ВКонтакте. |
| `MOD_CHANNEL` | ID канала/чата для модбота. |
| `ADMIN_VK_ID` | ID администратора ВКонтакте. |
| `PAY_API_TOKEN` | Токен платёжного API. |
| `PAY_API_URL` | Адрес платёжного API. |
| `DONATE_PHONE` | Номер телефона для приёма донатов. |
| `DONATE_CARD` | Номер карты для приёма донатов. |
| `LOCALSERVER_URL` | Адрес сервера изменения аккаунтов. |
| `GAME_API_URL` | Базовый адрес API сохранений игры. |
| `PUBLIC_SERVER_HOST` | Хост Flask-сервера приёма платежей. |
| `PUBLIC_SERVER_PORT` | Порт Flask-сервера приёма платежей. |
| `PUBLIC_SERVER_URL` | Публичный адрес Flask-сервера платежей. |
| `DB_PATH` | Путь к файлу базы данных. |
| `BOT_WORKDIR` | Рабочий каталог бота. |
| `PROXY` | Прокси для исходящих запросов. |
| `TG_TOKEN_AVTOMOIKA`, `VK_TOKEN_AVTOMOIKA` | Токены тестового окружения. |
| `VK_GROUP_ID_AVTOMOIKA`, `MOD_CHANNEL_AVTOMOIKA` | ID тестового окружения. |

Пример:

```bash
export TG_TOKEN="..."
export VK_TOKEN="..."
export VK_GROUP_ID="..."
export MOD_CHANNEL="..."
export ADMIN_VK_ID="..."
export PAY_API_TOKEN="..."
export PAY_API_URL="..."
export DONATE_PHONE="..."
export DONATE_CARD="..."
export LOCALSERVER_URL="http://127.0.0.1:5000"
export GAME_API_URL="https://nyanko-save.ponosgames.com"
export PUBLIC_SERVER_HOST="0.0.0.0"
export PUBLIC_SERVER_PORT="8000"
export PUBLIC_SERVER_URL="http://localhost:8000"
export DB_PATH="db/userdata.db"
export BOT_WORKDIR="."
export PROXY=""
```

Флаги запуска компонентов (`start_vk`, `start_tg`, `start_public_server`, `start_mainprocess` и другие) задаются в `config.py`.

## Запуск

```bash
python main.py
```

Приложение запускает VK- и Telegram-ботов, Flask-сервер платежей и фоновую очередь обработки задач в отдельных потоках/процессах.

## Ссылки

- Сообщество ВКонтакте: https://vk.com/club181453019
- Telegram-канал: https://t.me/vorontbc
