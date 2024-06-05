import script_base as sc
from config import token_vk, id_vk
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from script_base import MessageBuilder
import random
import json


class VkBotScript(sc.BotScript):
    def __init__(self):
        super().__init__()
        self.vk_session = vk_api.VkApi(token=token_vk)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, id_vk)

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
            random_id=random.randint(0, 1000),
            keyboard=keyboard
        )

    def get_action(self):
        for action in self.longpoll.listen():
            if action.type == VkBotEventType.MESSAGE_NEW:
                obj = action.object
                peer_id = obj['peer_id']
                user_id = obj['from_id']
                text = obj['text']
                if "payload" in obj:
                    payload = json.loads(obj['payload'])
                    if "button" in payload:
                        return sc.MessageContext().setPeerId(peer_id).setText(payload["button"]).setUserId(user_id)

                res = sc.MessageContext()

                attachments = obj['attachments']
                if attachments:
                    for att in attachments:
                        if att['type'] != 'photo':
                            continue
                        for size in att['photo']['sizes']:
                            if size['type'] == 'x':
                                res.addPhoto(size['url'])
                                break

                return res.setPeerId(peer_id).setUserId(user_id).setText(text)
            break

    def get_name(self):
        return "VKScript"
