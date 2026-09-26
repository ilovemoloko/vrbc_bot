import db_worker
from bot_script import bot, level_on_error, check_admin
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB, CouponDB
import config
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
coupon_db = CouponDB()


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
    buttons.add("manage notification", "manage_notifications")
    buttons.add("->->", "evalbutbetter 7")
    answer.addText("oijsdfijsdf").reply()


@bot.command(["ыыы 7", "evalbutbetter 7"], ignore_case=True)
def admin_panel(context: MessageContext):
    if check_admin(context) is False:
        return
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("<-<-", "evalbutbetter 6")
    buttons.add("update vk members", "update_vk_members")
    buttons.add("create coupon", "create_coupon")
    buttons.add("set proxy", "set_proxy")
    answer.addText("oijsdfijsdf").reply()


@bot.command("set_proxy")
def set_proxy(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    answer.setText("введи прокси").reply()
    fsm_db.update_state(context, "set_proxy")


@bot.command(".*", level="set_proxy")
def set_proxy(context: MessageContext):
    if check_admin(context) is False:
        return
    proxy_url = context.text
    res = local_server.set_proxy(proxy_url)
    answer = MessageBuilder().setReplyMode(context)
    answer.setText(res).reply()
    fsm_db.update_state(context, "*")


@bot.command("create_coupon")
def create_coupon(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    answer.setText("введи название купона").reply()
    fsm_db.update_state(context, "create_coupon_enter_name")


@bot.command("mega_leave", level=[
    "create_coupon_enter_name",
    "create_coupon_enter_uses",
    "create_coupon_enter_id",
    "create_coupon_enter_desc"
])
def mega_leave(context: MessageContext):
    if check_admin(context) is False:
        return
    fsm_db.update_state(context, "*")
    answer = MessageBuilder().setReplyMode(context)
    answer.setText("вы спаслись отсюда").reply()


@bot.command(".*", level="create_coupon_enter_name")
def create_coupon_enter_name(context: MessageContext):
    if check_admin(context) is False:
        return
    coupon_name = context.text
    buttons = ButtonsBuilder().add("вернуться", "mega_leave")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.setText("введи количество использований").reply()
    fsm_db.update_state(context, f"create_coupon_enter_uses {coupon_name}")


@bot.command(".*", level="create_coupon_enter_uses")
def create_coupon_enter_uses(context: MessageContext):
    if check_admin(context) is False:
        return
    coupon_name = context.fsm[0]
    uses = context.text
    buttons = ButtonsBuilder().add("вернуться", "mega_leave")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.setText("введи буст выдаваемый купоном").reply()
    fsm_db.update_state(context, f"create_coupon_enter_id {coupon_name} {uses}")


@bot.command(".*", level="create_coupon_enter_id")
def create_coupon_enter_id(context: MessageContext):
    if check_admin(context) is False:
        return
    coupon_name = context.fsm[0]
    uses = context.fsm[1]
    id = context.text
    buttons = ButtonsBuilder().add("вернуться", "mega_leave")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    boosts = local_server.get_default_values()['boosts']
    if id not in boosts:
        return answer.addText("такого буста нет").reply()

    boost_type = boosts[id]['type']
    if boost_type == "passive":
        return answer.addText("ТЫ ЧЕ ЕБЛАН ОН ПАССИВНЫЙ").reply()

    answer.setText("введи desc купона").reply()
    fsm_db.update_state(context, f"create_coupon_enter_desc {coupon_name} {uses} {id}")


@bot.command(".*", level="create_coupon_enter_desc")
def create_coupon_enter_desc(context: MessageContext):
    if check_admin(context) is False:
        return
    coupon_name = context.fsm[0]
    uses = context.fsm[1]
    id = context.fsm[2]
    desc = context.text
    coupon_db.add_coup(coupon_name, uses, id, desc)

    buttons = ButtonsBuilder().add("вернуться", "mega_leave")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.setText("молись чтобы оно работало").reply()
    fsm_db.update_state(context, "*")


@bot.command("update_vk_members")
def update_vk_members(context: MessageContext):
    if check_admin(context) is False:
        return

    vk_obj = db_worker.bot_objects['vk']
    members_list = vk_obj.get_group_members()
    db_worker.vk_members_db.add_member_mass(members_list)

    answer = MessageBuilder().setReplyMode(context)
    answer.setText("done").reply()


@bot.command("manage_notifications")
def manage_notifications(context: MessageContext):
    if check_admin(context) is False:
        return
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("delete", "delete_notification")
    buttons.add("set", "set_notification")
    answer.addText("oijsdfijsdf").reply()


@bot.command("delete_notification")
def delete_notification(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    bot_obj = context.srcobj
    bot_obj.update_notification("")
    answer.setText("done").reply()


@bot.command("set_notification")
def set_notification(context: MessageContext):
    if check_admin(context) is False:
        return
    buttons = ButtonsBuilder()
    buttons.add("goback", "manage_notifications")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.setText("какой ставить текст говори").reply()
    fsm_db.update_state(context, "set_notification")


@bot.command(".*", level="set_notification")
def set_notification(context: MessageContext):
    if check_admin(context) is False:
        return
    answer = MessageBuilder().setReplyMode(context)
    text = context.text
    bot_obj = context.srcobj
    bot_obj.update_notification(text)
    answer.setText("done").reply()
    fsm_db.update_state(context, "*")


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
    directory = config.BOT_WORKDIR
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
    if disabled == 1:
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
