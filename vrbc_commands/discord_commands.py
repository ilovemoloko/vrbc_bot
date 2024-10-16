from bot_script import bot, level_on_error
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
import techsup
import time
import utils

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


@bot.command([r"startfight.*", "!отправить", "!админ", "отправить", "админ", "помоги", "!помоги"], level=["*", "letsgo", "first_msg"])
def start_fight(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Написать админу", "letsgo")
    buttons.add("Меню помощи", "help")

    if len(context.text.split()) > 1:
        fsm_db.update_state(context, "*")

    answer.setText("В этом меню вы можете обратиться к администраторам бота.").reply()


@bot.command("letsgo", level=["*", "letsgo"])
def letsgo(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться", "startfight 1")

    current_time = int(time.time())
    user_last_use = fsm_db.get_brawl_data(context)
    user_cooldown = 60*60
    next_use = user_cooldown - (current_time - user_last_use)

    if next_use > 0:
        buttons.insert(0, "Вернуться в главное меню", "menu")
        buttons.insert(0, "Попробовать снова", "letsgo")
        return answer.addText(f"Пожалуйста, подождите ещё {utils.humanize_time(next_use)}").reply()

    answer.setText("Напишите сообщение, которое вы хотите отправить").reply()
    fsm_db.update_state(context, "letsgo")


modbot = techsup.Modbot()


@bot.command(".*", level="letsgo")
@level_on_error("start_msg")
def letsgo(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("В главное меню", "menu")

    text = context.text
    if len(text) == 0:
        return answer.setText("Напишите сообщение (в нем должен быть текст), которое вы хотите отправить").reply()
    elif len(text) > 2000:
        return answer.setText("Слишком длинное сообщение. Сократите его и попробуйте снова").reply()

    local_user_id = fsm_db.get_local_user_id(context)
    bot_obj = context.srcobj
    bot_obj.get_user_description(context)
    ctx = techsup.LittleContext(context.peer_id,
                                context.text,
                                context.userData["name"],
                                local_user_id,
                                context.userData["image_url"],
                                context.attached_photos, answer)
    modbot.handle_message(ctx)
    fsm_db.set_brawl_data(context, int(time.time()))
    fsm_db.update_state(context, "*")

    buttons = ButtonsBuilder()
    answer = answer.setButtons(buttons)
    buttons.add("Главное меню", "menu")
    return answer.setText("Сообщение отправлено\nОжидайте ответа").reply()
