import script_base as sc
from config import token_vk, id_vk
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from script_base import MessageBuilder
import random
import json
import threading


class VkBotScript(sc.BotScript):
    def __init__(self):
        super().__init__()
        self.vk_session = vk_api.VkApi(token=token_vk)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, id_vk)

    def handle_action(self, action):
        t = threading.Thread(target=super().handle_action, args=(action,))
        t.start()

    def send_message(self, message: MessageBuilder):
        buttons = message.buttons
        keyboard = None

        if buttons:
            buttons_vk = []
            for b in buttons.buttons:
                buttons_vk.append([{
                    "action": {
                        "type": "text",
                        "payload": json.dumps({"button": b["payload"]}),
                        "label": b["text"]
                    }
                }])
            keyboard = {
                "one_time": False,
                "buttons": buttons_vk,
                "inline": True
            }
            keyboard = json.dumps(keyboard)
        self.vk.messages.send(
            peer_id=message.peerId,
            message=message.text,
            random_id=random.randint(-100000000, 10000000),
            keyboard=keyboard,
            dont_parse_links=False
        )

    def get_action(self):
        for action in self.longpoll.listen():
            if action.type == VkBotEventType.MESSAGE_NEW:
                res = sc.MessageContext(self.get_name())
                obj = action.object['message']
                peer_id = obj['peer_id']
                user_id = obj['from_id']
                text = obj['text']
                res.setText(text).setPeerId(peer_id).setUserId(user_id)

                if "payload" in obj:
                    payload = json.loads(obj['payload'])
                    if "button" in payload:
                        return res.setText(payload["button"])

                attachments = obj['attachments']
                if attachments:
                    for att in attachments:
                        if att['type'] != 'photo':
                            continue
                        for size in att['photo']['sizes']:
                            if size['type'] == 'y':
                                res.addPhoto(size['url'])
                                break

                return res
            break

    def get_name(self):
        return "vk"
