from bot_script import bot, check_admin
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
from vrbc_commands.menu_commands import recovery_menu
import local_server
import utils
import time
import re

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


@bot.command("save_account")
def save_account(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    uses_count = info_worker.get_uses(context)
    if uses_count == 0:
        buttons.add("Где получить эти коды?", "tcccget_help")
    answer.setText("Пожалуйста, пришлите коды от аккаунта (текстом или скриншотом)").reply()
    fsm_db.update_state(context, "save_account")


@bot.command(".*", level="save_account", weak=True)
def save_account_input(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    attachments = context.attached_photos
    msg = context.text

    answer.setText("Начинаем сохранять ваш аккаунт").reply().setText("")

    buttons.add("Перейти в главное меню", "начать")

    if len(attachments) > 0:
        url = attachments[0]
        image = utils.get_image(url)
        msg = utils.getText(image)

    try:
        codes = utils.extract_codes(msg)
    except:
        uses_count = info_worker.get_uses(context)
        if uses_count == 0:
            buttons.add("Где получить эти коды?", "tcccget_help")
        res = "Бот не нашел кодов в сообщении. Пожалуйста, пришлите коды от аккаунта (текстом или скриншотом)"
        return answer.setText(res).reply()

    transfer, pin = codes
    data, success, version = utils.getSave(transfer, pin)
    if not success:
        return answer.setText("Не удалось получить сохранение. Убедитесь в правильности кодов.").reply()

    inq = utils.getInq(data)
    if inq == "LOL":
        return answer.setText("Ошибка обработки аккаунта.").reply()

    status, msg = utils.inq_checker((inq, version), context)
    if status is not True:
        answer.setText(msg)
    if not status:
        fsm_db.update_state(context, "first_msg")
        if "Вы достигли лимита" in msg:
            buttons.insert(0, "Увеличить лимит", "buy_slot")
        return answer.reply()

    user_id = fsm_db.get_local_user_id(context)
    files = {"save": data}
    status, msg = local_server.backup_account(user_id, inq, files)
    answer.addText(f"Ваш код аккаунта: {inq}")
    answer.addText(msg).reply()
    fsm_db.update_state(context, "first_msg")


@bot.command("recovery_account")
def recovery_account(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    current_time = int(time.time())
    user_last_use = info_worker.get_value(context, 'last_use_recovery')
    user_cooldown = 5*60
    if check_admin(context):
        user_cooldown = 0
    next_use = user_cooldown - (current_time - user_last_use)
    if next_use > 0:
        buttons.add("Вернуться в меню функций", "menu")
        return answer.addText(f"Пожалуйста, подождите ещё {utils.humanize_time(next_use)}").reply()

    user_id = fsm_db.get_local_user_id(context)
    accounts = local_server.get_user_backups(user_id)

    if len(accounts) == 0:
        return answer.setText("У вас еще нет сохранений.").reply()
    elif len(accounts) == 1:
        old_inq = accounts[0]
        answer.setText(f"Восстанавливаем аккаунт {old_inq}").reply().setButtons(None)
        context.text = f"select_account {old_inq}"
        select_account(context, False)
    else:
        text = "Выберите аккаунт для восстановления\n"
        for account in accounts:
            text += f" - - {account}\n"
        answer.setText(text).reply()
        fsm_db.update_state(context, "select_account")


@bot.command(".*", level="select_account", weak=True)
def select_account(context: MessageContext, send_start_msg=True):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться", "recovery_menu")

    user_id = fsm_db.get_local_user_id(context)
    accounts = local_server.get_user_backups(user_id)

    inq_regex = r"([\da-fA-F]{9})"
    result = re.search(inq_regex, context.text)
    if result is None:
        return answer.setText("Неверный код аккаунта").reply()
    old_inq = result.group(0)
    if old_inq not in accounts:
        return answer.setText("Неверный код аккаунта").reply()

    answer.setText("""❗❗❗ВНИМАНИЕ❗❗❗
Код вашего аккаунта игры изменится после восстановления.
Если вы восстановите аккаунт, то старый код аккаунта больше не будет доступен для какого-либо использования в боте.
Используйте эту функцию лишь в том случае, если вам действительно нужно восстановить аккаунт.
Если вы согласны с условиями, то напишите заглавными буквами слово ВОССТАНОВИТЬ""").reply()

    fsm_db.update_state(context, f"select_account_conf {int(send_start_msg)} {old_inq}")


@bot.command("recovery_menu", level="select_account_conf")
def recovery_menu_back_conf(context: MessageContext):
    fsm_db.update_state(context, "*")
    recovery_menu(context)


@bot.command(".*", level="select_account_conf")
def select_account_conf(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться", "recovery_menu")
    text = context.text
    if text != "ВОССТАНОВИТЬ":
        answer.setText("""❗❗❗ЭТО ВАЖНО, ПРОЧТИТЕ ВНИМАТЕЛЬНО❗❗❗
Код вашего аккаунта игры изменится после восстановления.
Если вы восстановите аккаунт, то старый код аккаунта больше не будет доступен для какого-либо использования в боте.
Используйте эту функцию лишь в том случае, если вам действительно нужно восстановить аккаунт.
Если вы согласны с условиями, то напишите заглавными буквами слово ВОССТАНОВИТЬ""").reply()
    else:
        fsm_db.update_state(context, "*")
        select_account_afterconf(context)


def select_account_afterconf(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    current_time = int(time.time())
    info_worker.set_value(context, 'last_use_recovery', current_time)

    answer.setText("Сейчас бот отправит коды аккаунта...").reply()
    if int(context.fsm[0]):
        buttons.add("Посмотреть список аккаунтов", "recovery_account")

    user_id = fsm_db.get_local_user_id(context)
    old_inq = context.fsm[1]
    status, new_inq, msg, tc, cc = local_server.recovery_backup(user_id, old_inq)
    if (not status) or (not new_inq) or (new_inq == "") or (tc == "") or (cc == ""):
        if msg == "Ваши коды:":
            msg = "Попробуйте восстановить аккаунт ещё раз"
        return answer.setText(msg).reply()
    answer.setButtons(None)
    try:
        answer.setText("Ваши коды: ").reply().setText(tc).reply().setText(cc).reply()
    except:
        answer.setText("Произошла ошибка. Попробуйте восстановить позже.")
    utils.recovery_rite(context, old_inq, new_inq)
    fsm_db.update_state(context, "first_msg")
