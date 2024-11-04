from bot_script import bot, level_on_error, check_admin
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
import local_server
import utils
import os
import sys
import subprocess
import threading
import time
import techsup
import public_server


fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


def stop_flask_server():
    public_server.kill()


@bot.command(["ыыы 3", "ыыы", "evalbutbetter 3"], ignore_case=True)
def admin_panel(context: MessageContext):
    if check_admin(context) is False:
        return
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("update bv", "update_bot_values")
    buttons.add("restart bot", "restart_bot")
    buttons.add("unpack bot", "unpack_bot")
    buttons.add("hack reset", "hack_reset")
    buttons.add("->->", "evalbutbetter 4")
    answer.addText("!админка").reply()


@bot.command(["ыыы 4", "evalbutbetter 4"], ignore_case=True)
def admin_panel(context: MessageContext):
    if check_admin(context) is False:
        return
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("<-<-", "evalbutbetter 3")
    buttons.add("console", "console")
    buttons.add("reverse rite", "reverse_rite")
    buttons.add("upgrade bot", "upgrade_bot")
    buttons.add("->->", "evalbutbetter 5")
    answer.addText("!админка").reply()


@bot.command(["ыыы 5", "evalbutbetter 5"], ignore_case=True)
def admin_panel(context: MessageContext):
    if check_admin(context) is False:
        return
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("<-<-", "evalbutbetter 4")
    buttons.add("lock bot", "lock_bot")
    buttons.add("unlock bot", "unlock_bot")
    buttons.add("islocked", "islocked")
    buttons.add("->->", "evalbutbetter 6")
    answer.addText("oijsdfijsdf").reply()


@bot.command(["ыыы 6", "evalbutbetter 6"], ignore_case=True)
def admin_panel(context: MessageContext):
    if check_admin(context) is False:
        return
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("<-<-", "evalbutbetter 5")
    buttons.add("stop_bot", "stop_bot")
    buttons.add("get queue", "get_queue")
    answer.addText("oijsdfijsdf").reply()


