import vk
import telebot
import sqlite3
import time
import threading
from telebot import types


databasem = sqlite3.connect('HSE_BOT_DB.sqlite')

dbm = databasem.cursor()

bot = telebot.TeleBot('TOKEN')

session = vk.Session()
vk_api = vk.API(session, v='5.59')

vk_arr = []
group_id_arr = []
vk_id = ['9793010', '20707740', '261222034']
sub_is_active = False


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


def get_post():
    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    for i in groups:
        print(i[1])
        db.execute("SELECT MAX(p_date) FROM Posts WHERE gid = ?", (str(i[0]),))
        last_post = db.fetchall()
        for j in last_post:
            print(j)
        db.execute("SELECT u.id FROM Users as u, UsersGroups as ug WHERE u.id = ug.uid AND u.is_sub = 1 AND ug.gid = ?",
                   (str(i[0]),))
        sub_users = db.fetchall()
        print(sub_users)
        posts = vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
        for p in posts['items']:
            if type(p) != int:
                if 'id' in p:
                    if int(p['date']) > int(last_post[0][0]):
                        print('new post')
                        link = 'https://vk.com/wall-' + i[0] + '_' + str(p['id'])
                        for u in sub_users:
                            bot.send_message(u[0], link)

    db.execute("DELETE FROM Posts")

    for i in groups:
        posts = vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
        for _k in posts['items']:
            if type(_k) != int:
                if 'id' in _k:
                    db.execute("INSERT INTO Posts (id, gid, p_date) VALUES (?, ?, ?)",
                               (str(i[0]) + '_' + str(_k['id']), str(i[0]), str(_k['date'])))

    database.commit()
    database.close()
    t = threading.Timer(60, get_post)
    t.start()


get_post()


markup.row('Ok')
markup.row('Главное меню')

markup1.row('5 последних постов')
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

    global vk_arr, group_id_arr

    if message.text == 'Выбрать группы':
        bot.send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости, а затем нажми "Ок"',
                         reply_markup=markup)

    if message.text == 'Настройки':
        bot.send_message(message.chat.id, 'Выбери, что ты хочешь изменить', reply_markup=markup_settings)

    if message.text == 'Сбросить группы':
        group_id_arr = []
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
            group_selection(message, str(j[0]))

    if message.text == 'Ok':
        bot.send_message(message.chat.id, 'Что ты хочешь получить?', reply_markup=markup1)

    if message.text == '5 последних постов':
        vk_arr = five_last_posts(message)
        if vk_arr:
            for _i in vk_arr:
                bot.send_message(message.chat.id, _i)
        else:
            bot.send_message(message.chat.id, 'Ты не выбрал группу')
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


def group_selection(msg, grp_id):
    dtbs = sqlite3.connect('HSE_BOT_DB.sqlite')
    dtbs_c = dtbs.cursor()

    dtbs_c.execute("SELECT gid FROM UsersGroups WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
    check_group = dtbs_c.fetchall()
    print(check_group)
    if not check_group:
        print(msg.chat.id)
        dtbs_c.execute("INSERT INTO UsersGroups VALUES(?, ?)", (msg.chat.id, grp_id,))
        dtbs.commit()
        group_id_arr.append(grp_id)
        bot.send_message(msg.chat.id, 'Ты выбрал ' + msg.text)
    else:
        bot.send_message(msg.chat.id, msg.text + ' уже была выбрана')

    dtbs.close()


def five_last_posts(msg):
    arr_link = []
    link_count = 0
    dtbs = sqlite3.connect('HSE_BOT_DB.sqlite')
    dtbs_c = dtbs.cursor()

    dtbs_c.execute("SELECT p.id FROM Posts as p, UsersGroups as ug WHERE ug.uid = ? AND ug.gid = p .gid "
                   "ORDER BY p.p_date DESC ", (msg.chat.id,))
    flp = dtbs_c.fetchall()
    for i in flp:
        link = 'https://vk.com/wall-' + str(i[0])
        if link_count < 5:
            arr_link.append(link)
            link_count += 1
            print(link)

    dtbs.close()
    return arr_link


if __name__ == '__main__':
    bot.polling(none_stop=True)
    while True:
        time.sleep(200)
