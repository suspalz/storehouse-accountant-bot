from datetime import date

import pygsheets

import globals

# client = pygsheets.authorize(service_account_file='service_key2.json')
client = pygsheets.authorize(service_account_file='service_key1.json')
spreadsheet = client.open('Бухгалтерия2')

# все операции будут заводиться в дату, которая стоит на серверном компьютере
today = date.today()

# управление операциями
op_sheet = spreadsheet.worksheet('title', 'Операции')
item_sheet = spreadsheet.worksheet('title', 'Все запасы')
unit_sheet = spreadsheet.worksheet('title', 'Единицы измерения')
buyer_sheet = spreadsheet.worksheet('title', 'Получатели изделий')
party_sheet = spreadsheet.worksheet('title', 'Контрагенты')
seller_sheet = spreadsheet.worksheet('title', 'Поставщики полуфабрикатов')
employee_sheet = spreadsheet.worksheet('title', 'Сотрудники')

# сдвиг таблицы
OFFSET = 8

# указатель на текущий пустой ряд
globals.curr_row = 8

# словарь операции
operation = {'date': None, 'type': None, 'name': None, 'price': None, 'unit': None, 'amount': None, 'amount_left': None,
             'sell_type': None,
             'seller_name': None, 'responsible': None}

# удобная маркировка столбцов через буквенные имена переменных, т.к. в pygsheets функции в качестве параметров обычно
# берут числа
a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z, aa, ab, ac, ad = range(1, 31)


# очистка операционного словаря
def clear(voc):
    for key in voc:
        voc[key] = None


# получение списка из столбца (используется для доставки данных из справочника)
def get_list(sheet, col):
    values = sheet.get_col(col, include_tailing_empty=False)[1:]
    return values


# функция, конвертирующая строковое представление float python (через точку) в строковое представление float Google
# Sheets (через запятую)
def convert_float(str_number):
    str_number = str_number.replace('.', ',')
    return str_number


# обратная функция вышеупомянутой
def un_convert_float(str_number):
    str_number = str_number.replace(',', '.')
    return str_number


def get_production_stage():
    return op_sheet.get_value('D1')


def find_suggested_price(name):
    return globals.suggested_price[name]


# функция, очищающая таблицу операций до первой пустой строки
def clean_up_ops_table():
    global op_sheet
    point_to_empty_op()
    exception = False
    try:
        for row in range(OFFSET, globals.curr_row):
            clear_row(row)
    except Exception as exc:
        exception = True
        print(exc)
    globals.curr_row = OFFSET
    return exception


# функция, возвращающая общее кол-во остатков на складе
def total_stocks_output():
    total_stock = op_sheet.cell('B1').value
    if total_stock == '  -   ₽ ':
        return 'Сейчас на складе нет остатков.'
    else:
        return f'Общее количество остатков на складе: {total_stock}'


# функция, обновляющая globals.curr_row на актуальное значение (первую пустую строку, т.е. доступную для ввода операции)
def point_to_empty_op():
    globals.curr_row = int(op_sheet.get_value('E1'))


def clear_row(row):
    op_sheet.update_value((row, b), '')
    op_sheet.update_value((row, c), '')
    op_sheet.update_value((row, d), '')
    op_sheet.update_value((row, e), '')
    op_sheet.update_value((row, g), '')
    op_sheet.update_value((row, i), '')
    op_sheet.update_value((row, j), '')
    op_sheet.update_value((row, k), '')
    op_sheet.update_value((row, r), '')
    op_sheet.update_value((row, t), '')
    op_sheet.update_value((row, u), '')
    op_sheet.update_value((row, y), '')
    op_sheet.update_value((row, z), '')


