import vk
import telebot
import sqlite3
import time
from telebot import types
import bot_modules

bot = telebot.TeleBot('TOKEN')

session = vk.Session()
vk_api = vk.API(session, v='5.59')

databasem = sqlite3.connect('HSE_BOT_DB.sqlite')
dbm = databasem.cursor()

# botCondition 0 - простой, 1 - отказ для подписки,
# 2 - выбор для подписки, 3 - отказ для последних, 4 - выбор для последних

markup_start = types.ReplyKeyboardMarkup()
markup_settings = types.ReplyKeyboardMarkup()
markup = types.ReplyKeyboardMarkup()
markup1 = types.ReplyKeyboardMarkup()

markup_start.row('Выбрать группы для подписки')
# markup_start.row('Настройки')

markup_settings.row('Подписаться на группы')
markup_settings.row('Отписаться от групп')

markup.row('Далее')

dbm.execute("SELECT * FROM Groups")
groups = dbm.fetchall()
# for i in range(0, len(groups)):
#     print(groups[i][0])

# for i in groups:
#     markup.row(i[1])

bot_modules.get_rss_post(bot)

bot_modules.get_vk_post(bot, vk_api)

markup1.row('5 последних постов')
markup1.row('5 последних постов из RSS')
markup1.row('Подписаться на обновления')
markup1.row('Начать')
# markup1.row('Выбрать интересующие категории')
markup1.row('Назад')


@bot.message_handler(commands=['start'])
def send_welcome(message):
    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    db.execute("SELECT id FROM Users WHERE id = ?", (message.chat.id,))
    check_user = db.fetchall()
    if not check_user:
        db.execute("INSERT INTO Users (id, reg_date, bcond) VALUES (?, datetime('now', 'localtime'), 0)",
                   (message.chat.id,))
        database.commit()
        database.close()
        print(bot.get_chat(message.chat.id))
        bot.send_message(message.chat.id,
                         'Привет! Я бот, который поможет тебе следить за всеми новостями твоего любимого ВУЗа! \n '
                         'Ты можешь получать новости регулярно по подписке или периодически запрашивать сам!',
                         reply_markup=markup_start)
    else:
        bot.send_message(message.chat.id, 'Добро пожаловать. Снова.', reply_markup=markup_start)


# @bot.message_handler(func=lambda message: True, content_types=['sticker'])
# def stckr(message):
#     print(message)
#     bot.send_sticker(message.chat.id, 'BQADBAADoAQAAuJy2QABvPab6HKF4CYC')


