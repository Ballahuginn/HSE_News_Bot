import vk
import telebot
import sqlite3
import time
from telebot import types
import bot_modules

bot = telebot.TeleBot('281761912:AAErjD0U7krOu6-8-j96rzpIC1xDLjF8dLs')

session = vk.Session()
vk_api = vk.API(session, v='5.59')

databasem = sqlite3.connect('HSE_BOT_DB.sqlite')
dbm = databasem.cursor()

# botCondition 0 - простой, 1 - отказ для подписки,
# 2 - выбор для подписки, 3 - отказ для последних, 4 - выбор для последних

markup_none = types.ReplyKeyboardHide()

dbm.execute("SELECT * FROM Groups")
groups = dbm.fetchall()

#bot_modules.get_rss_post(bot)

#bot_modules.get_vk_post(bot, vk_api)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()
    markup = types.ReplyKeyboardMarkup()
    markup.row('Выбрать группы для подписки')
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
                         reply_markup=markup)
    else:
        markup.row('Выбрать группы для отписки')
        markup.row('Главное меню')
        bot.send_message(message.chat.id, 'Добро пожаловать. Снова.', reply_markup=markup)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def news_source(message):

    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    if message.text == 'Выбрать группы для отписки':
        db.execute("UPDATE Users SET bcond = 1 WHERE id = ?", (message.chat.id,))
        database.commit()

        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()

        markup = types.ReplyKeyboardMarkup()
        markup.row('Далее')
        markup.row('Отменить все')
        check_if_all = bot_modules.groups_as_buttons_unsub(groups, active_groups, markup)
        if check_if_all > 0:
            bot.send_message(message.chat.id, 'Выбери группы, откуда ты НЕ хочешь получать новости, как только они '
                                              'выходят, а затем нажми "Далее"', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, 'Ты НЕ подписан на все группы получать новости, '
                                              'как только они выходят')
            bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)

    if message.text == 'Выбрать группы для подписки':
        db.execute("UPDATE Users SET bcond = 2 WHERE id = ?", (message.chat.id,))
        database.commit()

        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()
        markup = types.ReplyKeyboardMarkup()
        markup.row('Далее')
        markup.row('Выбрать все')
        check_if_all = bot_modules.groups_as_buttons_sub(groups, active_groups, markup)
        if check_if_all > 0:
            if len(active_groups) != 0:
                bot.send_message(message.chat.id, 'Ты уже подписан на следующие группы:')
                for i in active_groups:
                    bot.send_message(message.chat.id, i[1])
            bot.send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости, как только они выходят'
                                              ', а затем нажми "Далее"', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                              'как только они выходят.')
            bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)

    for j in groups:
        if message.text == str(j[1]):
            db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
            bot_condition = db.fetchall()
            bot_modules.group_selection(bot, message, str(j[0]), bot_condition)
            markup = types.ReplyKeyboardMarkup()
            if bot_condition[0][0] == 1:
                markup.row('Далее')
                markup.row('Отменить все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_unsub(groups, active_groups, markup)
                if check_if_all == 0:
                    bot.send_message(message.chat.id,
                                     'Ты не подписан ни на одну группу для получения постоянных новостей')
                    bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)
                else:
                    bot.send_message(message.chat.id, 'Выбери группы или нажми "Далее"', reply_markup=markup)
            if bot_condition[0][0] == 2:
                markup.row('Далее')
                markup.row('Выбрать все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_sub(groups, active_groups, markup)
                if check_if_all == 0:
                    bot.send_message(message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                                      'как только они выходят.')
                    bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)
                else:
                    bot.send_message(message.chat.id, 'Выбери группы или нажми "Далее"', reply_markup=markup)
            if bot_condition[0][0] == 3:
                markup.row('Завершить')
                markup.row('Отменить все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_unsub(groups, active_groups, markup)
                if check_if_all == 0:
                    bot.send_message(message.chat.id, 'Ты НЕ подписан на получение новостей по запросу',
                                     reply_markup=markup)
                    markup = bot_modules.press_done(db, database, message, types)
                    bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)
                else:
                    bot.send_message(message.chat.id, 'Выбери группы или нажми "Завершить"', reply_markup=markup)
            if bot_condition[0][0] == 4:

                markup.row('Завершить')
                markup.row('Выбрать все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_sub(groups, active_groups, markup)
                if check_if_all == 0:
                    bot.send_message(message.chat.id, 'Ты подписан на все группы для получения новостей '
                                                      'по запросу')
                    markup = bot_modules.press_done(db, database, message, types)
                    bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)
                else:
                    bot.send_message(message.chat.id, 'Выбери группы или нажми "Завершить"', reply_markup=markup)

    if message.text == 'Отменить все':
        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()
        if bot_condition[0][0] == 1:
            db.execute("UPDATE UsersGroups SET upget = 0 WHERE uid = ?", (message.chat.id,))
            database.commit()
            bot.send_message(message.chat.id, 'Ты отписался от всех групп для получения новостей, '
                                              'как только они выходят', markup)
            bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)
        if bot_condition[0][0] == 3:
            db.execute("UPDATE UsersGroups SET fetget = 0 WHERE uid = ?", (message.chat.id,))
            database.commit()
            bot.send_message(message.chat.id, 'Ты отписался от всех групп для получения новостей по запросу')
            markup = bot_modules.press_done(db, database, message, types)
            bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)

    if message.text == 'Выбрать все':
        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()
        if bot_condition[0][0] == 2:
            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id", (message.chat.id,))
            uncreated = db.fetchall()
            db.execute("UPDATE UsersGroups SET upget = 1 WHERE uid = ?", (message.chat.id,))
            database.commit()
            for i in groups:
                if i not in uncreated:
                    print(i[0])
                    db.execute("INSERT INTO UsersGroups (uid, gid, upget, fetget) VALUES (?, ?, 1, 0)",
                               (message.chat.id, i[0],))
                    database.commit()
            bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)
        if bot_condition[0][0] == 4:
            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id", (message.chat.id,))
            uncreated = db.fetchall()
            db.execute("UPDATE UsersGroups SET fetget = 1 WHERE uid = ?", (message.chat.id,))
            database.commit()
            for i in groups:
                if i not in uncreated:
                    print(i[0])
                    db.execute("INSERT INTO UsersGroups (uid, gid, upget, fetget) VALUES (?, ?, 0, 1)",
                               (message.chat.id, i[0],))
                    database.commit()
            markup = bot_modules.press_done(db, database, message, types)
            bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)

    if message.text == 'Далее':
        bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)

    if message.text == 'Завершить':
        markup = bot_modules.press_done(db, database, message, types)
        bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)

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

    if message.text == 'Настройки':
        markup = types.ReplyKeyboardMarkup()
        markup.row('Выбрать группы для подписки')
        markup.row('Выбрать группы для отписки')
        markup.row('Главное меню')
        bot.send_message(message.chat.id, 'Выбери, что ты хочешь сделать', reply_markup=markup)

    if message.text == 'Главное меню':
        markup = bot_modules.press_done(db, database, message, types)
        bot.send_message(message.chat.id, 'Добро пожаловать в главное меню!', reply_markup=markup)

    if message.text == 'О проекте':
        bot.send_message(message.chat.id, 'Этот бот является дипломной работой студентов 4 курса ДКИ МИЭМ '
                                          'Барсукова Павла и Садонцева Максима.\n'
                                          'Этот бот является первым новостым ботом НИУ ВШЭ!\n'
                                          'Плагиат и копирование данного бота преследуются по закону!')

    if message.text == 'Оставить пожелания':
        db.execute("UPDATE Users SET review = 1 WHERE id = ?", (message.chat.id,))
        database.commit()
        bot.send_message(message.chat.id, 'Как ты думаешь, чего не хвататет этому боту?', reply_markup=markup_none)

    else:
        db.execute("SELECT review FROM Users WHERE id = ?", (message.chat.id,))
        review = db.fetchall()
        if review[0][0] == 1:
            db.execute("INSERT INTO Reviews (uid, rev_text, rev_date) VALUES (?, ?, datetime('now', 'localtime'))",
                       (message.chat.id, message.text))
            db.execute("UPDATE Users SET review = 0 WHERE id = ?", (message.chat.id,))
            database.commit()
            markup = bot_modules.press_done(db, database, message, types)
            bot.send_message(message.chat.id, 'Спасибо за отзыв! Твое мнение очень важно для нас!', reply_markup=markup)


if __name__ == '__main__':
    bot.polling(none_stop=True)
    while True:
        time.sleep(200)
