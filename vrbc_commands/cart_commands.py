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


def _extract_cat_and_levels(text: str):
    if text is None:
        return None, (None, None)
    text = text.strip()
    if not text:
        return None, (None, None)
    m = re.match(r'^"([^"]+)"\s*(.*)$', text)
    if m:
        cat_part, rest = m.group(1).strip(), m.group(2).strip()
    else:
        parts = text.split(None, 1)
        cat_part = parts[0] if parts else None
        rest = parts[1].strip() if len(parts) > 1 else ""

    if not rest:
        return cat_part, (None, None)
    m2 = re.match(r'^(\d+)\s*\+\s*(\d+)$', rest)
    if m2:
        return cat_part, (int(m2.group(1)), int(m2.group(2)))
    m3 = re.match(r'^\+\s*(\d+)$', rest)
    if m3:
        return cat_part, (0, int(m3.group(1)))
    m4 = re.match(r'^(\d+)$', rest)
    if m4:
        return cat_part, (int(m4.group(1)), 0)
    return cat_part, (None, None)


@bot.command(["предметы", "cart", "!каталог.*", "каталог.*"], ignore_case=True)
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


@bot.command("selectcategory .*", level=["*", "additem"], weak="True")
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

    buttons.insert(0,"Добавить предмет", f"chooseitem {category_id}")
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
        if not user_bot_values['default_user']["is_member"]:
            answer.addText("Подпишитесь на группу, чтобы в вашей корзине было больше места")
        buttons.add("Начать взлом", "starthack").add("Убрать предмет из корзины", "removeitem").add("Назад", "cart")
        return answer.reply()

    if context.text.startswith("! добавить"):
        context.text = context.text[2:]
    command_parts = context.text.split(" ", 2)
    if len(command_parts) == 3:
        context.text = command_parts[2]
        if not command_parts[1].isnumeric():
            return answer.addText("Неправильно введено ID. Пожалуйста, напишите целое число.").reply()
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
            if not context.text.isnumeric():
                return answer.addText("Неправильно введено ID. Пожалуйста, напишите целое число.").reply()
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