# функция, возвращающая общие остатки на складе по позициям
def list_stocks_message():
    output = ''
    rows = [int(row) for row in op_sheet.get_col(aa, include_tailing_empty=False)][:-1]
    if len(rows) > 0:
        for row in rows:
            row_data = op_sheet.get_row(row, include_tailing_empty=False)
            output += (f'Имя: {row_data[e - 1]}\n'
                       f'Кол-во: {row_data[n - 1]} {row_data[i - 1]}\n'
                       f'Сумма: {row_data[o - 1]} ₽\n'
                       f'--------------------------------------\n')
    else:
        output = 'Сейчас на складе нет остатков.'
    return output


def list_ingredients_message(production_stage):
    op_sheet.update_value((1, ad), production_stage)
    output = ''
    rows = [int(row) for row in op_sheet.get_col(ac, include_tailing_empty=False)]
    if len(rows) > 0:
        for row in rows:
            row_data = op_sheet.get_row(row, include_tailing_empty=False)
            output += (f'Имя: {row_data[e - 1]}\n'
                       f'Снятое кол-во: {row_data[k - 1][1:]} {row_data[i - 1]}\n'
                       f'Снятая сумма: {row_data[m - 1][1:]} ₽\n'
                       f'--------------------------------------\n')
    else:
        op_sheet.update_value((1, ad), '')
        return 'Нет информации по затраченным материалам на данную позицию.'
    op_sheet.update_value((1, ad), '')
    return output


# функция, возвращающая все закупки по контрагентам
def list_purchases_message():
    output = ''
    summ = 0
    offset = 2
    while party_sheet.get_value((offset, a)) != '':
        if party_sheet.get_value((offset, a)) != '0':
            output += (f'Были совершены закупки на {party_sheet.get_value((offset, a))} ₽'
                       f' у {party_sheet.get_value((offset, b))}\n')
            summ += float(un_convert_float(party_sheet.get_value((offset, a))))
        offset += 1
    if output == '':
        output = 'Закупок совершено не было.'
    else:
        output += f'Сумма затрат: {summ} ₽'
    return output


# функция, возвращающая всю прибыль по контрагентам
def list_sales_message():
    output = ''
    summ = 0
    offset = 2
    while party_sheet.get_value((offset, e)) != '':
        output += (f'Было продано товара на {party_sheet.get_value((offset, e))} ₽'
                   f' для {party_sheet.get_value((offset, f))}\n')
        summ += float(un_convert_float(party_sheet.get_value((offset, e))))
        offset += 1
    if output == '':
        output = 'Продаж совершено не было.'
    else:
        output += f'Итоговая прибыль: {summ} ₽'
    return output


# функция, позволяющая посмотреть средневзвешенную цену для списания товара, а также доступное количество на складе
# этого товара
def look_up_amount_price(name):
    point_to_empty_op()
    op_sheet.update_value((globals.curr_row, b), today.strftime('%d.%m.%Y'))
    op_sheet.update_value((globals.curr_row, c), 'Списание')
    op_sheet.update_value((globals.curr_row, e), name)
    amount = op_sheet.get_value((globals.curr_row, n))
    price = op_sheet.get_value((globals.curr_row, h))
    unit = op_sheet.get_value((globals.curr_row, p))
    if unit != '':
        operation['unit'] = unit
    else:
        operation['unit'] = None
    op_sheet.update_value((globals.curr_row, b), '')
    op_sheet.update_value((globals.curr_row, c), '')
    op_sheet.update_value((globals.curr_row, e), '')
    operation['amount_left'] = amount
    operation['price'] = price
    return amount


# функция для подсмотра единицы измерения
def look_up_unit(name):
    point_to_empty_op()
    op_sheet.update_value((globals.curr_row, e), name)
    unit = op_sheet.get_value((globals.curr_row, p))
    op_sheet.update_value((globals.curr_row, e), '')
    if unit != '':
        operation['unit'] = unit
    return unit


