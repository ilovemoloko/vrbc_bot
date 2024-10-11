from bot_script import bot
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB
import local_server
import utils
import re

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


@bot.command(["предметы", "cart"], ignore_case=True)
def cart(context: MessageContext):
    fsm_db.update_state(context, "*")
    buttons = ButtonsBuilder()
    answer = (MessageBuilder().setReplyMode(context)
              .setText("Вы можете выбрать предметы из представленных категорий\n\n"
                       "Если вы хотите увидеть список предметов из всех каталогов, "
                       "то используйте команду Список").setButtons(buttons))

    categories = info_worker.get_bot_values(context)['categories']
    for i in categories:
        buttons.add(categories[i], f"selectcategory {i}")
    answer.reply()


@bot.command("selectcategory \\d+", level=["*", "chooseitem"])
def selectcategory(context: MessageContext):
    category_id = context.text.split()[1]
    if category_id == "all":
        return allcategories(context)

    buttons = ButtonsBuilder()
    buttons.add("Корзина", "viewcart")
    buttons.add("Назад", "cart")

    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    bot_values = info_worker.get_bot_values(context)
    category_id = int(category_id)
    if category_id not in bot_values['categorized']:
        return answer.setText("Такой категории нет").reply()
    category_items = bot_values['categorized'][category_id]
    category_name = bot_values['categories'][category_id]

    buttons.add("Добавить предмет", f"chooseitem {category_id}")
    fsm_db.update_state(context, f"chooseitem {category_id}")

    answer.addText(f"Категория \"{category_name}\"\nЕсли вы хотите увидеть список предметов из всех каталогов, то используйте команду Список", start="")
    for i in category_items:
        answer.addText(f"{category_items[i][1]} (ID: {i})")

    answer.reply()


@bot.command(["allcategories", "!список", "список"], ignore_case=True)
def allcategories(context: MessageContext):
    fsm_db.update_state(context, "chooseitem all")

    buttons = ButtonsBuilder()
    buttons.add("Добавить предмет", f"chooseitem all")
    buttons.add("Корзина", "viewcart")
    buttons.add("Назад", "cart")

    bot_values = info_worker.get_bot_values(context)

    categories = bot_values['categories']
    answer = MessageBuilder().setReplyMode(context)
    for cat in categories:
        cat_items = bot_values['categorized'][cat]
        for i in cat_items:
            answer.addText(f"{cat_items[i][1]} (ID: {i})")

    answer.setButtons(buttons)
    answer.reply()


