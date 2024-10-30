from flask import Flask, request, Response
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
from script_base import MessageContext, ButtonsBuilder
import utils
from multiprocessing import Process

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()

app = Flask(__name__)


@app.route('/', methods=['POST'])
def trololo():
    data = request.form
    if int(data['currency']) != 643:
        return "-1"
    platform, platform_id = data['label'].split('_')
    platform_id = int(platform_id)
    amount = float(data['withdraw_amount'])

    sha_hash = data['sha1_hash']

    ctx = MessageContext(platform).setUserId(platform_id)
    buttons = ButtonsBuilder()
    buttons.add("Донат", "donate")
    utils.sendmsg(platform, platform_id, f'Пришло пожертвование в {amount} рублей. Спасибо!', buttons=buttons)
    info_worker.add_donate(ctx, amount)
    return Response(status=200)


@app.route('/pr', methods=['GET'])
def pr():
    return "ПРЯНИКИ"


pserv_process: Process = None


def start():
    global pserv_process
    pserv_process = Process(target=app.run, kwargs={'port': 8000, 'host': '0.0.0.0'})
    pserv_process.start()


def kill():
    global pserv_process
    pserv_process.terminate()
    pserv_process.join()
