from flask import Flask, request
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
from script_base import MessageContext
import utils
import logging

logging.getLogger("werkzeug").setLevel(logging.ERROR)

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()

app = Flask(__name__)


@app.route('/', methods=['POST'])
def trololo():
    data = request.form
    if int(data['currency']) != 643: return "-1"
    platform, platform_id = data['label'].split('_')
    platform_id = int(platform_id)
    ctx = MessageContext(platform).setUserId(platform_id)
    amount = int(data['amount'])
    utils.sendmsg(platform, platform_id, f'Пришло пожертвование в {amount} рублей. Спасибо!')
    info_worker.add_donate(ctx, amount)
    return "thank you"


def start():
    app.run(host='0.0.0.0', port=80, threaded=True)
