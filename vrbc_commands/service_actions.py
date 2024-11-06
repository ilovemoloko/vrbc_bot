from bot_script import bot
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB, VkMembers

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()
vk_members_db = VkMembers()


@bot.command("ileft")
def ileft(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    if not context.trusted:
        return answer.addText("Точно?").reply()

    vk_members_db.remove_member(context.user_id)

    answer.addText("Вы вышли из группы. "
                   "Если это из-за проблем с аккаунтом, обратитесь в техподдержку (!помощь) "
                   "или воспользуйтесь командой !восстановить для быстрого восстановления.").reply()


@bot.command("ijoin")
def ijoin(context: MessageContext):
    vk_members_db.add_member(context.user_id)


@bot.command("notsubscribed")
def notsubscribed(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    if not context.trusted:
        return answer.addText("Точно?").reply()

    buttons.add("Я подписан", "start")
    answer.addText("Вы должны быть подписаны на канал @vorontbc, чтобы использовать этого бота").reply()
