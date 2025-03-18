from bot_script import bot
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
import local_server
import utils

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
    try:
        data, success, version = utils.getSave(transfer, pin)
    except Exception as e:
        res = f"Произошла неожиданная ошибка. Возможно, что на серверах игры имеются проблемы. Попробуйте снова"
        print("GET SAVE ERROR", e)
        answer.setText(res).reply()
        return

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
    answer.addText(f"Аккаунт ({inq}) можно восстановить в меню восстановления (!восстановить)")
    answer.addText(msg).reply()
    fsm_db.update_state(context, "first_msg")