@bot.command("get_queue")
def get_queue(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    answer.setText(str(local_server.get_queue())).reply()


@bot.command("stop_bot")
def stop_bot(context: MessageContext):
    if check_admin(context) is False:
        return

    answer = MessageBuilder().setReplyMode(context)
    answer.setText("Ожидание конца процессов...").reply()

    if utils.hack_locked:
        sys.argv.append("lock")
        utils.mass_msg("Бот выключается. "
                       "Дождитесь включения бота, после чего попробуйте использовать его.")
    else:
        if "lock" in sys.argv:
            sys.argv.remove("lock")

    bot.stop()
    me_thread = threading.current_thread().name
    while True:
        time.sleep(0.1)
        threads = threading.enumerate()
        if any((("handle_action" in thread.name) and (thread.name != me_thread)) for thread in threads):
            continue
        break

    answer.setText("Выключаю бота").reply()

    stop_flask_server()


@bot.command("islocked")
def islocked(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    if utils.hack_locked:
        answer.addText("Бот заблокирован").reply()
    else:
        answer.addText("Бот разблокирован").reply()
        

@bot.command("lock_bot")
def lock_bot(context: MessageContext):
    if check_admin(context) is False:
        return
    utils.hack_locked = True


@bot.command("unlock_bot")
def unlock_bot(context: MessageContext):
    if check_admin(context) is False:
        return
    utils.hack_locked = False
    utils.mass_msg()


@bot.command("hack_reset")
def hack_reset(context: MessageContext):
    if check_admin(context) is False:
        return
    fsm_db.hack_reset()


@bot.command("upgrade_bot")
def upgrade_bot(context: MessageContext):
    if check_admin(context) is False:
        return
    unpack_bot(context)
    restart_bot(context)


@bot.command("console")
def console(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    answer.addText("вводи код").reply()
    fsm_db.update_state(context, "console")


@bot.command(".*", level="console")
@level_on_error("*")
def console_command(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    text = context.text
    result = utils.exec_and_return(context, text)
    result = str(result)
    if result == "None":
        result = "ок."
    elif len(result) > 1024:
        result = result[:1024] + "..."
        print(result)
    answer.addText(f"{result}").reply()
    fsm_db.update_state(context, "*")


@bot.command("update_bot_values")
def update_bot_values(context: MessageContext):
    if check_admin(context) is False:
        return
    local_server.update_variables()
    answer = MessageBuilder().setReplyMode(context)
    answer.addText("Бот обновлен").reply()


@bot.command("restart_bot")
def restart_bot(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    answer.setText("Ожидание конца процессов...").reply()

    if utils.hack_locked:
        sys.argv.append("lock")
        utils.mass_msg("Бот перезапускается. "
                       "Это не гарантирует того, что бот будет работать исправно, но вы можете попытаться.")
    else:
        if "lock" in sys.argv:
            sys.argv.remove("lock")

    # bot.stop()
    me_thread = threading.current_thread().name
    while True:
        time.sleep(0.1)
        threads = threading.enumerate()
        if any((("handle_action" in thread.name) and (thread.name != me_thread)) for thread in threads):
            continue
        break

    answer.setText("Перезапускаю бота").reply()
    stop_flask_server()
    os.execv(sys.executable, ['python'] + sys.argv)


@bot.command("unpack_bot")
def unpack_bot(context: MessageContext):
    if check_admin(context) is False:
        return
    directory = "***REMOVED***"
    command = ['7z', "x", "-aoa", "project.tar.gz"]

    result = subprocess.run(command, cwd=directory, check=True, stdout=subprocess.PIPE)
    result = result.stdout.decode('utf-8')

    answer = MessageBuilder().setReplyMode(context)
    answer.addText(f"{result}").reply()


@bot.command("reverse_rite")
def reverse_rite(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    answer.addText("код аккаунта?").reply()
    fsm_db.update_state(context, "reverse_rite")


@bot.command(".*", level="reverse_rite", weak=True)
def reverse_rite_check(context: MessageContext):
    if check_admin(context) is False:
        return
    inq = context.text

    if inq.lower() == "none":
        inq = ""

    answer = MessageBuilder().setReplyMode(context)
    account = bca_db.get_account_info(inq)
    if account is None:
        fsm_db.update_state(context, "*")
        return answer.addText("такого аккаунта нет").reply()

    user_id, isjp, originalcode, disabled = account
    if disabled:
        fsm_db.update_state(context, "*")
        return answer.addText("аккаунт уже реверснут").reply()

    utils.recovery_rite(context, inq, originalcode)
    bca_db.set_disabled(originalcode, False)
    answer.addText("аккаунт реверснут").reply()
    fsm_db.update_state(context, "*")


@bot.command(r"сукорз [\s\S]*", replace_newline="\n")
def sucart(context: MessageContext):
    if check_admin(context) is False:
        return
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться в корзину", "viewcart")
    newcart_str = context.text.split("сукорз", 1)[1]
    for item in newcart_str.splitlines():
        item_id, amount = item.split()
        info_worker.add_to_cart(context, int(item_id), int(amount), ignore_max=True)
    answer.addText("Корзина обновлена").reply()

modbot = techsup.Modbot()

@bot.command("инфо")
def info(context: MessageContext):
    if check_admin(context) is False:
        return
    local_user_id = fsm_db.get_local_user_id(context)
    answer = MessageBuilder().setReplyMode(context)
    if local_user_id is None:
        answer.setText("У вас пока что нет аккаунта!")
    else:
        user_info = local_user_db.get_info(context)
        fsm_level = fsm_db.get_state(context)
        answer.setText(f"Ваша информация об аккаунте:\n\n{user_info}").addText(f"fsmstate = {fsm_level}")
    bot_obj = context.srcobj
    bot_obj.get_user_description(context)
    answer.addText(str(context.userData), start="\n\n")
    answer.reply()

    # context.text = "spsdufhsdpifhsdpfisudhfspdifuhspfiusdhf dfsipudufhs dpfosudf"
    # ctx = techsup.LittleContext(context.peer_id,
    #                             context.text,
    #                             context.userData["name"],
    #                             local_user_id,
    #                             context.userData["image_url"],
    #                             context.attached_photos, answer)
    # modbot.handle_message(ctx)
