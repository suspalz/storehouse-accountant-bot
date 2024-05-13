import telebot
import pygsheets
from telebot import types
from text_lines import *
from markups import *

bot = telebot.TeleBot('6865566493:AAEkaaZZwEcmqXvdkpxG3gYzohECLmoDzR0')

USER_STATE = {}
DEFAULT, EXPECT_DATE = 0, 1

client = pygsheets.authorize(service_account_file='service_key2.json')

spreadsheet = client.open('Бухгалтерия')
op_sheet = spreadsheet.worksheet('title', 'Операции')

#проверка подключения
print(client.spreadsheet_titles())


def set_state(id, state):
    USER_STATE[id] = state


def get_state(id, state):
    return USER_STATE.get(id, None)



@bot.message_handler(commands=['start'])
def main(message):
    bot.send_message(message.chat.id, 'Привет!', reply_markup=reply_markup)
    bot.send_message(message.chat.id, start_greeting, reply_markup=main_markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_start_query(call):
    if call.data == 'operation':
        bot.send_message(call.message.chat.id, operation_type, reply_markup=ops_markup)
    elif call.data == 'cancel':
        bot.send_message(call.message.chat.id, start_greeting, reply_markup=main_markup)
    elif call.data == 'purchase':
        bot.send_message(call.message.chat.id, 'Введите, пожалуйста, дату в формате ДД.ММ.ГГГГ')

@bot.message_handler(commands=['update_value'])
def update(message):
    op_sheet.update_value('H15', '20')
    bot.send_message(message.chat.id, op_sheet.cell('B1').value)


@bot.message_handler()
def info(message):
    if message.text == 'Общие остатки':
        total_stock = op_sheet.cell('B1').value
        if total_stock == '  -   ₽ ':
            bot.send_message(message.chat.id, no_total_stocks)
        else:
            bot.send_message(message.chat.id, total_stock)


bot.polling(none_stop=True)


# @bot.message_handler(content_types=['photo'])
# def get_photo(message):
#     markup = types.ReplyKeyboardMarkup()
#     markup.add(types.KeyboardButton("Общие остатки"))
#     bot.reply_to(message, "Вау, вот это фото!", reply_markup=markup)

# @bot.callback_query_handler(func=lambda callback: True)
# def callback_message(callback):
#     if callback.data == 'delete':
#         bot.delete_message(callback.message.chat.id, callback.message.message_id - 1)