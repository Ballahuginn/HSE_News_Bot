import vk
import sqlite3
import time
from telebot import types
import bot_modules

dbpath = bot_modules.dbpath
bot = bot_modules.bot


session = vk.Session()
vk_api = vk.API(session, v=bot_modules.api_ver, timeout=bot_modules.timeout)

databasem = sqlite3.connect(dbpath)
dbm = databasem.cursor()

# botCondition 0 - простой, 1 - отказ для подписки,
# 2 - выбор для подписки, 3 - отказ для последних, 4 - выбор для последних

dbm.execute("SELECT id FROM Users")
users = dbm.fetchall()

markup_none = types.ReplyKeyboardRemove()

dbm.execute("SELECT * FROM Groups")
groups = dbm.fetchall()

bot_modules.get_rss_post(bot)

bot_modules.get_vk_post(bot, vk_api)

bot_modules.evening_hse(bot, vk_api)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    markup = types.ReplyKeyboardMarkup()
    markup.row('\U00002705 Выбрать группы для подписки')
    db.execute("SELECT id FROM Users WHERE id = ?", (message.chat.id,))
    check_user = db.fetchall()
    if not check_user:
        db.execute("INSERT INTO Users (id, reg_date, bcond, username, first_name, last_name) VALUES (?, datetime('now', 'localtime'), 0, ?, ?, ?)",
                   (message.chat.id, message.chat.username, message.chat.first_name, message.chat.last_name,))
        database.commit()
        database.close()
        # print(bot.get_chat(message.chat.id))
        bot.send_message(message.chat.id,
                         'Привет! Я бот, который поможет тебе следить за всеми новостями твоего любимого ВУЗа! \n'
                         'Я могу присылать тебе новости из разных групп ВК, связанных с Вышкой.\n'
                         'А еще у меня есть вечерняя рассылка популярных новостей \U0001F306',
                         reply_markup=markup)
    else:
        markup.row('\U0001F6AB Выбрать группы для отписки')
        markup.row('\U0001F51D Главное меню')
        bot.send_message(message.chat.id, 'Добро пожаловать. Снова.', reply_markup=markup)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def news_source(message):

    database = sqlite3.connect(dbpath)
    db = database.cursor()

    if message.text == '\U0001F6AB Выбрать группы для отписки':
        db.execute("UPDATE Users SET bcond = 1 WHERE id = ?", (message.chat.id,))
        database.commit()

        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()

        markup = types.ReplyKeyboardMarkup()
        markup.row('\U000027A1 Далее')
        markup.row('Отписаться от всех')
        check_if_all = bot_modules.groups_as_buttons_unsub(groups, active_groups, markup)
        if check_if_all > 0:
            bot.send_message(message.chat.id, 'Выбери группы, откуда ты НЕ хочешь получать новости, как только они '
                                              'выходят, а затем нажми "Далее"', reply_markup=markup)
        else:
            bot_modules.send_message(bot, message.chat.id,
                             'Ты не подписан ни на одну группу для получения новостей, как только они выходят', False)
            bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)

    if message.text == '\U00002705 Выбрать группы для подписки':
        db.execute("UPDATE Users SET bcond = 2 WHERE id = ?", (message.chat.id,))
        database.commit()

        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()
        markup = types.ReplyKeyboardMarkup()
        markup.row('\U000027A1 Далее')
        markup.row('Выбрать все')
        check_if_all = bot_modules.groups_as_buttons_sub(groups, active_groups, markup)
        if check_if_all > 0:
            if len(active_groups) != 0:
                bot_modules.send_message(bot, message.chat.id, 'Ты уже подписан на следующие группы:', False)
                for i in active_groups:
                    bot_modules.send_message(bot, message.chat.id, i[1], False)
            bot.send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости, как только они выходят'
                                              ', а затем нажми "Далее"', reply_markup=markup)
        else:
            bot_modules.send_message(bot, message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                              'как только они выходят', False)
            bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)

    for j in groups:
        if message.text == str(j[1]):
            db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
            bot_condition = db.fetchall()
            bot_modules.group_selection(bot, message, str(j[0]), bot_condition)
            markup = types.ReplyKeyboardMarkup()
            if bot_condition[0][0] == 1:
                markup.row('\U000027A1 Далее')
                markup.row('Отписаться от всех')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_unsub(groups, active_groups, markup)
                if check_if_all == 0:
                    bot_modules.send_message(bot, message.chat.id,
                                     'Ты не подписан ни на одну группу для получения новостей, как только они выходят', False)
                    bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)
                else:
                    bot.send_message(message.chat.id, 'Выбери группы или нажми "Далее"', reply_markup=markup)
            if bot_condition[0][0] == 2:
                markup.row('\U000027A1 Далее')
                markup.row('Выбрать все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_sub(groups, active_groups, markup)
                if check_if_all == 0:
                    bot_modules.send_message(bot, message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                                      'как только они выходят', False)
                    bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)
                else:
                    bot.send_message(message.chat.id, 'Выбери группы или нажми "Далее"', reply_markup=markup)
            if bot_condition[0][0] == 3:
                markup.row('\U0001F3C1 Завершить')
                markup.row('Отписаться от всех')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_unsub(bot_modules.vk_groups, active_groups, markup)
                if check_if_all == 0:
                    bot.send_message(message.chat.id, 'Ты НЕ подписан на \U0001F306 Вечернюю Вышку',
                                     reply_markup=markup)
                    markup = bot_modules.press_done(db, database, message, types)
                    bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)
                else:
                    bot.send_message(message.chat.id, 'Выбери группы или нажми "Завершить"', reply_markup=markup)
            if bot_condition[0][0] == 4:

                markup.row('\U0001F3C1 Завершить')
                markup.row('Выбрать все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_sub(bot_modules.vk_groups, active_groups, markup)
                if check_if_all == 0:
                    bot_modules.send_message(bot, message.chat.id, 'Ты подписан на все группы для получения новостей '
                                                      'в \U0001F306 Вечерней Вышке', False)
                    markup = bot_modules.press_done(db, database, message, types)
                    bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)
                else:
                    bot.send_message(message.chat.id, 'Выбери группы или нажми "Завершить"', reply_markup=markup)

    if message.text == 'Отписаться от всех':
        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()
        if bot_condition[0][0] == 1:
            db.execute("UPDATE UsersGroups SET upget = 0 WHERE uid = ?", (message.chat.id,))
            database.commit()
            bot_modules.send_message(bot, message.chat.id, 'Ты отписался от всех групп, из которых получал новости, '
                                              'как только они выходили', False)
            bot_modules.press_next(db, database, message, bot_modules.vk_groups, bot, bot_modules, types)
        if bot_condition[0][0] == 3:
            db.execute("UPDATE UsersGroups SET fetget = 0 WHERE uid = ?", (message.chat.id,))
            database.commit()
            bot_modules.send_message(bot, message.chat.id, 'Ты отписался от всех групп для \U0001F306 Вечерней Вышки', False)
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
                    # print(i[0])
                    db.execute("INSERT INTO UsersGroups (uid, gid, upget, fetget) VALUES (?, ?, 1, 0)",
                               (message.chat.id, i[0],))
                    database.commit()
            bot_modules.press_next(db, database, message, bot_modules.vk_groups, bot, bot_modules, types)
        if bot_condition[0][0] == 4:
            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id", (message.chat.id,))
            uncreated = db.fetchall()
            db.execute("UPDATE UsersGroups SET fetget = 1 WHERE uid = ?", (message.chat.id,))
            database.commit()
            for i in groups:
                if i not in uncreated:
                    # print(i[0])
                    db.execute("INSERT INTO UsersGroups (uid, gid, upget, fetget) VALUES (?, ?, 0, 1)",
                               (message.chat.id, i[0],))
                    database.commit()
            markup = bot_modules.press_done(db, database, message, types)
            bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)

    if message.text == '\U000027A1 Далее':
        bot_modules.press_next(db, database, message, groups, bot, bot_modules, types)

    if message.text == '\U0001F3C1 Завершить':
        markup = bot_modules.press_done(db, database, message, types)
        bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)

    if message.text == '5 последних постов':
        vk_arr = bot_modules.five_last_posts(message)
        if vk_arr:
            for _i in vk_arr:
                bot_modules.send_message(bot, message.chat.id, _i, False)
        else:
            bot_modules.send_message(bot, message.chat.id, 'Ты не выбрал группы', False)

    if message.text == '5 последних постов из RSS':
        rss_arr = bot_modules.five_last_rss(message)
        if rss_arr:
            for _i in rss_arr:
                bot.send_message(message.chat.id, _i)
        else:
            bot_modules.send_message(bot, message.chat.id, 'Ты не выбрал RSS', False)

    if message.text == '\U0001f527 Настройки':
        markup = types.ReplyKeyboardMarkup()
        markup.row('\U00002705 Выбрать группы для подписки')
        markup.row('\U0001F6AB Выбрать группы для отписки')
        markup.row('\U0001F51D Главное меню')
        bot.send_message(message.chat.id, 'Выбери, что ты хочешь сделать', reply_markup=markup)

    if message.text == '\U0001F51D Главное меню':
        markup = bot_modules.press_done(db, database, message, types)
        bot.send_message(message.chat.id, 'Добро пожаловать в главное меню!', reply_markup=markup)

    if message.text == '\U00002139 О проекте':
        bot_modules.send_message(bot, message.chat.id, 'Этот бот является дипломной работой студентов 4 курса ДКИ МИЭМ '
                                          'Барсукова Павла и Садонцева Максима.\n'
                                          'Этот бот является первым новостым ботом НИУ ВШЭ!\n'
                                          'Плагиат и копирование данного бота преследуются по закону!', False)

    if message.text == '\U0001F4AC Оставить пожелания':
        db.execute("UPDATE Users SET bcond = 5 WHERE id = ?", (message.chat.id,))
        database.commit()
        bot.send_message(message.chat.id, 'Как ты думаешь, чего не хвататет этому боту? \U0001F914', reply_markup=markup_none)

    else:
        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()
        if bot_condition[0][0] == 5:
            db.execute("INSERT INTO Reviews (uid, rev_text, rev_date) VALUES (?, ?, datetime('now', 'localtime'))",
                       (message.chat.id, message.text))
            db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
            database.commit()
            markup = bot_modules.press_done(db, database, message, types)
            bot.send_message(message.chat.id, 'Спасибо за отзыв! Твое мнение очень важно для нас! \U0001F64F', reply_markup=markup)


if __name__ == '__main__':
    bot.polling(none_stop=True)
    while True:
        time.sleep(200)
