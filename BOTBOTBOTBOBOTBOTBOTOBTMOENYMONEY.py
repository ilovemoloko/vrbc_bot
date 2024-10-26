from flask import Flask, request
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
import utils

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()

app = Flask(__name__)


@app.route('/', methods=['POST'])
def trololo():
    data = request.form
    if data['currency'] != 643: return "-1"
    user_id = data['label']
    amount = int(data['amount'])
    utils.sendmsg('Одноклассники', 'Путин', 'Вы молодец!!!')
    info_worker.add_donate(user_id, amount)
    return "thank you"


if __name__ == '__main__':
    app.run()
