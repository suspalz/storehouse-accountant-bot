# отдельный файл с глобальными переменными для операций с производством и предложенной ценой
production_count = 0
production_sum = 0
curr_row = 8

production_set = set()
production_pos = {}

suggested_price = {}


def reset_production_report():
    global production_set, production_pos
    production_set = set()
    production_pos = {}


def reset_production():
    global production_count, production_sum
    production_count = 0
    production_sum = 0
