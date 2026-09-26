from flask import Flask, request, Response
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB, MonthlyReportDatabase
from script_base import MessageContext, ButtonsBuilder
import config
import utils
from multiprocessing import Process
import traceback

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()
mr_db = MonthlyReportDatabase()

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_payment():
    try:
        data = request.json
        if not data:
            return "-1"

        # Проверка валюты
        if data.get("currency") != "RUB":
            return "-1"

        if data.get("type") != "payment_success":
            return "-1"

        # Разбираем payload: {src}_{user_id}
        payload = data.get("payload", "")
        if "_" not in payload:
            return "-1"
        src, platform_id_str = payload.split("_", 1)
        platform_id = int(platform_id_str)

        # Сумма платежа
        amount = float(data.get("amount", 0))

        # Обработка платежа
        ctx = MessageContext(src).setUserId(platform_id)
        info_worker.add_donate(ctx, amount)

        # Кнопки
        buttons = ButtonsBuilder()
        buttons.add("Донат", "donate")
        utils.sendmsg(src, platform_id, f'Пришло пожертвование {amount} рублей.\nСпасибо за поддержку бота!', buttons=buttons)

        # Обновляем отчет
        mr_db.add_payment(amount)

        return Response(status=200)

    except Exception as e:
        print("Ошибка обработки платежа:", traceback.format_exc())
        return Response(status=500)


@app.route('/pr', methods=['GET'])
def pr():
    return "ПРЯНИКИ"


pserv_process: Process = None

def start():
    global pserv_process
    pserv_process = Process(target=app.run, kwargs={'port': config.PUBLIC_SERVER_PORT, 'host': config.PUBLIC_SERVER_HOST, 'threaded': True})
    pserv_process.start()

def kill():
    global pserv_process
    pserv_process.terminate()
    pserv_process.join()
