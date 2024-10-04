from bot_script import bot
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
import utils

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


@bot.command(r"startfight .*")
def start_fight(context: MessageContext):
    answer = MessageBuilder().setReplyMode(context)
    message = "я не хочу пока тестировать как у тебя работает внедрение новых команд с тз синтаксиса"
    user = str(fsm_db.get_local_user_id(context))

    # если спор уже начат хз аезир сам сделай дб штуки
    if answer:
        return answer.setText("У Вас уже ведется диалог с админчиками. Пожалуйста, дождитесь ответа.").reply()
    req = utils.create_ds_channel(user, "PLATFORM")
    if req.status_code == 200:
        discord_channel_id = eval(req.text)['id']
        if message:
            utils.send_ds_message(discord_channel_id, message)
            return answer.setText("Ваше сообщение было передано администрации. уйди отсюда сука").reply()
        return answer.setText("Был начат спор с администрацией (вы выбрали смерть.)").reply()
    return answer.setText("Я НЕ МОГУ ОТПРАВИТЬ ПОЖАЛУЙСТА УЙДИ").reply()
    # тебе кстати возможно интересно как же так вышло что я начал работать
    # я обнаружил что нужно просто сесть за кодинг ночью под бедфингер-бейби блю
    #код дс бота кстати полностью готов нужно просто чут чут поиграться с изображениями (и здесь тоже)


@bot.command(r".*", level="fight")  # интересно а как сделать так чтоб любое сообщение не принадлежащее к основному протоколу шло в дискорд
def complain(context: MessageContext):
    # я подозреваю что нужно подобную ноунейм команду просто в конец пихнуть
    # я не очень хочу тебе весь код сносить и менять как мне удобно и понятно потому что он сука твой
    # поэтому если что просто подправь я думаю это не так сложно и думаю это можно отдельно вынести
    if "ты не общаешься с админами еблан" * 0: return
    answer = MessageBuilder().setReplyMode(context)
    attempt = utils.send_ds_message("тут должен быть айди канала дискорда из дб", context.text)
    if attempt.status_code == 200:
        return answer.setText("Отправлено.").reply()
    return answer.setText("завались").reply()
