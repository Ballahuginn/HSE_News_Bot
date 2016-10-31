import vk
import telebot
import time
import threading
from telebot import types


bot = telebot.TeleBot('TOKEN')

session = vk.Session()
vk_api = vk.API(session, v='5.59')

vk_arr = []
group_arr = []
group_id_arr = []
vk_id = ['9793010', '20707740']

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

    def print_vk_sub(msg, last_post_date):
        last_posts = vk_sub(vk_id, last_post_date)

        for i in range(1, len(last_posts), 2):
            bot.send_message(msg.chat.id, last_posts[i])
        # vk_last_post = five_last_posts[0]

        t = threading.Timer(15, print_vk_sub, [msg, last_post_date])
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
            bot.send_message(message.chat.id, 'Ты не выбрал группу')
    if message.text == 'Подписаться на обновления':
        last_post = vk_start_sub(vk_id)
        bot.send_message(message.chat.id, 'Ты подписался на уведомления!')
        print_vk_sub(message, last_post)
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


def vk_start_sub(id_vk):
    last_post = []
    for _j in id_vk:
        group = vk_api.wall.get(owner_id=_j, count=6, filter='owner')
        post_count = 0
        for _p in group['items']:
            if type(_p) != int:
                if 'is_pinned' not in _p and post_count < 1:
                    last_post.append(_p['date'])
                    post_count += 1

    return last_post


def vk_sub(id_vk, last_post_date):
    last_posts = []
    _pd = 0
    for _j in id_vk:
        group = vk_api.wall.get(owner_id=_j, count=6, filter='owner')
        post_count = 0
        for _p in group['items']:
            if type(_p) != int:
                if 'is_pinned' not in _p and post_count < 5:
                    post_count += 1
                    if int(_p['date']) > int(last_post_date[_pd]):
                        last_posts.append(str(_p['date']))
                        link = 'https://vk.com/wall' + _j + '_' + str(_p['id'])
                        print(link)
                        last_posts.append(link)
        _pd += 1

    return last_posts


if __name__ == '__main__':
    bot.polling(none_stop=True)
    while True:
        time.sleep(200)