@bot.message_handler(func=lambda message: True, content_types=['text'])
def news_source(message):
    # bot.send_sticker(161146940, 'BQADBAADtwEAAuJy2QABsbHWsd0vf4gC')

    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    if message.text == 'Выбрать группы для подписки':
        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()

        check_if_all = 0

        markup_sub = types.ReplyKeyboardMarkup()
        markup_sub.row('Далее')
        # markup_sub.row('Выбрать все')
        for i in groups:
            if i not in active_groups:
                markup_sub.row(i[1])
                check_if_all += 1
        if check_if_all > 0:
            bot.send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости, как только они выходят'
                                              ', а затем нажми "Далее"', reply_markup=markup_sub)
        else:
            bot.send_message(message.chat.id, 'Ты подписан на все группы', reply_markup=markup)

        db.execute("UPDATE Users SET bcond = 2 WHERE id = ?", (message.chat.id,))
        database.commit()

    for j in groups:
        if message.text == str(j[1]):
            bot_modules.group_selection(bot, message, str(j[0]))
    if message.text == 'Далее':
        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()
        if bot_condition[0][0] == 2:
            db.execute("UPDATE Users SET bcond = 4 WHERE id = ?", (message.chat.id,))
            database.commit()
        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()

        check_if_all = 0

        markup_sub = types.ReplyKeyboardMarkup()
        markup_sub.row('ОК')
        # markup_sub.row('Выбрать все')
        for i in groups:
            if i not in active_groups:
                markup_sub.row(i[1])
                check_if_all += 1
        if check_if_all > 0:
            bot.send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости по запросу'
                                              ', а затем нажми "ОК"', reply_markup=markup_sub)
        else:
            bot.send_message(message.chat.id, 'Ты подписан на все группы', reply_markup=markup)

    if message.text == 'ОК':
        db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
        database.commit()

    if message.text == 'Назад':
        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()
        if bot_condition[0][0] == 4:
            db.execute("UPDATE Users SET bcond = 2 WHERE id = ?", (message.chat.id,))
            database.commit()
        # if message.text == 'Отказ от подписки':
        #     user_id = message.chat.id
        #     db.execute("SELECT gid FROM UsersGroups WHERE uid = ?", (user_id,))
        #     user_subs = db.fetchall()
        #     global isSub
        #     if user_subs:
        #         for i in user_subs:
        #             markup_sub.row(i[0])
        #         isSub = 2
        #         for j in groups:
        #             if message.text == str(j[1]):
        #                 bot_modules.group_selection(bot, message, str(j[0]))
        #         bot.send_message(message.chat.id, 'Отписаться от',
        #                          reply_markup=markup)
        #
        # if message.text == 'Выбрать группы':
        #     isSub = 1
        #     bot.send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости, а затем нажми "Ок"',
        #                      reply_markup=markup)
        #
        # if message.text == 'Настройки':
        #     bot.send_message(message.chat.id, 'Выбери, что ты хочешь изменить', reply_markup=markup_settings)
        #
        # if message.text == 'Сбросить группы':
        #     db.execute("DELETE FROM UsersGroups WHERE uid = ?", (message.chat.id,))
        #     database.commit()
        #     bot.send_message(message.chat.id, 'Группы были сброшены', reply_markup=markup_settings)
        # if message.text == 'Остановить подписку':
        #     db.execute("SELECT id FROM Users WHERE id = ? AND is_sub = 1", (message.chat.id,))
        #     subsc = db.fetchall()
        #     if subsc:
        #         db.execute("UPDATE Users SET is_sub = 0 WHERE id = ?", (message.chat.id,))
        #         database.commit()
        #         bot.send_message(message.chat.id, 'Ты отписался от обновлений')
        #     else:
        #         bot.send_message(message.chat.id, 'А ты и не был подписан на обновления :)')
        #
        # if message.text == 'Главное меню':
        #     bot.send_message(message.chat.id, 'Добро пожаловать в главное меню!', reply_markup=markup_start)
        #
        # if isSub == 1:
        #     isSub = 0
        #     for j in groups:
        #         if message.text == str(j[1]):
        #             bot_modules.group_selection(bot, message, str(j[0]))
        # if isSub == 2:
        #     isSub = 0
        #     for j in groups:
        #         if message.text == str(j[1]):
        #             bot_modules.group_unselection(bot, message, str(j[0]))
        # else:
        #     isSub = 0
        #     # bot.send_sticker(message.chat.id, 'BQADBAADoAQAAuJy2QABvPab6HKF4CYC')
        # if message.text == 'ОК':
        #     db.execute("SELECT gid FROM UsersGroups WHERE uid = ?", (message.chat.id,))
        #     user_subs = db.fetchall()
        #     if user_subs:
        #         print(user_subs)
        #     bot.send_message(message.chat.id, 'Что ты хочешь получить?', reply_markup=markup1)
        #
        # if message.text == '5 последних постов':
        #     vk_arr = bot_modules.five_last_posts(message)
        #     if vk_arr:
        #         for _i in vk_arr:
        #             bot.send_message(message.chat.id, _i)
        #     else:
        #         bot.send_message(message.chat.id, 'Ты не выбрал группу')
        #
        # if message.text == '5 последних постов из RSS':
        #     rss_arr = bot_modules.five_last_rss(message)
        #     if rss_arr:
        #         for _i in rss_arr:
        #             bot.send_message(message.chat.id, _i)
        #     else:
        #         bot.send_message(message.chat.id, 'Ты не выбрал RSS')
        #
        # if message.text == 'Подписаться на обновления':
        #     db.execute("SELECT id FROM Users WHERE id = ? AND is_sub = 0", (message.chat.id,))
        #     subsc = db.fetchall()
        #     if subsc:
        #         db.execute("UPDATE Users SET is_sub = 1 WHERE id = ?", (message.chat.id,))
        #         database.commit()
        #         bot.send_message(message.chat.id, 'Ты подписался на обновления')
        #     else:
        #         bot.send_message(message.chat.id, 'Ты уже подписан на обновления')
        # elif message.text == 'Назад':
        #     bot.send_message(message.chat.id, 'Выбери, откуда ты хочешь получить новости, а затем нажми "Ок"',
        #                      reply_markup=markup)


if __name__ == '__main__':
    bot.polling(none_stop=True)
    while True:
        time.sleep(200)