@bot.command(["chooseitem \\d+", "!добавить.*", "добавить.*", "chooseitem.*", "! добавить.*", "! Добавить.*"], level=["*", "additem"], weak=True, ignore_case=True)
def chooseitem(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    user_bot_values = info_worker.get_bot_values(context)

    cart_size = info_worker.get_cart_size(context)
    if cart_size >= info_worker.get_value(context, 'cart_size', src=user_bot_values['default_user']):
        answer.addText("Корзина переполнена")
        buttons.add("Начать взлом", "starthack").add("Убрать предмет из корзины", "removeitem").add("Назад", "cart")
        return answer.reply()

    if context.text.startswith("! добавить"):
        context.text = context.text[2:]
    command_parts = context.text.split()
    if len(command_parts) == 3:
        context.text = command_parts[2]
        item_id = int(command_parts[1])
        if item_id not in user_bot_values["items"]:
            buttons.add("Список предметов", "cart")
            return answer.addText("Такого предмета нет в каталоге. Попробуйте еще раз.").reply()
        fsm_db.update_state(context, f"additem {item_id}")
        context.fsm = [command_parts[1]]
        return additem(context)
    elif len(command_parts) == 2:
        if not command_parts[0] == "chooseitem":
            context.text = command_parts[1]
            item_id = int(context.text)
            if item_id not in user_bot_values["items"]:
                buttons.add("Список предметов", "cart")
                return answer.addText("Такого предмета нет в каталоге. Попробуйте еще раз.").reply()
            category_id = user_bot_values["items"][item_id][2]
            fsm_db.update_state(context, f"chooseitem {category_id}")
            context.fsm = [str(category_id)]
            return chooseitem2(context)

    if not context.text.startswith("chooseitem"):
        buttons.add("Список предметов", "cart")
        context.text = "chooseitem 1"
    fsm_db.update_state(context, context.text)

    answer.addText("Напишите ID нужного вам предмета").reply()


@bot.command("return_27", level=["find_cat_2", "additem"], weak=True)
def return_27(context: MessageContext):
    context.fsm = [6]
    context.text = "27"
    chooseitem2(context)


@bot.command("find_cat", level=["additem", "chooseitem"], weak=True)
def find_cat(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Назад", "return_27")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Введите примерное имя кота (либо его ID), которого вы хотите найти")
    answer.reply()
    fsm_db.update_state(context, "find_cat_2")


@bot.command(".*", level="chooseitem", weak=True)
def chooseitem2(context: MessageContext):
    text = context.text
    category_id = context.fsm[0]

    buttons = ButtonsBuilder()
    buttons.add("Назад", f"selectcategory {category_id}")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    result = re.search(r"\d+", text)
    if not result:
        return answer.addText("Неправильно введено ID. Пожалуйста, напишите целое число.").reply()

    item_id = int(result.group(0))
    items_data = info_worker.get_bot_values(context)['items']

    if item_id not in items_data:
        return answer.addText("Такого предмета нет в каталоге. Попробуйте еще раз.").reply()

    limit_amount = items_data[item_id][0]
    if limit_amount != "Нет":
        buttons.insert(0, "Добавить максимальное количество", f"chooseitem {item_id} {limit_amount}")
    fsm_db.update_state(context, f"additem {item_id}")
    if item_id == 27:
        answer.addText("Введите примерное имя кота (либо его ID), которого вы хотите добавить на аккаунт")
        buttons.insert(0, "Поиск котов", "find_cat")
    else:
        answer.addText(f"Введите количество предмета, которое вы хотите добавить на аккаунт\n")
        answer.addText(f"Лимит: {limit_amount}")
    answer.reply()


@bot.command(".*", level="find_cat_2", weak=True)
def find_cat_2(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Искать ещё раз", "find_cat")
    buttons.add("Добавить кота", "return_27")

    text = context.text
    cat_id = utils.search_cat(text)
    answer.addText("Результаты поиска:\n")
    for i in cat_id:
        answer.addText(f" - {i[0]} (ID: {i[1]})")
    answer.reply()

    fsm_db.update_state(context, "additem 27")


@bot.command(r"find .*", ignore_case=True)
def find_cat(context: MessageContext):
    query = context.text.split(" ", 1)[1]
    context.text = query
    return find_cat_2(context)


def addcat(context: MessageContext):
    text = context.text
    item_id = 27
    items_data = info_worker.get_bot_values(context)['items'][item_id]
    buttons = ButtonsBuilder()
    buttons.add("Смотреть предметы", f"selectcategory {items_data[2]}")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    if text.isnumeric():
        cat_id = int(text)
    else:
        cat_id = utils.search_cat(text)
        if len(cat_id) == 0:
            cat_id = -1
        else:
            cat_id = cat_id[0][1]

    if item_id == 27:
        if not (str(cat_id) in local_server.cats_names):
            return answer.addText("В базе данных бота пока что ещё нет такого кота").reply()

    fsm_db.update_state(context, f"chooseitem {items_data[2]}")
    info_worker.add_to_cart(context, item_id, cat_id)

    buttons.insert(0, "Начать взлом", "starthack")
    buttons.insert(0, "Посмотреть корзину", "viewcart")
    img = local_server.cats_icons[str(cat_id)]
    answer.setPreviewUrl(img)
    return answer.addText(f"Кот {local_server.cats_names[str(cat_id)]} {cat_id} добавлен в корзину").reply()


@bot.command(".*", level="additem", weak=True)
def additem(context: MessageContext):
    text = context.text
    item_id = int(context.fsm[0])
    if item_id == 27:
        return addcat(context)
    items_data = info_worker.get_bot_values(context)['items'][item_id]

    buttons = ButtonsBuilder()
    buttons.add("Смотреть предметы", f"selectcategory {items_data[2]}")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    result = re.search(r"\d+", text)
    if not result:
        return answer.addText("Неправильно введено количество. Пожалуйста, напишите целое число").reply()

    amount = int(result.group(0))
    if items_data[0] != "Нет":
        if amount > items_data[0]:
            amount = items_data[0]
            answer.addText("Вы превысили лимит, поэтому в корзину будет добавлено максимальное количество\n")

    info_worker.add_to_cart(context, item_id, amount)
    fsm_db.update_state(context, f"chooseitem {items_data[2]}")
    buttons.insert(0, "Начать взлом", "starthack")
    buttons.insert(0, "Посмотреть корзину", "viewcart")

    answer.addText(f"Предмет {items_data[1]} ({amount}) добавлен в корзину").reply()


def addItemStr(message: MessageBuilder, amount, item_name, item_id, start="\n -- ", show_id=True):
    id_text = f" (ID: {item_id})" if show_id else ""
    message.addText(f"{amount}", start=start)
    message.addText(f"{item_name}", start=" ")
    if item_id == 27:
        message.addText(f"{local_server.cats_names[str(amount)]}", start=" ")
    if show_id:
        message.addText(f"{id_text}", start=" ")
    return message


def addCart(answer, cart, items_info, only_item=None, show_id=True):
    changed = False
    for i in cart:
        item_info = items_info[i]
        item_name = item_info[1]
        item_id = i
        if not (item_id == only_item or only_item is None):
            continue
        if isinstance(cart[i], list):
            for j in cart[i]:
                addItemStr(answer, j, item_name, item_id, show_id=show_id)
                changed = True
        else:
            addItemStr(answer, cart[i], item_name, item_id, show_id=show_id)
            changed = True
    return changed


@bot.command(["viewcart", "корзина", "!корзина"], level=["*", "starthack_agreement"], ignore_case=True)
def viewcart(context: MessageContext):
    fsm_db.update_state(context, "*")
    buttons = ButtonsBuilder()
    buttons.add("Смотреть категории предметов", "cart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    user_bot_values = info_worker.get_bot_values(context)['default_user']

    cart = info_worker.get_value(context, 'cart')
    items_info = info_worker.get_bot_values(context)['items']
    cart_size = info_worker.get_cart_size(context)
    max_cart_size = info_worker.get_value(context, 'cart_size', src=user_bot_values)

    if len(cart) == 0:
        answer.addText("Корзина пуста")
    else:
        buttons.add("Начать взлом", "starthack")
        buttons.add("Убрать предмет", "removeitem")
        answer.addText("Ваша корзина:\n")
        addCart(answer, cart, items_info)

    buttons.add("Бусты", "boosts")
    buttons.add("Больше функций/Помощь", "menu")
    answer.addText(f"\nЗаполненность корзины: {cart_size} из {max_cart_size} предметов").reply()


@bot.command(["removeitem", "!убрать.*", "убрать.*"], ignore_case=True)
def removeitem(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Убрать всё", "remove_all")
    buttons.add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    if info_worker.get_cart_size(context) == 0:
        answer.addText("Корзина пуста")
    else:
        answer.addText("Напишите ID нужного вам предмета")
        if not context.text.startswith("removeitem"):
            context.text = "removeitem"
        fsm_db.update_state(context, context.text)
    answer.reply()


@bot.command("remove_all")
def remove_all(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Да, убрать всё", "remove_all_conf")
    buttons.add("Назад", "removeitem")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    answer.addText("Вы уверены, что хотите очистить корзину?").reply()


@bot.command("remove_all_conf")
def remove_all_conf(context: MessageContext):
    info_worker.clear_cart(context)
    viewcart(context)


@bot.command(".*", level="removeitem", weak=True)
def removeitem(context: MessageContext):
    regex = re.search(r"\d+", context.text)
    buttons = ButtonsBuilder().add("Убрать всё", "remove_all").add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    if not regex:
        return answer.addText("Неправильно введен ID предмета").reply()

    item_id = int(regex.group(0))
    if item_id not in info_worker.get_value(context, 'cart'):
        return answer.addText("Такого предмета нет в корзине").reply()

    items_info = info_worker.get_bot_values(context)['items']
    stackable = info_worker.check_stackable(items_info[item_id])

    if stackable:
        if len(info_worker.get_value(context, 'cart')[item_id]) > 1:
            answer.addText("Пожалуйста, уточните какой именно предмет вы хотите удалить из корзины (Укажите число)\n")
            addCart(answer, info_worker.get_value(context, 'cart'), items_info, item_id, show_id=False)
            fsm_db.update_state(context, f"removeitem2 {item_id}")
            return answer.reply()

    info_worker.del_from_cart(context, item_id)
    fsm_db.update_state(context, "*")
    answer.addText("Предмет удален из корзины").reply()


@bot.command(".*", level="removeitem2", weak=True)
def removeitem2(context: MessageContext):
    regex = re.search(r"\d+", context.text)
    buttons = ButtonsBuilder().add("Вернуться в корзину", "viewcart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    if not regex:
        return answer.addText("Пожалуйста, введите число").reply()

    item_id = int(context.fsm[0])

    res = info_worker.del_from_cart(context, item_id, int(regex.group(0)))
    if res:
        fsm_db.update_state(context, "*")
        answer.addText("Предмет удален из корзины")
    else:
        answer.addText("Такого предмета нет в корзине")
    answer.reply()