# операция покупки
def purchase(name, price, unit, amount, seller_name, responsible):
    point_to_empty_op()
    op_sheet.update_value((globals.curr_row, b), today.strftime('%d.%m.%Y'))
    op_sheet.update_value((globals.curr_row, c), 'Поступление')
    op_sheet.update_value((globals.curr_row, e), name)
    op_sheet.update_value((globals.curr_row, g), convert_float(price))
    op_sheet.update_value((globals.curr_row, i), unit)
    op_sheet.update_value((globals.curr_row, j), convert_float(amount))
    op_sheet.update_value((globals.curr_row, z), responsible)
    op_sheet.update_value((globals.curr_row, y), seller_name)
    op_sheet.update_value((globals.curr_row, r), 'Покупка')


# операция продажи
def sell(name, price, unit, amount, buyer, sell_price, responsible):
    point_to_empty_op()
    op_sheet.update_value((globals.curr_row, b), today.strftime('%d.%m.%Y'))
    op_sheet.update_value((globals.curr_row, c), 'Списание')
    op_sheet.update_value((globals.curr_row, e), name)
    op_sheet.update_value((globals.curr_row, g), convert_float(price))
    op_sheet.update_value((globals.curr_row, i), unit)
    amount = str(0 - float(amount))
    op_sheet.update_value((globals.curr_row, k), convert_float(amount))
    op_sheet.update_value((globals.curr_row, r), 'Продажа')
    op_sheet.update_value((globals.curr_row, t), buyer)
    op_sheet.update_value((globals.curr_row, u), convert_float(sell_price))
    op_sheet.update_value((globals.curr_row, z), responsible)


# операция списания
def write_off(name, price, unit, amount, responsible):
    point_to_empty_op()
    op_sheet.update_value((globals.curr_row, b), today.strftime('%d.%m.%Y'))
    op_sheet.update_value((globals.curr_row, c), 'Списание')
    op_sheet.update_value((globals.curr_row, e), name)
    op_sheet.update_value((globals.curr_row, g), convert_float(price))
    op_sheet.update_value((globals.curr_row, i), unit)
    op_sheet.update_value((globals.curr_row, r), 'Списание')
    amount = str(0 - float(amount))
    op_sheet.update_value((globals.curr_row, k), convert_float(amount))
    op_sheet.update_value((globals.curr_row, z), responsible)


def production_out(name, price, amount, unit):
    point_to_empty_op()
    production_stage = int(get_production_stage()) + 1 if globals.production_count <= 0 else int(get_production_stage())
    globals.production_count += 1
    op_sheet.update_value((globals.curr_row, b), today.strftime('%d.%m.%Y'))
    op_sheet.update_value((globals.curr_row, c), 'Списание')
    op_sheet.update_value((globals.curr_row, d), production_stage)
    op_sheet.update_value((globals.curr_row, e), name)
    op_sheet.update_value((globals.curr_row, g), convert_float(price))
    op_sheet.update_value((globals.curr_row, i), unit)
    op_sheet.update_value((globals.curr_row, r), 'Производство')
    amount = str(0 - float(amount))
    op_sheet.update_value((globals.curr_row, k), convert_float(amount))
    globals.production_sum += float(un_convert_float(op_sheet.get_value((globals.curr_row, m))))


def production_in(name, amount, unit, responsible):
    point_to_empty_op()
    globals.production_sum = -globals.production_sum
    production_stage = int(get_production_stage())
    globals.production_count += 1
    op_sheet.update_value((globals.curr_row, b), today.strftime('%d.%m.%Y'))
    op_sheet.update_value((globals.curr_row, c), 'Поступление')
    op_sheet.update_value((globals.curr_row, d), production_stage)
    op_sheet.update_value((globals.curr_row, e), name)
    op_sheet.update_value((globals.curr_row, g), convert_float(str(globals.production_sum / float(amount))))
    op_sheet.update_value((globals.curr_row, i), unit)
    op_sheet.update_value((globals.curr_row, r), 'Производство')
    amount = str(float(amount))
    op_sheet.update_value((globals.curr_row, j), convert_float(amount))
    op_sheet.update_value((globals.curr_row, z), responsible)
    globals.reset_production()
