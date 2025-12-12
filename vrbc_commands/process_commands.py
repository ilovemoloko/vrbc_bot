import config
from bot_script import bot, level_on_error, generate_cart_str
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
from vrbc_commands.cart_commands import addCart
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


@bot.command('tccc_ncorrect')
def tccc_ncorrect(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    answer.addText("Вы отправили коды боту в нужном формате, но бот не может получить аккаунт.\n\n"
                   "Это могло произойти по следующим причинам:\n"
                   "1) Коды правильные, но устаревшие. Учтите, что каждая пара кодов Одноразовая!\n"
                   "2) Вы вышли с экрана кодов до того, как бот закончил процесс. Эти коды работают лишь тогда, когда их можно увидеть на экране игры\n"
                   "3) Вы пытаетесь использовать бота на неподдерживаемой версии. Бот работает только с английской и японской версиями игры (не перепутайте китайскую версию с японской)").reply()


agreement_text = """❗❗❗ВНИМАНИЕ❗❗❗
В тексте спрятано слово, которое нужно написать боту, чтобы вы могли начать выдачу предметов.
У вас не получится использовать бота дальше, если вы внимательно не прочитаете этот текст ПОЛНОСТЬЮ

❗Прочтите текст, чтобы у вас в дальнейшем не возникло проблем с аккаунтом❗

Вы должны знать следующие вещи перед использованием бота:
1. Через некоторое время после отправки кодов аккаунта, бот пришлет вам новые в ответ.
❗АККАУНТ НУЖНО БУДЕТ АКТИВИРОВАТЬ В ИГРЕ С ПОМОЩЬЮ ТЕХ КОДОВ, КОТОРЫЕ ВАМ ДАСТ БОТ❗
Пока вы этого не сделаете - у вас будет пустой аккаунт.
О том, как это делается вы сможете прочитать, нажав кнопку \"Как активировать аккаунт?\" (Она у вас появится после выдачи кодов ботом)

2. Любой аккаунт, который передавался боту ❗ВОЗМОЖНО ВОССТАНОВИТЬ❗ при любых формах его утраты/блокировки.
Стоит учитывать, что восстановление возможно лишь по сохранениям аккаунта.
Каждый раз, когда бот получает аккаунт, прогресс сохранения перезаписывается.
Восстановить аккаунт можно в меню команды !восстановить
Ознакомьтесь с этим текстом до конца, после чего напишите боту ПРОДОЛЖИТЬ

3. При любых проблемах с аккаунтом/игрой вы можете обращаться в тех. поддержку бота.
Чтобы нам написать, используйте команду !помощь
"""

iamdumb_text = """❗ВНИМАНИЕ❗
Прочтите, иначе в будущем вы не будете знать что делать, если возникнут проблемы с аккаунтом

После отправки кодов аккаунта, бот пришлет новые.
Аккаунт нужно активировать в игре с этими кодами (подробности по кнопке "Как активировать аккаунт?", которая у вас появится после выдачи кодов).
Пока вы этого не сделаете - у вас будет пустой аккаунт.

Любой аккаунт можно восстановить при утрате/блокировке через команду !восстановить. 
Восстановление идет по последнему сохранению, которое бот обновляет при получении аккаунта.

При проблемах с аккаунтом/игрой пишите в техподдержку через команду !помощь.

Напишите ПРОДОЛЖИТЬ для продолжения.
"""


@bot.command(".*", level="starthack_agreement")
def starthack_agreement(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться", "viewcart")
    if context.text.lower() == "продолжить":
        return starthack(context, True)
    try:
        if utils.extract_codes(context.text):
            return answer.addText("Коды от вас потребуются на следующем этапе.\n"
                                  "Сейчас боту нужно, чтобы вы прочитали текст выше "
                                  "и написали слово, которое там скрыто. "
                                  "Бот должен убедиться, что вы прочитали тот текст").reply()
    except:
        pass
    answer.addText(iamdumb_text).reply()


@bot.command(["starthack", "!взлом", "взлом"], ignore_case=True)
def starthack(context: MessageContext, agreed=False):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    if utils.hack_locked:
        utils.add_mass_msg(context, answer)
        return answer.setText("Накрутка сейчас отключена. Бот оповестит вас, когда мы его включим.").reply()

    uses_count = info_worker.get_uses(context)
    if uses_count == 0:
        if not agreed:
            buttons.add("Вернуться", "viewcart")
            fsm_db.update_state(context, "starthack_agreement")
            return answer.addText(iamdumb_text).reply()
        else:
            fsm_db.update_state(context, "*")

    user_bot_values = info_worker.get_bot_values(context)['default_user']

    current_time = int(time.time())
    user_last_use = info_worker.get_value(context, 'last_use')
    user_cooldown = info_worker.get_value(context, 'cooldown', src=user_bot_values)
    next_use = user_cooldown - (current_time - user_last_use)

    if next_use > 0:
        buttons.add("Пропустить время", "skip_cd")
        buttons.add("Вернуться в корзину", "viewcart")
        fsm_db.update_state(context, "starthack")
        if not user_bot_values["is_member"]:
            answer.addText("Подпишитесь на группу, чтобы время ожидания было меньше на 10 часов.\n")
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
    answer.reply()
    buttons.buttons = []

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

    if utils.hack_locked:
        utils.add_mass_msg(context, answer)
        fsm_db.update_state(context, "starthack")
        return answer.setText("Накрутка сейчас отключена. Бот оповестит вас, когда мы его включим.").reply()

    current_time = int(time.time())
    user_last_use = info_worker.get_value(context, 'last_use')
    user_cooldown = info_worker.get_value(context, 'cooldown', src=user_bot_values)
    next_use = user_cooldown - (current_time - user_last_use)

    if next_use > 0:
        buttons.add("Вернуться в корзину", "viewcart")
        fsm_db.update_state(context, "starthack")
        if not user_bot_values["is_member"]:
            answer.addText("Подпишитесь на группу, чтобы время ожидания было меньше на 10 часов.\n")
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
    try:
        data, success, version = utils.getSave(transfer, pin)
    except Exception as e:
        res = f"Произошла неожиданная ошибка. Возможно, что на серверах игры имеются проблемы. Попробуйте снова"
        print("GET SAVE ERROR", e)
        answer.setText(res).reply()
        fsm_db.update_state(context, "starthack")
        return

    if not success:
        fsm_db.update_state(context, "starthack")
        buttons.add("Но коды правильные", "tccc_ncorrect")
        buttons.add("Вернуться в корзину", "viewcart")
        return answer.setText("Не удалось получить сохранение. Убедитесь в правильности кодов.").reply()
    info_worker.set_value(context, 'japan_user', version == "ja")

    inq = utils.getInq(data)

    if inq == "LOL":
        fsm_db.update_state(context, "starthack")
        return answer.setText("Ошибка обработки аккаунта.").reply()

    status, msg = utils.inq_checker((inq, version), context)
    answer.setText(msg)
    if not status or status == "retry":
        fsm_db.update_state(context, "starthack")
        if status == "retry":
            buttons.add("?????", "huh_whatisthat")
            answer.reply()
            return starthack2(context, retry=True)
        if "Вы достигли лимита" in msg:
            buttons.insert(0, "Увеличить лимит", "buy_slot")
        buttons.add("Вернуться в корзину", "viewcart")
        return answer.reply()

    num_version = utils.getVersion(data)
    if num_version <= config.min_version:
        buttons.add("Вернуться в корзину", "viewcart")
        fsm_db.update_state(context, "starthack")
        return answer.setText("Ваша версия игры слишком старая. "
                              "Обновитесь, и тогда бот сможет закончить процесс").reply()

    # if num_version == 140000:
    #     buttons.add("Вернуться в корзину", "viewcart")
    #     fsm_db.update_state(context, "starthack")
    #     return answer.setText("Эта версия игры пока что не поддерживается. "
    #                           "В группе будет пост, когда мы наладим её").reply()

    try:
        wait_time = local_server.get_wait_time()
    except:
        answer.setText("Бот потерял связь с сервером. Попробуйте ещё раз немного позже.").reply()
        raise ConnectionError

    wait_time = round(float(wait_time))
    wait_time = utils.humanize_time(wait_time)
    buttons.add("Случайный факт", "funfact")
    answer.addText(f"Примерное время ожидания до получения кодов: {wait_time}")
    answer.addText("\nНе заходите в игру, пока бот не закончит процесс.").reply()
    buttons = ButtonsBuilder()
    answer.setButtons(buttons)

    cart = info_worker.get_value(context, 'cart')
    files = {"save": data}
    headers = {"cart": str(cart),
               "ver": version,
               "inq": inq,
               "user": str(fsm_db.get_local_user_id(context))}

    hack_result = local_server.hack_account(files, headers)

    if hack_result['status'] == 1:
        transfer, confirmation = hack_result['codes']
        success_status = hack_result['success_status']
        answer.setText("Взлом успешен. Ваши коды:").reply()
        answer.setText(transfer).reply()
        answer.setText(confirmation).reply()

        cart_str = generate_cart_str(cart)

        info_worker.set_preset(context, "last_cart", cart_str)
        info_worker.clear_cart(context)
        info_worker.clear_boosts(context)
        info_worker.spend_from_boosts(context, success_status)
        info_worker.set_value(context, 'last_use', current_time)
        fsm_db.update_state(context, "first_msg")

        if not user_bot_values["is_member"]:
            answer.setText("Подпишитесь на группу, чтобы ожидать на 10 часов меньше и иметь более широкую корзину").reply()

        uses_count = info_worker.get_uses(context)
        if uses_count == 0:
            buttons.add("Как активировать аккаунт?", "tccc_help")
        buttons.add("Не получается ввести коды", "help_enter")
        buttons.add("Уменьшить время ожидания", "reducecd")

        user_bot_values = info_worker.get_bot_values(context)['default_user']
        user_cooldown = info_worker.get_value(context, 'cooldown', src=user_bot_values)
        answer.setText(f"Следующее использование бота будет через {utils.humanize_time(user_cooldown)}\n\n"
                       f"Хотите снизить время ожидания или увеличить лимиты? "
                       f"Поддержите нас материально с помощью команды !донат для получения бонусов!")

        info_worker.add_uses(context)
    else:
        fsm_db.update_state(context, "starthack")
        answer.setText(f"Произошла ошибка. Причина: {hack_result['msg']}").setButtons(buttons)

    return answer.reply()


@bot.command("tccc_help", level="first_msg")
def tccc_help_fm(context: MessageContext):
    return tccc_help(context)
