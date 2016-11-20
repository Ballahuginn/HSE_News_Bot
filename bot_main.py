import vk
import telebot
import sqlite3
import time
from telebot import types
import bot_modules


bot = telebot.TeleBot('237770898:AAGX-2hK_05G9y9ehzUBhJy1dB8MzsRB3fc')

session = vk.Session()
vk_api = vk.API(session, v='5.59')

databasem = sqlite3.connect('HSE_BOT_DB.sqlite')
dbm = databasem.cursor()


markup_start = types.ReplyKeyboardMarkup()
markup_settings = types.ReplyKeyboardMarkup()
markup = types.ReplyKeyboardMarkup()
markup1 = types.ReplyKeyboardMarkup()


markup_start.row('Выбрать группы')
markup_start.row('Настройки')

markup_settings.row('Сбросить группы')
markup_settings.row('Остановить подписку')
markup_settings.row('Главное меню')


dbm.execute("SELECT * FROM Groups")
groups = dbm.fetchall()

for i in groups:
    markup.row(i[1])

bot_modules.get_rss_post()

bot_modules.get_vk_post(bot, vk_api)


markup.row('Ok')
markup.row('Главное меню')

markup1.row('5 последних постов')
markup1.row('5 последних постов из RSS')
markup1.row('Подписаться на обновления')
# markup1.row('Выбрать интересующие категории')
markup1.row('Назад')


@bot.message_handler(commands=['start'])
def send_welcome(message):
    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    db.execute("SELECT id FROM Users WHERE id = ?", (message.chat.id,))
    check_user = db.fetchall()
    if not check_user:
        db.execute("INSERT INTO Users (id, reg_date) VALUES (?, datetime('now', 'localtime'))", (message.chat.id,))
        database.commit()
        database.close()
    print(bot.get_chat(message.chat.id))
    bot.send_message(message.chat.id,
                     'Привет! Я бот, который поможет тебе следить за всеми новостями твоего любимого ВУЗа!',
                     reply_markup=markup_start)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def news_source(message):
    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    if message.text == 'Выбрать группы':
        bot.send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости, а затем нажми "Ок"',
                         reply_markup=markup)

    if message.text == 'Настройки':
        bot.send_message(message.chat.id, 'Выбери, что ты хочешь изменить', reply_markup=markup_settings)

    if message.text == 'Сбросить группы':
        db.execute("DELETE FROM UsersGroups WHERE uid = ?", (message.chat.id,))
        database.commit()
        bot.send_message(message.chat.id, 'Группы были сброшены', reply_markup=markup_settings)
    if message.text == 'Остановить подписку':
        db.execute("SELECT id FROM Users WHERE id = ? AND is_sub = 1", (message.chat.id,))
        subsc = db.fetchall()
        if subsc:
            db.execute("UPDATE Users SET is_sub = 0 WHERE id = ?", (message.chat.id,))
            database.commit()
            bot.send_message(message.chat.id, 'Ты отписался от обновлений')
        else:
            bot.send_message(message.chat.id, 'А ты и не был подписан на обновления :)')

    if message.text == 'Главное меню':
        bot.send_message(message.chat.id, 'Добро пожаловать в главное меню!', reply_markup=markup_start)

    for j in groups:
        if message.text == str(j[1]):
            bot_modules.group_selection(bot, message, str(j[0]))

    if message.text == 'Ok':
        bot.send_message(message.chat.id, 'Что ты хочешь получить?', reply_markup=markup1)

    if message.text == '5 последних постов':
        vk_arr = bot_modules.five_last_posts(message)
        if vk_arr:
            for _i in vk_arr:
                bot.send_message(message.chat.id, _i)
        else:
            bot.send_message(message.chat.id, 'Ты не выбрал группу')

    if message.text == '5 последних постов из RSS':
        rss_arr = bot_modules.five_last_rss(message)
        if rss_arr:
            for _i in rss_arr:
                bot.send_message(message.chat.id, _i)
        else:
            bot.send_message(message.chat.id, 'Ты не выбрал RSS')

    if message.text == 'Подписаться на обновления':
        db.execute("SELECT id FROM Users WHERE id = ? AND is_sub = 0", (message.chat.id,))
        subsc = db.fetchall()
        if subsc:
            db.execute("UPDATE Users SET is_sub = 1 WHERE id = ?", (message.chat.id,))
            database.commit()
            bot.send_message(message.chat.id, 'Ты подписался на обновления')
        else:
            bot.send_message(message.chat.id, 'Ты уже подписан на обновления')
    elif message.text == 'Назад':
        bot.send_message(message.chat.id, 'Выбери, откуда ты хочешь получить новости, а затем нажми "Ок"',
                         reply_markup=markup)


if __name__ == '__main__':
    bot.polling(none_stop=True)
    while True:
        time.sleep(200)
