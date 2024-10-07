import discord
from discord.ext import commands
import vk_api
import telebot
import json
from config import token_tg, token_vk, discord_config

intents = discord.Intents.default()
intents.all()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)
client.remove_command('help')

tgbot = telebot.TeleBot(token_tg)
vk = vk_api.VkApi(token=token_vk)


def sendvk(place, text, is_end=False):
    buttons_vk = []
    buttons_vk.append([{
        "action": {
            "type": "text",
            "payload": json.dumps({"button": "startfight"}),
            "label": "Ответить"
        }
    }])

    keyboard = {
        "one_time": False,
        "buttons": buttons_vk,
        "inline": True
    }
    keyboard = json.dumps(keyboard)
    if not is_end:
        vk.method("messages.send", {"peer_id": place, "message": text, "random_id": 0, 'keyboard': keyboard})
    else:
        vk.method("messages.send", {"peer_id": place, "message": text, "random_id": 0})


def sendtg(place, text, is_end=False):
    keyboard = telebot.types.InlineKeyboardMarkup()
    label = "Ответить"
    pl = "startfight"
    keyboard.add(telebot.types.InlineKeyboardButton(label, callback_data=pl))
    if not is_end:
        tgbot.send_message(chat_id=place, text=text, reply_markup=keyboard)
    else:
        tgbot.send_message(chat_id=place, text=text)


@client.event
async def on_message(ctx):
    if ctx.author.id == client.user.id: return
    if ctx.channel.category and ctx.channel.category.name == "закрыто": return
    if ctx.content.startswith("!"): return await client.process_commands(ctx)
    peerId, platform = ctx.channel.topic.split(" ")
    content = ctx.content
    if platform == "tg":
        sendtg(peerId, content)
    else:
        sendvk(peerId, content)
    await ctx.add_reaction("👍")


@client.command()
async def close(ctx):
    await ctx.message.channel.edit(category=discord.utils.get(ctx.guild.channels, name="закрыто"))
    peerId, platform = ctx.channel.topic.split(" ")
    txt = "Администратор прекратил беседу. Все дальнейшие сообщения передаваться не будут."
    if platform == "tg":
        sendtg(peerId, txt, True)
    else:
        sendvk(peerId, txt, True)
    await ctx.send("Обсуждение закрыто. Все дальнейшие сообщения не будут передаваться пользователю (и наоборот)")


@client.command(description="Yes", aliases=['evalbutbetter', 'superstronkcommand', 'aaaaaaaaaaaaaaaaa'])
async def idk(ctx, mode, *, command=""):
    peerId, platform = ctx.channel.topic.split(" ")
    try:
        command = command.replace("-t", "   ")
        command = command.replace("context", str(peerId))
        if mode == "1":
            await ctx.send(str(eval(command)).replace('lkhjkhwjlkhrejwharjkhawkrhkawjrnla', "no"))

        elif mode == "2":
            exec(command)
            await ctx.send("Successful")

        elif mode == "3":
            async def aexec(code, ctx):
                exec(
                    'async def __ex(ctx): ' +
                    ''.join('\n {0}'.format(l) for l in code.split('\n'))
                )
                return await locals()['__ex'](ctx)

            x = await aexec(command, ctx)
            await ctx.send(x or '.')
    except Exception as e:
        await ctx.send("```" + str(repr(e)) + "```")


client.run(discord_config()["token"])
