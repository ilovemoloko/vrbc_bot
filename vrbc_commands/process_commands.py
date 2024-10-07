from bot_script import bot, level_on_error, generate_cart_str
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
from vrbc_commands.cart_commands import addCart
from vrbc_commands.donate_commands import reducecd
import local_server
import utils
import time

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


@bot.command("tcccget_help")
def tcccget_help(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    answer.addText("Прочтите первую часть текста по ссылке\n\nhttps://vk.com/topic-***REMOVED***_48144534").reply()


@bot.command("tccc_help")
def tccc_help(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    answer.addText("Прочтите последнюю часть текста по ссылке\n\nhttps://vk.com/topic-***REMOVED***_48144534").reply()


agreement_text = """❗❗❗ВНИМАНИЕ❗❗❗
В тексте спрятано слово, которое нужно написать боту, чтобы вы могли начать выдачу предметов.
У вас не получится использовать бота дальше, если вы внимательно не прочитаете этот текст ПОЛНОСТЬЮ

❗Прочтите текст, чтобы у вас в дальнейшем не возникло проблем с аккаунтом❗

Вы должны знать следующие вещи перед использованием бота:
1. Через некоторое время после отправки кодов аккаунта, бот пришлет вам новые в ответ.
❗АККАУНТ НУЖНО БУДЕТ АКТИВИРОВАТЬ В ИГРЕ С ПОМОЩЬЮ ТЕХ КОДОВ, КОТОРЫЕ ВАМ ДАСТ БОТ❗
О том, как это делается вы сможете прочитать, нажав кнопку \"Как активировать аккаунт?\"

2. Любой аккаунт, который передавался боту ❗ВОЗМОЖНО ВОССТАНОВИТЬ❗ при любых формах его утраты/блокировки.
Стоит учитывать, что восстановление возможно по сохранениям аккаунта.
Каждый раз, когда бот получает аккаунт, прогресс сохранения перезаписывается.
Восстановить аккаунт можно в меню команды !восстановить
Ознакомьтесь в этим текстом до конца, после чего напишите боту большими буквами ПРОДОЛЖИТЬ

3. При любых проблемах с аккаунтом/игрой вы можете обращаться в тех. поддержку бота.
Чтобы нам написать, используйте команду !помощь
"""


iamdumb_text = """❗ВНИМАНИЕ❗ (короткая версия)

После отправки кодов аккаунта, бот пришлет новые.
Аккаунт нужно активировать в игре с этими кодами (подробности по кнопке "Как активировать аккаунт?", которая у вас появится).

Любой аккаунт можно восстановить при утрате/блокировке через команду !восстановить. 
Восстановление идет по последнему сохранению, которое бот обновляет при получении аккаунта.

При проблемах с аккаунтом/игрой пишите в техподдержку через команду !помощь.

Напишите ПРОДОЛЖИТЬ для продолжения.
Вы виноваты сами, если не прочтёте хотя-бы краткую (эту) версию текста.
"""


@bot.command("iamdumb")
def iamdumb(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    answer.addText(iamdumb_text).reply()


@bot.command(".*", level="starthack_agreement")
def starthack_agreement(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Подсказка", "iamdumb")
    buttons.add("Вернуться", "viewcart")
    if context.text == "ПРОДОЛЖИТЬ":
        return starthack(context, True)
    answer.addText(agreement_text).reply()


@bot.command(["starthack", "!взлом", "взлом"], ignore_case=True)
def starthack(context: MessageContext, agreed=False):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    uses_count = info_worker.get_uses(context)

    if uses_count == 0:
        if not agreed:
            buttons.add("Вернуться", "viewcart")
            fsm_db.update_state(context, "starthack_agreement")
            return answer.addText(agreement_text).reply()

    user_bot_values = info_worker.get_bot_values(context)['default_user']

    current_time = int(time.time())
    user_last_use = info_worker.get_value(context, 'last_use')
    user_cooldown = info_worker.get_value(context, 'cooldown', src=user_bot_values)
    next_use = user_cooldown - (current_time - user_last_use)

    if next_use > 0:
        buttons.add("Вернуться в корзину", "viewcart")
        fsm_db.update_state(context, "starthack")
        return answer.addText(f"Пожалуйста, подождите ещё {utils.humanize_time(next_use)}").reply()

    answer.setText("Ваша корзина:\n")
    cart = info_worker.get_value(context, 'cart')
    items_info = info_worker.get_bot_values(context)['items']

    changed = addCart(answer, cart, items_info)
    if not changed:
        answer.addText("Корзина пуста")
        buttons.buttons = []
        buttons.add("Выбрать предметы", "cart")
        return answer.reply()
    buttons.add("Обратно к выбору предметов", "cart")
    buttons.buttons = []
    answer.reply()

    if uses_count == 0:
        buttons.add("Где получить коды?", "tcccget_help")

    answer.setText("Пожалуйста, пришлите коды от аккаунта (текстом или скриншотом)").reply()
    fsm_db.update_state(context, "starthack")


@bot.command(".*", level="starthack", weak=True)
@level_on_error("starthack")
def starthack2(context: MessageContext, retry=False):
    fsm_db.update_state(context, "hack_process")
    attachments = context.attached_photos
    msg = context.text
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    user_bot_values = info_worker.get_bot_values(context)['default_user']

    current_time = int(time.time())
    user_last_use = info_worker.get_value(context, 'last_use')
    user_cooldown = info_worker.get_value(context, 'cooldown', src=user_bot_values)
    next_use = user_cooldown - (current_time - user_last_use)

    if next_use > 0:
        buttons.add("Вернуться в корзину", "viewcart")
        fsm_db.update_state(context, "starthack")
        return answer.addText(f"Пожалуйста, подождите ещё {utils.humanize_time(next_use)}").reply()

    if len(attachments) > 0:
        url = attachments[0]
        image = utils.get_image(url)
        msg = utils.getText(image)

    codes = None
    try:
        codes = utils.extract_codes(msg)
        res = "Коды получены. Начинаем процесс взлома..."
        if not retry:
            answer.setText(res).reply()
    except:
        buttons.add("Вернуться в корзину", "viewcart")
        uses_count = info_worker.get_uses(context)
        if uses_count == 0:
            buttons.add("Где получить эти коды?", "tcccget_help")
        res = "Бот не нашел кодов в сообщении. Пожалуйста, пришлите коды от аккаунта (текстом или скриншотом)"
        answer.setText(res).reply()

    if not codes:
        fsm_db.update_state(context, "starthack")
        return

    transfer, pin = codes
    data, success, version = utils.getSave(transfer, pin)
    if not success:
        fsm_db.update_state(context, "starthack")
        buttons.add("Вернуться в корзину", "viewcart")
        return answer.setText("Не удалось получить сохранение. Убедитесь в правильности кодов.").reply()

    inq = utils.getInq(data)

    if inq == "LOL":
        fsm_db.update_state(context, "starthack")
        return answer.setText("Ошибка обработки аккаунта.").reply()

    status, msg = utils.inq_checker((inq, version), context)
    answer.setText(msg)
    if not status or status == "retry":
        fsm_db.update_state(context, "starthack")
        if status == "retry":
            answer.reply()
            return starthack2(context, retry=True)
        buttons.add("Вернуться в корзину", "viewcart")
        return answer.reply()

    wait_time = local_server.get_wait_time()
    answer.addText(f"Примерное время ожидания до получения кодов: {wait_time} сек.").reply()

    cart = info_worker.get_value(context, 'cart')
    files = {"save": data}
    headers = {"cart": str(cart),
               "ver": version,
               "inq": inq,
               "user": str(fsm_db.get_local_user_id(context))}

    hack_request = local_server.hack_account(files, headers)
    hack_result = eval(hack_request.content.decode("utf-8"))

    if hack_result['status'] == 1:
        transfer, confirmation = hack_result['codes']
        answer.setText("Взлом успешен. Ваши коды:").reply()
        answer.setText(transfer).reply()
        answer.setText(confirmation).reply()

        cart_str = generate_cart_str(cart)

        info_worker.set_preset(context, "last_cart", cart_str)
        info_worker.clear_cart(context)
        info_worker.clear_boosts(context)
        info_worker.set_value(context, 'last_use', current_time)
        fsm_db.update_state(context, "first_msg")

        uses_count = info_worker.get_uses(context)
        if uses_count == 0:
            buttons.add("Как активировать аккаунт?", "tccc_help")
        buttons.add("Уменьшить время ожидания", "reducecd")

        user_bot_values = info_worker.get_bot_values(context)['default_user']
        user_cooldown = info_worker.get_value(context, 'cooldown', src=user_bot_values)
        answer.setText(f"Следующее использование бота будет возможно через {utils.humanize_time(user_cooldown)}")
        info_worker.add_uses(context)
    else:
        fsm_db.update_state(context, "starthack")
        answer.setText(f"Произошла ошибка. Причина: {hack_result['msg']}").setButtons(buttons)

    return answer.reply()


@bot.command("tccc_help", level="first_msg")
def tccc_help_fm(context: MessageContext):
    return tccc_help(context)


@bot.command("reducecd", level="first_msg")
def reducecd_fm(context: MessageContext):
    fsm_db.update_state(context, "*")
    return reducecd(context)


@bot.command(".*", level="hack_process")
def hack_process(context: MessageContext):
    fsm_db.update_state(context, "*")
    MessageBuilder().setReplyMode(context).setText("Пожалуйста, подождите...").reply()