@bot.command(["find_cat", "!поиск", "поиск"], level=["additem", "chooseitem", "*"], weak=True, ignore_case=True)
def find_cat(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Добавление кота", "return_27")
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
        buttons.insert(0, "Увеличить лимит", "boostshop")
        buttons.insert(0, "Добавить максимальное количество", f"chooseitem {item_id} {limit_amount}")
    fsm_db.update_state(context, f"additem {item_id}")
    if item_id == 27:
        answer.addText("Введите примерное имя кота (либо его ID), которого вы хотите добавить на аккаунт")
        buttons.insert(0, "Поиск котов", "find_cat")
    elif item_id == 48:
        answer.addText("Введите примерное имя кота (либо его ID), которого вы хотите прокачать")
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
    cat_id = utils.search_cat(text, info_worker.get_value(context, "japan_user"))
    answer.addText("Результаты поиска:\n")
    for i in cat_id:
        answer.addText(f" - {i[0]} (ID: {i[1]})")
    answer.reply()


@bot.command(r"find .*")
def find_cat(context: MessageContext):
    query = context.text.split(" ", 1)[1]
    context.text = query
    return find_cat_2(context)


@bot.command(r"setlocal.*")
def setlocal(context: MessageContext):
    arg = context.text.split(" ", 1)[1]
    value = False
    if arg == "ja":
        value = True

    info_worker.set_value(context, "japan_user", value)

    buttons = ButtonsBuilder()
    buttons.add("Смотреть категории предметов", "cart")
    buttons.add("Посмотреть корзину", "viewcart")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    answer.addText(f"Бот переключил ваш поиск котов на {arg} версию.")
    answer.reply()


def addcat(context: MessageContext):
    text = context.text
    item_id = 27
    items_data = info_worker.get_bot_values(context)['items'][item_id]
    buttons = ButtonsBuilder()
    buttons.add("Смотреть предметы", f"selectcategory {items_data[2]}")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    is_jp = info_worker.get_value(context, "japan_user")

    if text.isnumeric():
        cat_id = int(text)
    else:
        cat_id = utils.search_cat(text, is_jp)
        if len(cat_id) == 0:
            cat_id = -1
        else:
            cat_id = cat_id[0][1]

    cats_names = local_server.get_cats_names(is_jp=is_jp)
    if item_id == 27:
        if not str(cat_id) in cats_names:
            answer.addText("В базе данных бота пока что ещё нет такого кота\n")
            max_id = local_server.max_cat_ja
            if cat_id > max_id:
                return answer.reply()
            if not is_jp:
                buttons.add("Включить японский поиск", "setlocal ja")
                answer.addText("Этого кота нет в глобальной версии игры.\n"
                               "Если вы играете на японской версии, то вы можете попытаться добавить кота после включения японского поиска")
            else:
                buttons.add("Включить английский поиск", "setlocal en")
                answer.addText("Этого кота нет в японской версии игры.\n"
                               "Если вы играете на английской версии, то вы можете попытаться добавить кота после включения английского поиска")
            return answer.reply()

    buttons.insert(0, "Начать взлом", "starthack")
    buttons.insert(0, "Посмотреть корзину", "viewcart")
    icons = local_server.get_icons(is_jp=is_jp)
    if str(cat_id) not in icons:
        answer.addText("В базе данных бота пока что ещё нет такого кота\n")
        max_id = local_server.max_cat_ja
        if cat_id > max_id:
            return answer.reply()
        if not is_jp:
            buttons.add("Включить японский поиск", "setlocal ja")
            answer.addText("Этого кота нет в глобальной версии игры.\n"
                           "Если вы играете на японской версии, то вы можете попытаться добавить кота после включения японской версии поиска")
        else:
            buttons.add("Включить английскую версию поиска", "setlocal en")
            answer.addText("Этого кота нет в японской версии игры.\n"
                           "Если вы играете на английской версии поиска, то вы можете попытаться добавить кота после включения японской версии поиска")
        return answer.reply()

    fsm_db.update_state(context, f"chooseitem {items_data[2]}")
    info_worker.add_to_cart(context, item_id, cat_id)

    img = icons[str(cat_id)]
    answer.setPreviewUrl(img)
    return answer.addText(f"Кот {cats_names[str(cat_id)]} {cat_id} добавлен в корзину").reply()


@bot.command(".*", level="additem", weak=True)
def additem(context: MessageContext):
    text = context.text
    item_id = int(context.fsm[0])
    if item_id == 27:
        return addcat(context)
    if item_id == 48:
        return additem48(context)
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


def addItemStr(message: MessageBuilder, amount, item_name, item_id, start="\n -- ", show_id=True, cats_names=None):
    id_text = f" (ID: {item_id})" if show_id else ""
    if item_id == 48:
        try:
            parts = str(amount).split()
            if len(parts) >= 3:
                cat_id, base, plus = parts[0], parts[1], parts[2]
                name = cats_names.get(str(cat_id), '???') if cats_names is not None else '???'
                message.addText(f"Прокачка кота {name} #{cat_id} на {base}+{plus} уровней", start=start)
            else:
                # fallback
                message.addText(str(amount), start=start)
                message.addText(item_name, start=" ")
        except Exception:
            message.addText(str(amount), start=start)
            message.addText(item_name, start=" ")
        if show_id:
            message.addText(f"{id_text}", start=" ")
        return message

    if item_id == 27:
        if cats_names is not None:
            name = cats_names.get(str(amount), '???') if cats_names is not None else '???'
            message.addText(f"Получение кота {name} #{amount}", start=start)
    else:
        message.addText(f"{amount}", start=start)
        message.addText(f"{item_name}", start=" ")
    if show_id:
        message.addText(f"{id_text}", start=" ")
    return message


def addCart(answer, cart, items_info, only_item=None, show_id=True):
    changed = False
    cats_names = local_server.get_cats_names(is_jp=info_worker.get_value(answer.context, "japan_user"))
    for i in cart:
        item_info = items_info[i]
        item_name = item_info[1]
        item_id = i
        if not (item_id == only_item or only_item is None):
            continue
        if isinstance(cart[i], list):
            for j in cart[i]:
                addItemStr(answer, j, item_name, item_id, show_id=show_id, cats_names=cats_names)
                changed = True
        else:
            addItemStr(answer, cart[i], item_name, item_id, show_id=show_id, cats_names=cats_names)
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
    answer.addText(f"\nЗаполненность корзины: {cart_size} из {max_cart_size} предметов")
    if not user_bot_values["is_member"]:
        answer.addText("Подпишитесь на группу, чтобы в вашей корзине было больше места")
    answer.reply()


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


@bot.command(".*", level="additem48_levels", weak=True)
def additem48_levels(context: MessageContext):
    cat_part = context.fsm[0]
    text = context.text.strip()
    item_id = 48

    if not text:
        base = 0
        plus = 0
    else:
        m2 = re.match(r'^(\d+)\s*\+\s*(\d+)$', text)
        if m2:
            base = int(m2.group(1)); plus = int(m2.group(2))
        else:
            m3 = re.match(r'^\+\s*(\d+)$', text)
            if m3:
                base = 0; plus = int(m3.group(1))
            else:
                m4 = re.match(r'^(\d+)$', text)
                if m4:
                    base = int(m4.group(1)); plus = 0
                else:
                    # fallback: maybe user provided both cat and levels in one line
                    _, (base, plus) = _extract_cat_and_levels(text)

    if base is None and plus is None:
        buttons = ButtonsBuilder()
        buttons.add("Посмотреть корзину", "viewcart")
        buttons.add("Смотреть категории предметов", "cart")
        return MessageBuilder().setReplyMode(context).setButtons(buttons).addText('Неправильный формат уровней. Используйте: 1+10, +10 или 1').reply()

    is_jp = info_worker.get_value(context, 'japan_user')
    if str(cat_part).isnumeric():
        cat_id = int(cat_part)
    else:
        search = utils.search_cat(cat_part, is_jp)
        if not search:
            buttons = ButtonsBuilder()
            buttons.add("Искать ещё раз", "find_cat")
            buttons.add("Посмотреть корзину", "viewcart")
            return MessageBuilder().setReplyMode(context).setButtons(buttons).addText('Кот не найден').reply()
        cat_id = search[0][1]

    buttons = ButtonsBuilder()
    buttons.insert(0, 'Начать взлом', 'starthack')
    buttons.insert(0, 'Посмотреть корзину', 'viewcart')

    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    base = base or 0
    plus = plus or 0

    user_bot_values = info_worker.get_bot_values(context)
    spendable_boosts = info_worker.get_value(context, 'spendable_boosts')
    boosts_server = user_bot_values['boosts']
    user_cart = info_worker.get_value(context, "cart")
    spending = info_worker.get_spendable_amount(None, user_cart.get(item_id, []), set(str(cat_id)))
    limit_spend = info_worker.get_limit_spend(spendable_boosts, item_id, boosts_server)

    res = info_worker.add_to_cart(context, 48, f'{cat_id} {base} {plus}')
    if not res:
        answer.addText(f'У вас недостаточно доступных уровней для добавления такой прокачки.\n'
                       f'Убедитесь, что сумма уровней котов в корзине не превышает доступное вам число\n\n'
                       f'Текущая сумма в корзине: {spending} (всего доступно {limit_spend})')
        return answer.reply()
    spending += base + plus

    cats_names = local_server.get_cats_names(is_jp=is_jp)
    icons = local_server.get_icons(is_jp=is_jp)

    if str(cat_id) not in icons:
        answer.addText('В базе данных бота пока что ещё нет такого кота\n')
        max_id = local_server.max_cat_ja
        if cat_id > max_id:
            return answer.reply()
        buttons.add('Включить японский поиск', 'setlocal ja' if not is_jp else 'setlocal en')
        answer.addText('Этого кота нет в нужной версии игры. Попробуйте переключить поиск')
        return answer.reply()
    img = icons.get(str(cat_id))

    if img:
        answer.setPreviewUrl(img)
    name = cats_names.get(str(cat_id), '???')
    answer.addText(f'Прокачка кота {name} {cat_id} (уровни {base}+{plus}) добавлена в корзину\n\n'
                   f'Всего в корзине улучшений на {spending} уровней, '
                   f'доступно ещё {limit_spend-spending}').reply()
    fsm_db.update_state(context, '*')


def additem48(context: MessageContext):
    text = context.text.strip()
    item_id = 48
    user_bot_values = info_worker.get_bot_values(context)
    items_data = user_bot_values['items'][item_id]
    buttons = ButtonsBuilder()
    buttons.insert(0, 'Начать взлом', 'starthack')
    buttons.insert(0, 'Посмотреть корзину', 'viewcart')
    buttons.add('Смотреть предметы', f'selectcategory {items_data[2]}')
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)

    cat_part, levels = _extract_cat_and_levels(text)
    base, plus = levels if levels != (None, None) else (None, None)
    is_jp = info_worker.get_value(context, 'japan_user')
    if cat_part is None:
        fsm_db.update_state(context, f'additem48_levels {""}')
        context.fsm = [""]
        answer.addText('Введите ID или имя кота')
        return answer.reply()

    if str(cat_part).isnumeric():
        cat_id = int(cat_part)
    else:
        search = utils.search_cat(cat_part, is_jp)
        if not search:
            if base is None and plus is None:
                fsm_db.update_state(context, f'additem48_levels {cat_part}')
                context.fsm = [cat_part]
                answer.addText('Кот не найден. Введите корректный ID или имя кота')
                return answer.reply()
            return answer.addText('Кот не найден').reply()
        cat_id = search[0][1]

    icons = local_server.get_icons(is_jp=is_jp)
    if str(cat_id) not in icons:
        answer.addText('В базе данных бота пока что ещё нет такого кота\n')
        max_id = local_server.max_cat_ja
        if cat_id > max_id:
            return answer.reply()
        buttons.add('Включить японский поиск', 'setlocal ja' if not is_jp else 'setlocal en')
        answer.addText('Этого кота нет в нужной версии игры. Попробуйте переключить поиск')
        return answer.reply()

    if base is None and plus is None:
        fsm_db.update_state(context, f'additem48_levels {cat_part}')
        context.fsm = [cat_part]
        answer.addText('Введите уровни в формате: 1+10, +10 или 1 (base+plus)')
        return answer.reply()

    base = base or 0
    plus = plus or 0

    spendable_boosts = info_worker.get_value(context, 'spendable_boosts')
    boosts_server = user_bot_values['boosts']
    user_cart = info_worker.get_value(context, "cart")
    spending = info_worker.get_spendable_amount(None, user_cart.get(item_id, []), set(str(cat_id)))
    limit_spend = info_worker.get_limit_spend(spendable_boosts, item_id, boosts_server)

    res = info_worker.add_to_cart(context, item_id, f'{cat_id} {base} {plus}')
    if not res:
        answer.addText(f'У вас недостаточно доступных уровней для добавления такой прокачки.\n'
                       f'Убедитесь, что сумма уровней котов в корзине не превышает доступное вам число\n\n'
                       f'Текущая сумма в корзине: {spending} (всего доступно {limit_spend})')
        return answer.reply()
    spending += base + plus

    cats_names = local_server.get_cats_names(is_jp=is_jp)
    img = icons[str(cat_id)]
    answer.setPreviewUrl(img)
    name = cats_names.get(str(cat_id), '???')
    answer.addText(f'Прокачка кота {name} {cat_id} (уровни {base}+{plus}) добавлена в корзину\n\n'
                   f'Всего в корзине улучшений на {spending} уровней, '
                   f'доступно ещё {limit_spend-spending}').reply()
    fsm_db.update_state(context, '*')
