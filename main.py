import ssl
import threading
import time

import telebot

import markups
from sheet_handler import *

# авторизация, запуск
bot = telebot.TeleBot('6865566493:AAEkaaZZwEcmqXvdkpxG3gYzohECLmoDzR0')
if client.spreadsheet_titles() == ['Бухгалтерия2']:
    print('Бот успешно подключился к таблице.')

# набор состояний
USER_STATE = {}
(PR_OUT_STATE, PR_IN_STATE, AWAITING_STATE, DEFAULT_STATE, NAME_STATE, PRICE_STATE, UNIT_STATE,
 AMOUNT_STATE, BUYER_NAME_STATE, PRODUCTION_REPORT_STATE,
 SELL_PRICE_STATE, SELLER_NAME_STATE, RESPONSIBLE_STATE) = range(13)
operation_type = None
TIMEOUT = 60

# глобальные переменные, существующие для контроля количества пользователей, одновременно работающих с ботом
# (макс. 1 user)
is_busy = False
current_user = None
timer = None

# для работы с float
NEAR_ZERO = 0.00000001


def set_state(user_id, state):
    USER_STATE[user_id] = state


def get_state(user_id):
    return USER_STATE.get(user_id, None)


# функция попытки удаления для преотвращения крашей программы, связанных с задержкой соединения
def try_delete(message, response=None):
    try:
        if response is None:
            bot.delete_message(message.chat.id, message.message_id)
        else:
            bot.delete_message(message.chat.id, response.message_id)
    except Exception as exc:
        print(exc)
        print('failed to delete')


# функция отмены операции и перехода в дефолтное состояние
def cancel(message):
    if operation_type == 'production' or operation_type == 'production_in':
        for stage in range(globals.production_count):
            point_to_empty_op()
            clear_row(globals.curr_row - 1)
        globals.reset_production()
    clear(operation)
    set_state(message.from_user.id, DEFAULT_STATE)
    handle_default_state(message)


# функция "спросить наименование" и дальнейший переход в NAME_STATE
def ask_name(call, text=None):
    try:
        call.message
    except AttributeError:
        call.message = call  # если вызываем не из callback-меню, а уже в процессе производственного этапа
    if text is None:
        bot.send_message(call.message.chat.id, 'Введите, пожалуйста, наименование товара.',
                         reply_markup=markups.item_markup)
    else:
        bot.send_message(call.message.chat.id, text, reply_markup=markups.item_markup)
    set_state(call.from_user.id, NAME_STATE)


def ask_names(call):
    try:
        call.message
    except AttributeError:
        call.message = call  # если вызываем не из callback-меню, а уже в процессе производственного этапа
    rows = [int(row) for row in op_sheet.get_col(aa, include_tailing_empty=False)][:-1]
    production_stage = int(get_production_stage()) + 1 if globals.production_count <= 0 else int(get_production_stage())
    stock_markup = telebot.types.ReplyKeyboardMarkup()
    if len(rows) > 0:
        for row in rows:
            row_data = op_sheet.get_row(row, include_tailing_empty=False)
            stock_markup.add(telebot.types.KeyboardButton(f'{row_data[f - 1]} | '
                                                          f'{row_data[e - 1]}'))
        if globals.production_count > 0:
            stock_markup.add(telebot.types.KeyboardButton('✅ Подтвердить товары на отправку в производство'))
        stock_markup.add(telebot.types.KeyboardButton('❌ Отмена'))
        bot.send_message(call.message.chat.id, f'Введите, пожалуйста, наименование товара, '
                                               f'который Вы хотите отправить '
                                               f'в производство. Текущий производственный этап: {production_stage}',
                         reply_markup=stock_markup)
        set_state(call.from_user.id, NAME_STATE)
    else:
        bot.send_message(call.message.chat.id,
                         'Извините, сейчас на складе нет остатков, невозможно отправить в производство.')
        cancel(call.message)


# функция "спросить единицу измерения" и дальнейший переход в UNIT_STATE
def ask_unit(message, text):
    bot.send_message(message.chat.id, text, reply_markup=markups.unit_markup)
    set_state(message.from_user.id, UNIT_STATE)


