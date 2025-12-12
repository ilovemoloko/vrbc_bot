from bot_script import bot, check_admin
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
import local_server
import utils
import time
import re

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


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
    vk_id = -1
    if context.src == "vk":
        vk_id = context.user_id
    accounts = local_server.get_user_backups(user_id, vk_id=vk_id)

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

    if utils.hack_locked:
        utils.add_mass_msg(context, answer)
        fsm_db.update_state(context, "starthack")
        return answer.setText("Накрутка сейчас отключена. Бот оповестит вас, когда мы его включим.").reply()

    buttons.add("Вернуться", "recovery_menu")

    user_id = fsm_db.get_local_user_id(context)
    vk_id = -1
    if context.src == "vk":
        vk_id = context.user_id
    accounts = local_server.get_user_backups(user_id, vk_id=vk_id)

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


@bot.command(".*", level="select_account_conf")
def select_account_conf(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться", "recovery_menu")
    text = context.text
    if text != "ВОССТАНОВИТЬ":
        answer.setText("""❗❗❗ЭТО ВАЖНО, ПРОЧТИТЕ ВНИМАТЕЛЬНО❗❗❗
Если вы восстановите аккаунт, то старый код аккаунта больше не будет доступен для КАКОГО-ЛИБО использования в боте.
Код вашего аккаунта игры изменится после восстановления.

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
    status, new_inq, msg, tc, cc, ver = local_server.recovery_backup(user_id, old_inq)
    if (not status) or (not new_inq) or (new_inq == "") or (tc == "") or (cc == ""):
        if msg == "Ваши коды:":
            msg = "Произошла ошибка. Попробуйте восстановить аккаунт ещё раз"
        return answer.setText(msg).reply()
    answer.setButtons(None)
    try:
        if len(cc) == 0:
            raise ValueError
        buttons = ButtonsBuilder()
        buttons.add("Не получается ввести коды", "help_enter")
        answer.setButtons(buttons).setText(msg).reply().setButtons(None).setText(tc).reply().setText(cc).reply()
    except:
        answer.setText("Произошла ошибка. Попробуйте восстановить позже.")
    utils.recovery_rite(context, old_inq, new_inq, is_jp=ver)
    fsm_db.update_state(context, "first_msg")


@bot.command("help_enter", level=["first_msg", "*"])
def help_enter(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    answer.setText("""
Пожалуйста, сначала прочтите этот пост:
https://vk.ru/lib5436874?w=wall-***REMOVED***_5314

Если ошибка, показанная в посте полностью не совпадает с вашей, то сразу приступите ко второму способу.
Если это не помогло, обратитесь в тех. поддержку бота (напишите боту !отправить)
""").reply()
