import vk
import telebot
import time
from telebot import types


bot = telebot.TeleBot('TOKEN')

session = vk.Session()
api = vk.API(session)

group = ''
group_id = ''

markup = types.ReplyKeyboardMarkup()
markup1 = types.ReplyKeyboardMarkup()

markup.row('HSE Official VK Group')
markup.row('The Вышка')
markup1.row('5 последних постов')
markup1.row('Назад')
# markup.row('/start', '/help')

# print(api.users.get(user_ids="ballahuginn"))
# print(api.groups.getById(group_id="hse_university"))
# print(api.wall.get(domain="hse_university", filter="owner"))


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, 'Привет! Выбери, откуда ты хочешь получить новости.', reply_markup=markup)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def news_source(message):
    if message.text == 'HSE Official VK Group':
        global group, group_id
        group = 'hse_university'
        group_id = '25205856'
        bot.send_message(message.chat.id, 'Что ты хочешь получить?', reply_markup=markup1)
    elif message.text == 'The Вышка':
        group = 'thevyshka'
        group_id = '66036248'
        bot.send_message(message.chat.id, 'Что ты хочешь получить?', reply_markup=markup1)
    vk_arr = vkfunction(group, group_id)
    if message.text == '5 последних постов':
        for _l in vk_arr:
            bot.send_message(message.chat.id, _l)
    elif message.text == 'Назад':
        bot.send_message(message.chat.id, 'Выбери, откуда ты хочешь получить новости.', reply_markup=markup)


# @bot.message_handler(func=lambda message: message.text == '5 последних постов', content_types=['text'])
# def echo_all(message):
#     #print(group, group_id)
#     vk_arr = vkfunction(group, group_id)
#     #print(vk_arr)
#     if message.text == '5 последних постов':
#         for _l in vk_arr:
#             bot.send_message(message.chat.id, _l)


def vkfunction(vk_group, vk_group_id):
    arr_link = []
    hse_official = api.wall.get(owner_id='-' + vk_group_id, count=5, filter='owner')
    for _i in hse_official:
        if type(_i) != int:
            if 'id' in _i:
                link = 'https://vk.com/' + vk_group + '?w=wall-' + vk_group_id + '_' + str(_i['id'])
                arr_link.append(link)
    return arr_link


if __name__ == '__main__':
    bot.polling(none_stop=True)
    while True:
        time.sleep(200)