# функция "спросить цену" и дальнейший переход в PRICE_STATE
def ask_price(message, text):
    markup = telebot.types.ReplyKeyboardMarkup()
    suggested_price = find_suggested_price(operation['name'])
    if suggested_price != '':
        markup.add(un_convert_float(suggested_price))
    markup.add(telebot.types.KeyboardButton('❌ Отмена'))
    bot.send_message(message.chat.id, text,
                     reply_markup=markup)
    set_state(message.from_user.id, PRICE_STATE)


# -//-
def ask_amount(message, text):
    bot.send_message(message.chat.id, text,
                     reply_markup=markups.cancel_markup)
    set_state(message.from_user.id, AMOUNT_STATE)


# функция "спросить количество товара на продажу" и переход в AMOUNT_STATE
def ask_amount_sell(message, text):
    bot.send_message(message.chat.id, text,
                     reply_markup=markups.cancel_markup)
    set_state(message.from_user.id, AMOUNT_STATE)


# -//-
def ask_buyer_name(message, text):
    bot.send_message(message.chat.id, text,
                     reply_markup=markups.buyer_markup)
    set_state(message.from_user.id, BUYER_NAME_STATE)


# -//-
def ask_sell_price(message, text):
    bot.send_message(message.chat.id, text,
                     reply_markup=markups.cancel_markup)
    set_state(message.from_user.id, SELL_PRICE_STATE)


# -//-
def ask_responsible(message, text):
    bot.send_message(message.chat.id, text,
                     reply_markup=markups.employee_markup)
    set_state(message.from_user.id, RESPONSIBLE_STATE)


# -//-
def ask_seller(message, text):
    bot.send_message(message.chat.id, text,
                     reply_markup=markups.seller_markup)
    set_state(message.from_user.id, SELLER_NAME_STATE)


def ask_production_report(call, text=None):
    try:
        call.message
    except AttributeError:
        call.message = call
    rows = [int(row) for row in op_sheet.get_col(ab, include_tailing_empty=False)][1:]
    production_markup = telebot.types.ReplyKeyboardMarkup()
    if len(rows) > 0:
        for row in rows:
            row_data = op_sheet.get_row(row, include_tailing_empty=False)
            production_stage = row_data[d - 1]
            production_good = row_data[e - 1]
            production_amount = row_data[j - 1]
            production_unit = row_data[i - 1]
            button_text = f'{production_stage} | {production_good} | {production_amount} {production_unit}'
            globals.production_pos[production_stage] = row
            production_markup.add(
                telebot.types.KeyboardButton(button_text))
            globals.production_set.add(button_text)
        production_markup.add(telebot.types.KeyboardButton('❌ Отмена'))
        if text is None:
            bot.send_message(call.message.chat.id, 'Выберите производственный этап, который Вы хотите просмотреть.',
                             reply_markup=production_markup)
        else:
            bot.send_message(call.message.chat.id, text,
                             reply_markup=production_markup)
        set_state(call.from_user.id, PRODUCTION_REPORT_STATE)
    else:
        bot.send_message(call.message.chat.id,
                         'Извините, на складе ничего не произведено.')
        cancel(call.message)


def timeout():
    global is_busy, operation_type, current_user, timer
    operation_type = None
    clear(operation)
    if current_user is not None:
        print(f"Сессия истекла. Истекший пользователь: {current_user}.")
        set_state(current_user, AWAITING_STATE)
        markup = telebot.types.ReplyKeyboardRemove()
        bot.send_message(current_user, 'Вы долго не использовали бота, и были переведены в неактивное состояние. '
                                       'Напишите, пожалуйста, /start для начала работы.', reply_markup=markup)
        current_user = None
    is_busy = False
    timer = None


# функция окончания добавления операции
def finish_op(message, is_report=False):
    clear(operation)
    globals.reset_production()
    globals.reset_production_report()
    if not is_report:
        bot.send_message(message.chat.id, 'Операция добавлена в таблицу!')
    set_state(message.from_user.id, DEFAULT_STATE)
    handle_default_state(message)


