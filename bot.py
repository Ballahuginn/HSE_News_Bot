import vk
import telebot
import time
import threading
import os
from telebot import types


bot = telebot.TeleBot('237770898:AAGWJabjYZcPa7hN3mnfT1Gh3UPkaRVVCiQ')

session = vk.Session()
vk_api = vk.API(session, v='5.59')

vk_arr = []
group_arr = []
group_id_arr = []
vk_id_sub = ''
vk_id = '9793010'

markup = types.ReplyKeyboardMarkup()
markup1 = types.ReplyKeyboardMarkup()

markup.row('HSE Official VK Group')
markup.row('The Вышка')
markup.row('Ok!')
markup1.row('5 последних постов')
markup1.row('Подписаться на обновления')
markup1.row('Назад')

# print(vk_api.users.get(user_ids="ballahuginn"))
# print(vk_api.groups.getById(group_id="hse_university"))
# print(vk_api.wall.get(domain="hse_university", count=2, filter="owner"))


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, 'Привет! Выбери, откуда ты хочешь получить новости, а затем нажми "Ок"', reply_markup=markup)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def news_source(message):
    global vk_arr, group_id_arr

    def print_vk_sub(msg):
        vk_sub(vk_id)
        if os.stat('vk_sub_new.txt').st_size != 0:
            with open('vk_sub.txt', 'r') as old_file, open('vk_sub_new.txt', 'r') as new_file:
                old_line = old_file.readlines()
                new_line = new_file.readlines()
            if new_line[0] != old_line[0]:
                bot.send_message(msg.chat.id, new_line[1])
                with open('vk_sub.txt', 'w') as old_file, open('vk_sub_new.txt', 'r') as new_file:
                    new_line = new_file.read()
                    old_file.write(new_line)

        t = threading.Timer(5, print_vk_sub, [msg])
        t.start()

    if message.text == 'HSE Official VK Group':
        if '25205856' not in group_id_arr:
            # group_arr.append('hse_university')
            group_id_arr.append('25205856')
            bot.send_message(message.chat.id, 'Ты выбрал ' + message.text, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, message.text + ' уже была выбрана')
    if message.text == 'The Вышка':
        if '66036248' not in group_id_arr:
            # group_arr.append('thevyshka')
            group_id_arr.append('66036248')
            bot.send_message(message.chat.id, 'Ты выбрал ' + message.text, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, message.text + ' уже была выбрана')
    if message.text == 'Ok!':
        bot.send_message(message.chat.id, 'Что ты хочешь получить?', reply_markup=markup1)

    if message.text == '5 последних постов':
        vk_arr = vkfunction(group_id_arr)
        if vk_arr:
            for _i in vk_arr:
                bot.send_message(message.chat.id, _i)
        else:
            bot.send_message(message.chat.id, 'Вы не выбрали группу.')
    if message.text == 'Подписаться на обновления':
        vk_start_sub(vk_id)
        with open('vk_sub.txt', 'r') as f:
            link = f.readlines()
        bot.send_message(message.chat.id, link[1])
        print_vk_sub(message)
    elif message.text == 'Назад':
        bot.send_message(message.chat.id, 'Выбери, откуда ты хочешь получить новости, а затем нажми "Ок"', reply_markup=markup)
        group_id_arr = []


def vkfunction(vk_id_arr):
    arr_link = []
    vk_json_arr = []
    link_count = 0
    for _j in vk_id_arr:
        group = vk_api.wall.get(owner_id='-' + _j, count=6, filter='owner')
        post_count = 0
        for _k in group['items']:
            print(_k)
            if type(_k) != int:
                if 'id' in _k:
                    if 'is_pinned' not in _k and post_count < 5:
                        vk_json_arr.append(_k)
                        post_count += 1

    vk_sorted_arr = sorted(vk_json_arr, key=lambda k: int(k['date']), reverse=True)

    for _n in vk_sorted_arr:
        for _j in vk_id_arr:
            if '-' + _j == str(_n['owner_id']):
                link = 'https://vk.com/wall-' + _j + '_' + str(_n['id'])
                if link_count < 5:
                    arr_link.append(link)
                    link_count += 1
                    print(link)
    return arr_link


# def vk_sub(id_vk):
#     group = vk_api.wall.get(domain='ballahuginn', count=2, filter='owner')
#     post_count = 0
#     for _p in group:
#         if type(_p) != int:
#             if 'is_pinned' not in _p and post_count < 1:
#                 last_post = _p['date']
#                 post_count += 1
#                 link = 'https://vk.com/wall' + id_vk + '_' + str(_p['id'])
#                 print(link)
#
#     while True:
#         group = vk_api.wall.get(domain='ballahuginn', count=1, filter='owner')
#         for _p in group:
#             if type(_p) != int:
#                 if 'is_pinned' not in _p:
#                     if _p['date'] > last_post:
#                         link = 'https://vk.com/wall' + id_vk + '_' + str(_p['id'])
#                         print(link)
#                         last_post = _p['date']
#                     else:
#                         print('NULL')
#         time.sleep(30)

# abc = 1
# def hello():
#     global abc
#     if abc == 1:
#         s = 1
#         abc += 1
#     else:
#         s = 2
#         abc -= 1
#     print(s, abc)
# t = threading.Timer(1, hello)
# t.start()
# hello()

# def test():
#     s = '123'
    # with open('test.txt', 'w') as f:
    #     f.write(s)
    # with open('test.txt', 'r+') as f:
    #     l = f.readlines()
    #     print(l[2])


    # t = threading.Timer(1, test)
    # t.start()
    # return s

# t = threading.Timer(1, test)
# t.start()

# test()


def vk_start_sub(id_vk):
    group = vk_api.wall.get(domain='ballahuginn', count=2, filter='owner')
    post_count = 0
    for _p in group['items']:
        if type(_p) != int:
            if 'is_pinned' not in _p and post_count < 1:
                with open('vk_sub.txt', 'w') as f:
                    f.write(str(_p['date']))
                    f.write('\n')
                # last_post = _p['date']
                post_count += 1
                link = 'https://vk.com/wall' + id_vk + '_' + str(_p['id'])
                print(link)
                with open('vk_sub.txt', 'a') as f:
                    f.write(link)
                    f.write('\n')


def vk_sub(id_vk):
    group = vk_api.wall.get(domain='ballahuginn', count=1, filter='owner')
    for _p in group['items']:
        if type(_p) != int:
            if 'is_pinned' not in _p:
                with open('vk_sub.txt', 'r') as f:
                    l = f.readlines()
                if _p['date'] > int(l[0]):
                    link = 'https://vk.com/wall' + id_vk + '_' + str(_p['id'])
                    print(link)
                    with open('vk_sub_new.txt', 'w') as f:
                        f.write(str(_p['date']))
                        f.write('\n')
                        f.write(link)
                        f.write('\n')
                else:
                    open('vk_sub_new.txt', 'w').close()
                    print('NULL')


if __name__ == '__main__':
    bot.polling(none_stop=True)
    while True:
        time.sleep(200)
