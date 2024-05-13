from telebot import types

from sheet_handler import *

# главная группа кнопок (операции, остатки, отчеты, очистка) [inline]
main_markup = types.InlineKeyboardMarkup()

main_markup.add(types.InlineKeyboardButton('📝 Посмотреть общие остатки на складе', callback_data='stocks'))
main_markup.add(types.InlineKeyboardButton('📊 Текущие позиции на складе',
                                           callback_data='stock_positions'))
main_markup.add(types.InlineKeyboardButton('➗ Операции на складе', callback_data='operations'))
main_markup.add(types.InlineKeyboardButton('📦 Просмотреть произведенные товары', callback_data='production_report'))
main_markup.add(types.InlineKeyboardButton('📈 Просмотреть отчет о прибыли с продаж', callback_data='report_sell'))
main_markup.add(types.InlineKeyboardButton('📉 Просмотреть отчет о затратах с покупок', callback_data='report_buy'))
main_markup.add(types.InlineKeyboardButton('🔄 Обновить информацию о справочниках', callback_data='refresh'))
# main_markup.add(types.InlineKeyboardButton('🔴 Очистить таблицу операций', callback_data='clear_op_table'))

# кнопки операций [inline]
ops_markup = types.InlineKeyboardMarkup()

ops_markup.add(types.InlineKeyboardButton('💲Покупка', callback_data='purchase'))
ops_markup.add(types.InlineKeyboardButton('💵 Продажа', callback_data='sell'))
ops_markup.add(types.InlineKeyboardButton('📌 Списание', callback_data='write_off'))
ops_markup.add(types.InlineKeyboardButton('📦 В производство', callback_data='production'))
ops_markup.add(types.InlineKeyboardButton('❌ Отмена', callback_data='cancel'))

# полный справочник позиций [reply]
item_code_list = get_list(item_sheet, 2)
item_list = get_list(item_sheet, 1)
suggested_price_list = get_list(item_sheet, 3)
item_set = set(item_list)
item_markup = types.ReplyKeyboardMarkup()
for item, code, price in zip(item_list, item_code_list, suggested_price_list):
    item_markup.add(types.KeyboardButton(f'{code} | {item}'))
    globals.suggested_price[item] = price
item_markup.add(types.KeyboardButton('❌ Отмена'))

# справочник единиц измерения [reply]
unit_list = get_list(unit_sheet, 1)
unit_set = set(unit_list)
unit_markup = types.ReplyKeyboardMarkup()
for unit in unit_list:
    unit_markup.add(types.KeyboardButton(unit))
unit_markup.add(types.KeyboardButton('❌ Отмена'))

# справочник покупателей [reply]
buyer_list = get_list(buyer_sheet, 2)
buyer_set = set(buyer_list)
buyer_markup = types.ReplyKeyboardMarkup()
for buyer in buyer_list:
    buyer_markup.add(types.KeyboardButton(buyer))
buyer_markup.add(types.KeyboardButton('❌ Отмена'))

# справочник поставщиков [reply]
seller_list = get_list(seller_sheet, 2)
seller_set = set(seller_list)
seller_markup = types.ReplyKeyboardMarkup()
for seller in seller_list:
    seller_markup.add(types.KeyboardButton(seller))
seller_markup.add(types.KeyboardButton('❌ Отмена'))

# справочник сотрудников [reply]
employee_list = get_list(employee_sheet, 1)
employee_set = set(employee_list)
employee_markup = types.ReplyKeyboardMarkup()
for employee in employee_list:
    employee_markup.add(types.KeyboardButton(employee))
employee_markup.add(types.KeyboardButton('❌ Отмена'))


# кнопка отмены [reply]
cancel_markup = types.ReplyKeyboardMarkup()
cancel_markup.add(types.KeyboardButton('❌ Отмена'))

# кнопка подтверждения [reply]
confirm_markup = types.InlineKeyboardMarkup()
confirm_markup.add(types.InlineKeyboardButton('🔴 Да', callback_data='clear_confirmed'))
confirm_markup.add(types.InlineKeyboardButton('🟢 Отмена', callback_data='cancel'))


# обновление всех кнопок-справочников
def refresh():
    global item_markup, item_list, item_set
    global unit_markup, unit_list, unit_set
    global buyer_markup, buyer_list, buyer_set
    global seller_markup, seller_list, seller_set
    global employee_markup, employee_list, employee_set

    item_code_list = get_list(item_sheet, 2)
    item_list = get_list(item_sheet, 1)
    suggested_price_list = get_list(item_sheet, 3)
    item_set = set(item_list)
    item_markup = types.ReplyKeyboardMarkup()
    globals.suggested_price = {}
    for item, code, price in zip(item_list, item_code_list, suggested_price_list):
        item_markup.add(types.KeyboardButton(f'{code} | {item}'))
        if price != '':
            globals.suggested_price[item] = price
    item_markup.add(types.KeyboardButton('❌ Отмена'))

    unit_list = get_list(unit_sheet, 1)
    unit_set = set(unit_list)
    unit_markup = types.ReplyKeyboardMarkup()
    for unit in unit_list:
        unit_markup.add(types.KeyboardButton(unit))
    unit_markup.add(types.KeyboardButton('❌ Отмена'))

    buyer_list = get_list(buyer_sheet, 2)
    buyer_set = set(buyer_list)
    buyer_markup = types.ReplyKeyboardMarkup()
    for buyer in buyer_list:
        buyer_markup.add(types.KeyboardButton(buyer))
    buyer_markup.add(types.KeyboardButton('❌ Отмена'))

    seller_list = get_list(seller_sheet, 2)
    seller_set = set(seller_list)
    seller_markup = types.ReplyKeyboardMarkup()
    for seller in seller_list:
        seller_markup.add(types.KeyboardButton(seller))
    seller_markup.add(types.KeyboardButton('❌ Отмена'))

    employee_list = get_list(employee_sheet, 1)
    employee_set = set(employee_list)
    employee_markup = types.ReplyKeyboardMarkup()
    for employee in employee_list:
        employee_markup.add(types.KeyboardButton(employee))
    employee_markup.add(types.KeyboardButton('❌ Отмена'))
