from flask import Flask, request, Response
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
from script_base import MessageContext, ButtonsBuilder
import utils
import hashlib
from multiprocessing import Process

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()

app = Flask(__name__)

SECRET_WORD = "***REMOVED***"


@app.route('/', methods=['POST'])
def trololo():
    data = request.form
    try:
        if int(data['currency']) != 643:
            return "-1"
        platform, platform_id = data['label'].split('_')
        platform_id = int(platform_id)
        amount = float(data['withdraw_amount'])

        hash_string = f"{data['notification_type']}&{data['operation_id']}&{data['amount']}&{data['currency']}&{data['datetime']}&{data['sender']}&{data['codepro']}&{SECRET_WORD}&{data['label']}"
        calculated_sha1_hash = hashlib.sha1(hash_string.encode('utf-8')).hexdigest()
        if calculated_sha1_hash != data['sha1_hash']:
            print("Wrong hash")
            return "-1"

        ctx = MessageContext(platform).setUserId(platform_id)
        info_worker.add_donate(ctx, amount)
        buttons = ButtonsBuilder()
        buttons.add("Донат", "donate")
        utils.sendmsg(platform, platform_id, f'Пришло пожертвование в {amount} рублей. Спасибо!', buttons=buttons)
        print("Зачислено", amount)
        return Response(status=200)
    except Exception as e:
        print(e)
        return Response(status=500)


@app.route('/pr', methods=['GET'])
def pr():
    return "ПРЯНИКИ"


pserv_process: Process = None


def start():
    global pserv_process
    pserv_process = Process(target=app.run, kwargs={'port': 8000, 'host': '0.0.0.0', 'threaded': True})
    pserv_process.start()


def kill():
    global pserv_process
    pserv_process.terminate()
    pserv_process.join()