def reset_timer(message=None):
    print("timer reset")
    global timer, current_user
    if current_user is None and message is not None:
        current_user = message.from_user.id
    if timer:
        timer.cancel()
    timer = threading.Timer(TIMEOUT + 340, timeout)
    timer.start()


def reset_timer_menu(message=None):
    print("timer reset")
    global timer, current_user
    if current_user is None and message is not None:
        current_user = message.from_user.id
    if timer:
        timer.cancel()
    timer = threading.Timer(TIMEOUT, timeout)
    timer.start()


# Функция, помогающая определить пропускать ли UNIT_STATE, т.к. для одного наименования возможна только одна единица
# измерения => если такое наименование уже встречалось в таблице операций, то выбор единицы измерения не нужен
def skip_unit():
    looked_up_unit = look_up_unit(operation['name'])
    return looked_up_unit != ''


# большой блок try, созданный для отлавливания исключений, связанных с проблемами с соединением
# (в основном к Google Sheets)

try:

    @bot.message_handler(commands=['start'])
    def main(message):
        global is_busy, current_user, timer
        if is_busy and current_user != message.from_user.id:
            bot.send_message(message.chat.id, 'Бот на данный момент занят другим пользователем. Попробуйте позже, '
                                              'написав /start.')
        else:
            if is_busy and current_user == message.from_user.id:
                if timer:
                    timer.cancel()
            is_busy = True
            current_user = message.from_user.id
            set_state(current_user, DEFAULT_STATE)
            if timer:
                timer.cancel()
            timer = threading.Timer(TIMEOUT, timeout)
            timer.start()
            handle_default_state(message)


    @bot.message_handler(commands=['help'])
    def main(message):
        bot.send_message(message.chat.id, 'Добро пожаловать в бота по управленческому учету остатков на складе! '
                                          'Данный бот связывается с таблицей в Google Sheets (/url) и управляет ею')


    @bot.message_handler(commands=['url'])
    def main(message):
        bot.send_message(message.chat.id,
                         'https://docs.google.com/spreadsheets/d/1mnp5yCJx9T3hU7m3I-Pz6rZzwwoBVgFnRvFOBTn6OyY')


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == DEFAULT_STATE)
    def handle_default_state(message):
        reset_timer_menu(message)
        clear(operation)
        markup = telebot.types.ReplyKeyboardRemove()
        response = bot.send_message(message.chat.id, 'Вы в главном меню.', reply_markup=markup)
        time.sleep(0.9)
        try_delete(message, response=response)
        bot.send_message(message.chat.id, 'Выберите, что Вы хотите сделать:', reply_markup=markups.main_markup)
        set_state(message.from_user.id, AWAITING_STATE)


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == NAME_STATE)
    def handle_name_state(message):
        global operation_type
        reset_timer(message)
        try:
            split = message.text.split(' | ')
            message.text = split[1]
        except IndexError:
            print('not name')
        if message.text == '❌ Отмена':
            cancel(message)
        elif message.text == '✅ Подтвердить товары на отправку в производство':
            operation_type = 'production_in'
            ask_name(message, 'Введите, пожалуйста, наименование готового изделия.')
        elif (operation_type == 'purchase' or operation_type == 'production_in') and message.text in markups.item_list:
            operation['name'] = message.text
            if skip_unit():
                set_state(message.from_user.id, PRICE_STATE)
                if operation_type == 'purchase':
                    ask_price(message, f'Введите, пожалуйста, цену товара за единицу ({operation["unit"]}).')
                else:
                    ask_amount(message, f'Введите, пожалуйста, количество товара ({operation["unit"]}).')
            else:
                set_state(message.from_user.id, UNIT_STATE)
                ask_unit(message, 'Введите, пожалуйста, единицу измерения товара.')
        elif ((operation_type == 'sell' or operation_type == 'write_off' or operation_type == 'production')
              and message.text in markups.item_list):
            if look_up_amount_price(message.text) == '0':
                bot.send_message(message.chat.id, 'Списать невозможно. Остатков по этой позиции нет на складе.')
                set_state(message.from_user.id, DEFAULT_STATE)
                handle_default_state(message)
            else:
                operation['name'] = message.text
                set_state(message.from_user.id, AMOUNT_STATE)
                ask_amount_sell(message, f'Введите, пожалуйста, количество товара. Максимальное количество: '
                                         f'{operation["amount_left"]} {operation["unit"]}')
        else:
            ask_name(message, 'Не в справочнике. Введите, пожалуйста, наименование товара.')


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == UNIT_STATE)
    def handle_unit_state(message):
        reset_timer(message)
        if message.text == '❌ Отмена':
            cancel(message)
        elif operation_type == 'purchase' and message.text in markups.unit_set:
            operation['unit'] = message.text
            ask_price(message, f'Введите, пожалуйста, цену товара за единицу ({operation["unit"]}).')
        elif operation_type == 'production_in' and message.text in markups.unit_set:
            operation['unit'] = message.text
            ask_amount(message, f'Введите, пожалуйста, количество товара ({operation["unit"]}).')
        elif (operation_type == 'sell' or operation_type == 'write_off') and message.text in markups.unit_set:
            operation['unit'] = message.text
            ask_amount_sell(message, f'Введите, пожалуйста, количество товара. Максимальное количество: '
                                     f'{operation["amount_left"]} {operation["unit"]}')
        else:
            ask_unit(message, 'Неправильный ввод. Введите, пожалуйста, единицу измерения товара.')


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == PRICE_STATE)
    def handle_price_state(message):
        reset_timer(message)
        if message.text == '❌ Отмена':
            cancel(message)
        elif operation_type == 'purchase':
            try:
                if float(message.text) < NEAR_ZERO:
                    raise ValueError
                else:
                    operation['price'] = message.text
                    ask_amount(message, f'Введите, пожалуйста, количество товара ({operation["unit"]}).')
            except ValueError:
                ask_price(message, f'Неправильный ввод. Введите, пожалуйста, цену товара за единицу'
                                   f' ({operation["unit"]}).')


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == AMOUNT_STATE)
    def handle_amount_state(message):
        reset_timer(message)
        if message.text == '❌ Отмена':
            cancel(message)
        elif operation_type == 'purchase' or operation_type == 'production_in':
            try:
                if float(message.text) < NEAR_ZERO:
                    raise ValueError
                else:
                    operation['amount'] = message.text
                    if operation_type == 'purchase':
                        ask_seller(message, 'Введите, пожалуйста, наименование поставщика.')
                    else:
                        ask_responsible(message, f'Введите, пожалуйста, ответственного за заполнение этой операции.'
                                                 f' Этим действием Вы ее подтверждаете.')
            except ValueError:
                ask_amount(message, f'Неправильный ввод. Введите, пожалуйста, количество товара'
                                    f' ({operation["unit"]}).')
        elif operation_type == 'sell' or operation_type == 'write_off' or operation_type == 'production':
            try:
                amount = float(message.text)
                if amount > float(un_convert_float(operation['amount_left'])) or amount < NEAR_ZERO:
                    bot.send_message(message.chat.id,
                                     f'Вы списываете больше остатков, чем есть на складе'
                                     f' ({operation["amount_left"]} {operation["unit"]}),'
                                     f' либо ввели неположительное значение.'
                                     ' Введите, пожалуйста, корректное значение.', reply_markup=markups.cancel_markup)
                    set_state(message.from_user.id, AMOUNT_STATE)
                elif operation_type == 'sell':
                    operation['amount'] = message.text
                    set_state(message.from_user.id, BUYER_NAME_STATE)
                    ask_buyer_name(message, 'Введите, пожалуйста, наименование покупателя.')
                elif operation_type == 'production':
                    operation['amount'] = message.text
                    set_state(message.from_user.id, DEFAULT_STATE)
                    production_out(operation['name'], operation['price'], operation['amount'], operation['unit'])
                    ask_names(message)
                else:
                    operation['amount'] = message.text
                    ask_responsible(message, f'Введите, пожалуйста, ответственного за заполнение этой операции.'
                                             f' Этим действием Вы ее подтверждаете.')
            except ValueError:
                bot.send_message(message.chat.id,
                                 f'Вы ввели не число. Попробуйте снова (Максимум: {operation["amount_left"]} '
                                 f'{operation["unit"]}).',
                                 reply_markup=markups.cancel_markup)
                set_state(message.from_user.id, AMOUNT_STATE)


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == BUYER_NAME_STATE)
    def handle_buyer_name_state(message):
        reset_timer(message)
        if message.text == '❌ Отмена':
            cancel(message)
        else:
            if message.text in markups.buyer_set:
                operation['buyer'] = message.text  # верим в юзера
                ask_sell_price(message, f'Введите, пожалуйста, цену продажи (за единицу {operation["unit"]}).')
            else:
                ask_buyer_name(message, 'Не в справочнике. Введите, пожалуйста, наименование покупателя.')


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == SELL_PRICE_STATE)
    def handle_price_state(message):
        reset_timer(message)
        if message.text == '❌ Отмена':
            cancel(message)
        else:
            try:
                floated = float(message.text)
                if floated < NEAR_ZERO:
                    ask_sell_price(message,
                                   f'Неправильный ввод. Введите, пожалуйста, цену продажи'
                                   f' (за единицу {operation["unit"]}).')
                else:
                    operation['sell_price'] = message.text
                    ask_responsible(message, f'Введите, пожалуйста, ответственного за заполнение этой операции.'
                                             f' Этим действием Вы ее подтверждаете.')
            except ValueError:
                ask_sell_price(message,
                               f'Неправильный ввод. Введите, пожалуйста, цену'
                               f' продажи (за единицу {operation["unit"]}).')


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == SELLER_NAME_STATE)
    def handle_seller_name_state(message):
        reset_timer(message)
        if message.text == '❌ Отмена':
            cancel(message)
        else:
            if message.text in markups.seller_set:
                operation['seller_name'] = message.text
                ask_responsible(message, f'Введите, пожалуйста, ответственного за заполнение этой операции.'
                                         f' Этим действием Вы ее подтверждаете.')
            else:
                ask_seller(message, 'Не в справочнике. Введите, пожалуйста, наименование поставщика.')


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == PRODUCTION_REPORT_STATE)
    def handle_production_report_state(message):
        reset_timer(message)
        if message.text == '❌ Отмена':
            cancel(message)
        else:
            if message.text in globals.production_set:
                production_stage = message.text.split(' | ')[0]
                output = list_ingredients_message(production_stage)
                bot.send_message(message.chat.id, output)
                finish_op(message, is_report=True)
            else:
                ask_production_report(message, 'Выберите из списка. Выберите, пожалуйста, производственный этап.')


    @bot.message_handler(func=lambda message: get_state(message.from_user.id) == RESPONSIBLE_STATE)
    def handle_responsible_state(message):
        reset_timer(message)
        if message.text == '❌ Отмена':
            cancel(message)
        else:
            if message.text in markups.employee_set:
                operation['responsible'] = message.text
                if operation_type == 'purchase':
                    purchase(operation['name'], operation['price'], operation['unit'], operation['amount'],
                             operation['seller_name'], operation['responsible'])
                    finish_op(message)
                elif operation_type == 'sell':
                    sell(operation['name'], operation['price'], operation['unit'], operation['amount'],
                         operation['buyer'], operation['sell_price'], operation['responsible'])
                    finish_op(message)
                elif operation_type == 'production_in':
                    production_in(operation['name'], operation['amount'], operation['unit'], operation['responsible'])
                    finish_op(message)
                else:
                    write_off(operation['name'], operation['price'], operation['unit'], operation['amount'],
                              operation['responsible'])
                    finish_op(message)
            else:
                ask_responsible(message,
                                f'Не в справочнике. Введите, пожалуйста, ответственного за заполнение этой операции.'
                                f' Этим действием Вы ее подтверждаете.')


    @bot.callback_query_handler(func=lambda call: True)
    def handle_start_query(call):
        global operation_type
        if is_busy and current_user == call.from_user.id:
            reset_timer(call.message)
            clear(operation)
            globals.reset_production()
            set_state(call.message.from_user.id, None)
            if call.data == 'operations':
                bot.send_message(call.message.chat.id, 'Какой тип операции вас интересует?',
                                 reply_markup=markups.ops_markup)
                try_delete(call.message)
            elif call.data == 'cancel':
                clear(operation)
                try_delete(call.message)
                set_state(call.message.from_user.id, DEFAULT_STATE)
                handle_default_state(call.message)
            elif call.data == 'stocks':
                bot.send_message(call.message.chat.id, total_stocks_output())
                try_delete(call.message)
                set_state(call.message.from_user.id, DEFAULT_STATE)
                handle_default_state(call.message)
            elif call.data == 'purchase':
                operation_type = 'purchase'
                try_delete(call.message)
                ask_name(call)
            elif call.data == 'sell':
                operation_type = 'sell'
                try_delete(call.message)
                ask_name(call)
            elif call.data == 'write_off':
                operation_type = 'write_off'
                try_delete(call.message)
                ask_name(call)
            # elif call.data == 'clear_op_table':
            #     try_delete(call.message)
            #     bot.send_message(call.message.chat.id, 'Вы уверены в том, что хотите очистить таблицу операций?',
            #                      reply_markup=markups.confirm_markup)
            # elif call.data == 'clear_confirmed':
            #     try_delete(call.message)
            #     if not clean_up_ops_table():
            #         bot.send_message(call.message.chat.id, f'Таблица операций успешно очищена.
            #         {total_stocks_output()}')
            #     else:
            #         bot.send_message(call.message.chat.id,
            #                          'Произошла ошибка при очистке. Запросите помощь у администратора.')
            #     set_state(call.message.from_user.id, DEFAULT_STATE)
            #     handle_default_state(call.message)
            elif call.data == 'stock_positions':
                bot.send_message(call.message.chat.id, list_stocks_message())
                try_delete(call.message)
                set_state(call.message.from_user.id, DEFAULT_STATE)
                handle_default_state(call.message)
            elif call.data == 'report_buy':
                bot.send_message(call.message.chat.id, list_purchases_message())
                try_delete(call.message)
                set_state(call.message.from_user.id, DEFAULT_STATE)
                handle_default_state(call.message)
            elif call.data == 'report_sell':
                bot.send_message(call.message.chat.id, list_sales_message())
                try_delete(call.message)
                set_state(call.message.from_user.id, DEFAULT_STATE)
                handle_default_state(call.message)
            elif call.data == 'production':
                operation_type = 'production'
                try_delete(call.message)
                ask_names(call)
            elif call.data == 'production_report':
                operation_type = 'production_report'
                try_delete(call.message)
                ask_production_report(call)
            elif call.data == 'refresh':
                markups.refresh()
                bot.send_message(call.message.chat.id, 'Справочники обновлены.')
                try_delete(call.message)
                set_state(call.message.from_user.id, DEFAULT_STATE)
                handle_default_state(call.message)
        elif is_busy and current_user != call.from_user.id:
            try_delete(call.message)
            bot.send_message(call.message.chat.id, f'Бот на данный момент занят другим пользователем. '
                                                   'Попробуйте позже, написав /start.')
        else:
            try_delete(call.message)
            bot.send_message(call.message.chat.id, 'Бот свободен. Напишите, пожалуйста, /start для начала работы.')


    @bot.message_handler()
    def info(message):
        markup = telebot.types.ReplyKeyboardRemove()
        if is_busy and current_user != message.from_user.id:
            bot.send_message(message.chat.id, 'Бот на данный момент занят другим пользователем. '
                                              'Попробуйте позже, написав /start.', reply_markup=markup)
        elif is_busy and current_user == message.from_user.id:
            bot.send_message(message.chat.id, 'Пожалуйста, воспользуйтесь главным меню. Если его нет, напишите '
                                              '/start.', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, 'Бот свободен. Напишите, пожалуйста, /start для начала работы.',
                             reply_markup=markup)


    bot.polling(none_stop=True)
except ssl.SSLError:  # для обработки ситуаций, когда у Google Sheets API сильные задержки
    print("ssl")
    bot.polling(none_stop=True)
