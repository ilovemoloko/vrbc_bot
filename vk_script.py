import script_base as sc
from config import token_vk, id_vk
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from script_base import MessageBuilder
import random


class VkBotScript(sc.BotScript):
    def __init__(self):
        super().__init__()
        self.vk_session = vk_api.VkApi(token=token_vk)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, id_vk)

    def send_message(self, message: MessageBuilder):
        self.vk.messages.send(
            peer_id=message.peerId,
            message=message.text,
            random_id=random.randint(0, 1000)
        )

    def get_action(self):
        for action in self.longpoll.listen():
            if action.type == VkBotEventType.MESSAGE_NEW:
                obj = action.object
                peer_id = obj['peer_id']
                user_id = obj['from_id']
                text = obj['text']
                return sc.MessageContext().setPeerId(peer_id).setUserId(user_id).setText(text)
            break

    def get_name(self):
        return "VKScript"