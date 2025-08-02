import config
import script_base as sc
from config import token_vk, id_vk
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from script_base import MessageBuilder, MessageContext
import random
import json
import threading
import traceback


class VkBotScript(sc.BotScript):
    def __init__(self):
        super().__init__()
        self.vk_session = vk_api.VkApi(token=token_vk)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, id_vk)

    def get_users(self, num):
        users = []
        offset = 0
        count_per_request = 200

        while len(users) < num:
            response = self.vk.messages.getConversations(count=count_per_request, offset=offset, filter="unread")
            dialogs = response['items']
            if not dialogs:
                break

            for dialog in dialogs:
                chat_id = dialog['conversation']['peer']['id']
                last_message = dialog['last_message']['text']
                users.append((chat_id, last_message))

                if len(users) >= num:
                    break

            offset += count_per_request

        return users[:num]

    def massmsg(self, user_ids, message):
        max_users = 100
        user_ids = [x for x in user_ids if x != 2000000023]

        while user_ids:
            try:
                user_ids_batch = user_ids[:max_users]
                self.vk.messages.send(user_ids=user_ids_batch, message=message, random_id=random.randint(1, 2147483647))
                user_ids = user_ids[max_users:]
            except Exception as e:
                print(e)

    def handle_action(self, action):
        t = threading.Thread(target=super().handle_action, args=(action,))
        t.start()

    def _get_user_description(self, context: MessageContext):
        user_id = context.user_id
        user_data = self.vk.users.get(user_id=user_id, fields="photo_200")[0]

        user_name = f"{user_data['first_name']} {user_data['last_name']}"
        photo_url = user_data['photo_200']
        return {"name": user_name, "image_url": photo_url}

    def _send_message(self, message: MessageBuilder):
        buttons = message.buttons
        keyboard = None
        attachment = None
        previewUrl = message.previewUrl
        if previewUrl:
            attachment = previewUrl[0]

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
            dont_parse_links=0,
            attachment=attachment
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
                res.setRawAction(action)

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
            elif action.type == VkBotEventType.GROUP_LEAVE:
                res = sc.MessageContext(self.get_name())
                obj = action.object
                user_id = obj['user_id']
                is_self = obj['self']
                if not is_self:
                    break

                res.setText("ileft").setUserId(user_id).setPeerId(user_id)
                res.setRawAction(action)
                res.trust(True)

                return res
            elif action.type == VkBotEventType.GROUP_JOIN:
                res = sc.MessageContext(self.get_name())
                obj = action.object
                user_id = obj['user_id']
                is_self = True
                if "self" in obj:
                    is_self = obj['self']
                if not is_self:
                    break

                res.setText("ijoin").setUserId(user_id).setPeerId(user_id)
                res.setRawAction(action)
                res.trust(True)

                return res
            break

    def get_name(self):
        return "vk"

    def start(self):
        try:
            userids = []
            for x in self.get_users(1000):
                userids.append(x[0])
            msg = "Бот перезапущен. Вы можете попробовать снова."
            self.massmsg(userids, msg)
        except Exception as e:
            print(traceback.format_exc())
        super().start()

    def get_group_members(self):
        members = self.vk.groups.getMembers(group_id=config.id_vk)
        count = members['count']
        offset = 1000
        members = members['items']
        print("+1000")
        while offset < count:
            members.extend(self.vk.groups.getMembers(group_id=config.id_vk, count=1000, offset=offset)['items'])
            offset += 1000
            print("+1000")
        print(f"Всего участников: {count}")
        return members

