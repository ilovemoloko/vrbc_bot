from bot_script import bot, generate_cart_str
from script_base import MessageBuilder, ButtonsBuilder, MessageContext
from db_worker import FSMDatabase, LocalUsersDatabase, DBInfoWorker, BCAccountDB

fsm_db = FSMDatabase()
local_user_db = LocalUsersDatabase()
info_worker = DBInfoWorker()
bca_db = BCAccountDB()


@bot.command("menu")
def menu_message(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Восстановление/Сохранение аккаунтов", "recovery_menu")
    buttons.add("Пресеты", "presets")
    buttons.add("Донаты", "donate")
    buttons.add("Бусты", "boosts")
    buttons.add("Помощь", "help")

    MessageBuilder().setText("Выберите пункт меню").setReplyMode(context).setButtons(buttons).reply()


@bot.command("presets")
def presets(context: MessageContext):
    buttons = ButtonsBuilder()
    message = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Список пресетов", "presets_list")
    buttons.add("Добавить прошлую корзину", "add_last_cart")
    buttons.add("Список функций", "menu")
    buttons.add("Перейти в корзину", "viewcart")
    message.setText("В этом меню вы можете сохранять шаблон корзины, чтобы потом быстро добавлять предметы в свой список").reply()


@bot.command("add_last_cart")
def add_last_cart(context: MessageContext):
    buttons = ButtonsBuilder()
    message = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Перейти в корзину", "viewcart")
    buttons.add("Вернуться", "presets")

    last_cart = info_worker.get_value(context, 'last_cart')

    item_queries = []
    for item in last_cart.splitlines():
        item_id, amount = item.split()
        item_queries.append((int(item_id), int(amount)))
    n = info_worker.mass_add_to_cart(context, item_queries)

    message.setText(f"Предметы из прошлой корзины ({n} штук) добавлены").reply()


@bot.command("presets_list")
def presets_list(context: MessageContext):
    buttons = ButtonsBuilder()
    message = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Меню пресетов", "presets")
    buttons.add("Добавить пресет в корзину", "add_preset_to_cart")
    buttons.add("Изменить пресет", "change_preset")
    message.setText("Ваши сохраненные пресеты: ")
    presets_ = info_worker.get_value(context, 'presets')
    for preset in presets_:
        p_name, p_cart = presets_[preset]
        message.addText(f"#{preset} - {p_name}")
    message.reply()


@bot.command("add_preset_to_cart")
def add_preset_to_cart(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Вернуться", "presets_list")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Напишите номер нужного пресета").reply()
    fsm_db.update_state(context, context.text)


@bot.command(".*", level="add_preset_to_cart", weak=True)
def add_preset_to_cart_2(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться", "presets_list")
    preset_id = context.text
    presets_array = info_worker.get_value(context, 'presets')
    if preset_id in presets_array:
        newcart_str = presets_array[preset_id][1]
        item_queries = []
        for item in newcart_str.splitlines():
            item_id, amount = item.split()
            item_queries.append((int(item_id), int(amount)))
        info_worker.mass_add_to_cart(context, item_queries)
        buttons.add("В Корзину", "viewcart")
        fsm_db.update_state(context, "*")
        return answer.addText("Пресет успешно добавлен в корзину").reply()
    answer.addText("Некорректный номер пресета").reply()


@bot.command("change_preset")
def change_preset(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Вернуться", "presets_list")
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    answer.addText("Напишите номер нужного пресета\n\nВ указанный пресет запишется ваша текущая корзина").reply()
    fsm_db.update_state(context, context.text)


@bot.command(".*", level="change_preset", weak=True)
def change_preset_2(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться", "presets_list")
    preset_id = context.text
    presets_array = info_worker.get_value(context, 'presets')
    if preset_id in presets_array:
        answer.addText("Напишите новое имя пресета").reply()
        fsm_db.update_state(context, f"change_preset_name {preset_id}")
    else:
        answer.addText("Некорректный номер пресета").reply()


@bot.command(".*", level="change_preset_name", weak=True)
def change_preset_name(context: MessageContext):
    buttons = ButtonsBuilder()
    answer = MessageBuilder().setReplyMode(context).setButtons(buttons)
    buttons.add("Вернуться", "presets_list")
    preset_name = context.text
    preset_id = context.fsm_full.split(" ", 1)[1]

    if len(preset_name) > 32:
        return answer.addText("Имя слишком длинное").reply()

    presets_array = info_worker.get_value(context, 'presets')
    if preset_id in presets_array:
        presets_array[preset_id] = (preset_name, generate_cart_str(info_worker.get_value(context, 'cart')))
        info_worker.set_value(context, 'presets', presets_array)
        fsm_db.update_state(context, "*")
        return answer.addText("Пресет успешно изменен").reply()
    else:
        return answer.addText("Внутренняя ошибка.").reply()


@bot.command("recovery_menu")
def recovery_menu(context: MessageContext):
    buttons = ButtonsBuilder()
    buttons.add("Восстановить аккаунт", "recovery_account")
    buttons.add("Сохранить аккаунт", "save_account")
    buttons.add("Вернуться в меню", "menu")
    MessageBuilder().setText("Выберите пункт меню").setReplyMode(context).setButtons(buttons).reply()
