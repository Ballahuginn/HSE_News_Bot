import configparser
import datetime
import feedparser
import re
import sqlite3
import telebot
import threading
import time
import traceback
import vk
from math import radians, cos, sin, asin, sqrt
from telebot import types
import categorizator

config = configparser.ConfigParser()
config.read('config.ini')

Month = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'June': '06',
         'July': '07', 'Aug': '08', 'Sept': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}

bot = telebot.TeleBot(config['TELEGRAM.API']['TOKEN'])
api_ver = config['VK.API']['ver']
timeout = int(config['VK.API']['timeout'])
vk_api = vk.API(vk.Session(), v=api_ver, timeout=timeout)

dbpath = config['DEFAULT']['DB']

admin = config['ADMIN']['id'].split(', ')
broadcast = config['STICKER']['broadcast']
new_group = config['STICKER']['new_group']
cancel = config['STICKER']['cancel']
number_of_users = config['STICKER']['number_of_users']

start_h = int(config['EVENING']['start_h'])
start_m = int(config['EVENING']['start_m'])
end_h = int(config['EVENING']['end_h'])
end_m = int(config['EVENING']['end_m'])

vk_timer = int(config['VK']['timer'])
rss_timer = int(config['RSS']['timer'])

# config.read('locale_ru.ini')
# nextb = (config['COMMANDS']['NEXT'])

markup_none = types.ReplyKeyboardMarkup()
markup_none.row('\U0001F51D Назад в главное меню')


# botCondition 0 - простой, 1 - отказ для подписки,
# 2 - выбор для подписки, 3 - отказ для вечерней вышки, 4 - выбор для вечерней вышки, 5 - отзыв,
# 12 - основные группы, 34 - вечерняя вышка, 1234 - новый пользователь,
# 666 - броадкаст, 777 - новая группа


def send_welcome(message):
    database = sqlite3.connect(dbpath)
    db = database.cursor()

    db.execute("SELECT id FROM Users WHERE id = ?", (message.chat.id,))
    check_user = db.fetchall()

    if not check_user:
        db.execute("INSERT INTO Users (id, reg_date, bcond, username, first_name, last_name) VALUES "
                   "(?, datetime('now', 'localtime'), 1234, ?, ?, ?)",
                   (message.chat.id, message.chat.username, message.chat.first_name, message.chat.last_name,))
        database.commit()
        # print(bot.get_chat(message.chat.id))

        send_message(message.chat.id, 'Привет, ' + user_name(message.chat.id) +
                     '!\nЯ бот, который поможет тебе следить за всеми новостями твоего любимого ВУЗа! \n'
                     'Я могу присылать тебе новости из разных групп ВК, связанных с Вышкой.\n'
                     'А еще у меня есть вечерняя рассылка популярных новостей \U0001F306', False)

        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()
        markup = types.ReplyKeyboardMarkup()
        markup.row('\U000027A1 Далее')
        markup.row('Выбрать все')
        check_if_all = groups_as_buttons_sub(groups_list(), active_groups, markup)
        if check_if_all > 0:
            if len(active_groups) != 0:
                grp = 'Ты уже подписан на следующие группы:\n\n'
                for i in active_groups:
                    grp += str(i[1]) + '\n'
                send_message(message.chat.id, grp, False)
            send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости, '
                                          'как только они выходят, а затем нажми "Далее"', markup)
        else:
            send_message(message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                          'как только они выходят', False)
            press_next(message.chat.id)

    else:
        markup = press_done(message)
        send_message(message.chat.id, 'Добро пожаловать. Снова.\U000026A1', markup)

    database.close()


def send_goodbye(message):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT id FROM Users WHERE id = ?", (message.chat.id,))
    check_user = db.fetchall()

    if check_user:
        db.execute("UPDATE UsersGroups SET upget = 0, fetget = 0 WHERE uid = ?", (message.chat.id,))
        database.commit()
        database.close()
        send_message(message.chat.id, 'Очень жаль, что ты решил отписаться от всего \U0001F614\n'
                                      'Но я всегда буду рад, если ты снова решишь подписаться!\n'
                                      'Нужно просто нажать /start \U0001F609', markup_none)
    else:
        send_message(message.chat.id, 'Мне кажется или ты еще не начинал пользоваться ботом?\n'
                                      'Чтобы начать им пользоваться нажми /start \U0001F60E', markup_none)

    database.close()


def main_menu(message):
    #print(message.text)
    if message.text == '\U0001F6AB Выбрать группы для отписки':
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()

        if bot_condition[0][0] == 12:
            db.execute("UPDATE Users SET bcond = 1 WHERE id = ?", (message.chat.id,))
            database.commit()

            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                       (message.chat.id,))
            active_groups = db.fetchall()

            markup = types.ReplyKeyboardMarkup()
            markup.row('\U0001F3C1 Завершить')
            markup.row('Отписаться от всех')
            check_if_all = groups_as_buttons_unsub(groups_list(), active_groups, markup)
            if check_if_all > 0:
                send_message(message.chat.id, 'Выбери группы, откуда ты не хочешь получать новости, '
                                              'как только они выходят, а затем нажми "Завершить"', markup)
            else:
                send_message(message.chat.id, 'Ты не подписан ни на одну группу для получения новостей, '
                                              'как только они выходят', False)
                markup = press_done(message)
                send_message(message.chat.id, 'Настройка завершена', markup)

        if bot_condition[0][0] == 34:
            db.execute("UPDATE Users SET bcond = 3 WHERE id = ?", (message.chat.id,))
            database.commit()

            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                       (message.chat.id,))
            active_groups = db.fetchall()

            markup = types.ReplyKeyboardMarkup()
            markup.row('\U0001F3C1 Завершить')
            markup.row('Отписаться от всех')
            check_if_all = groups_as_buttons_unsub(vk_groups_list(), active_groups, markup)
            if check_if_all > 0:
                send_message(message.chat.id, 'Выбери группы, откуда ты не хочешь получать новости '
                                              'в \U0001F306 Вечерней Вышке, а затем нажми "Завершить"', markup)
            else:
                send_message(message.chat.id, 'Ты не подписан на \U0001F306 Вечернюю Вышку', False)
                markup = press_done(message)
                send_message(message.chat.id, 'Настройка завершена', markup)

        database.close()

    if message.text == '\U00002705 Выбрать группы для подписки':
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()

        if bot_condition[0][0] == 12:
            db.execute("UPDATE Users SET bcond = 2 WHERE id = ?", (message.chat.id,))
            database.commit()

            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                       (message.chat.id,))
            active_groups = db.fetchall()
            markup = types.ReplyKeyboardMarkup()
            markup.row('\U0001F3C1 Завершить')
            markup.row('Выбрать все')
            check_if_all = groups_as_buttons_sub(groups_list(), active_groups, markup)
            if check_if_all > 0:
                if len(active_groups) != 0:
                    grp = 'Ты уже подписан на следующие группы:\n\n'
                    for i in active_groups:
                        grp += str(i[1]) + '\n'
                    send_message(message.chat.id, grp, False)
                send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости, '
                                              'как только они выходят, а затем нажми "Завершить"', markup)
            else:
                send_message(message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                              'как только они выходят', False)
                markup = press_done(message)
                send_message(message.chat.id, 'Настройка завершена', markup)

        if bot_condition[0][0] == 34:
            db.execute("UPDATE Users SET bcond = 4 WHERE id = ?", (message.chat.id,))
            database.commit()

            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1 AND ug.gid",
                       (message.chat.id,))
            active_groups = db.fetchall()
            markup = types.ReplyKeyboardMarkup()
            markup.row('\U0001F3C1 Завершить')
            markup.row('Выбрать все')
            check_if_all = groups_as_buttons_sub(vk_groups_list(), active_groups, markup)
            if check_if_all > 0:
                send_message(message.chat.id, 'Выбери группы для Вечерней Вышки, а затем нажми "\U0001F3C1 Завершить"',
                             markup)
                if len(active_groups) != 0:
                    grp = 'Ты уже подписан на следующие группы:\n\n'
                    for i in active_groups:
                        grp += str(i[1]) + '\n'
                    send_message(message.chat.id, grp, False)
            else:
                send_message(message.chat.id, 'Ты уже подписан на все группы для \U0001F306 Вечерней Вышки', False)
                markup = press_done(message)
                send_message(message.chat.id, 'Настройка завершена', markup)

        database.close()

    for j in groups_list():
        if message.text == str(j[1]):
            database = sqlite3.connect(dbpath)
            db = database.cursor()

            db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
            bot_condition = db.fetchall()
            group_selection(message, str(j[0]), bot_condition)
            markup = types.ReplyKeyboardMarkup()

            if bot_condition[0][0] == 1:
                markup.row('\U0001F3C1 Завершить')
                markup.row('Отписаться от всех')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = groups_as_buttons_unsub(groups_list(), active_groups, markup)
                if check_if_all == 0:
                    send_message(message.chat.id, 'Ты не подписан ни на одну группу для получения '
                                                  'новостей, как только они выходят', False)
                    markup = press_done(message)
                    send_message(message.chat.id, 'Настройка завершена', markup)
                else:
                    send_message(message.chat.id, 'Выбери группы или нажми "Далее"', markup)

            if bot_condition[0][0] == 2:
                markup.row('\U0001F3C1 Завершить')
                markup.row('Выбрать все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = groups_as_buttons_sub(groups_list(), active_groups, markup)
                if check_if_all == 0:
                    send_message(message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                                  'как только они выходят', False)
                    markup = press_done(message)
                    send_message(message.chat.id, 'Настройка завершена', markup)
                else:
                    send_message(message.chat.id, 'Выбери группы или нажми "Завершить"', markup)

            if bot_condition[0][0] == 3:
                markup.row('\U0001F3C1 Завершить')
                markup.row('Отписаться от всех')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1 AND ug.gid",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = groups_as_buttons_unsub(vk_groups_list(), active_groups, markup)
                if check_if_all == 0:
                    send_message(message.chat.id, 'Ты не подписан на \U0001F306 Вечернюю Вышку', markup)
                    markup = press_done(message)
                    send_message(message.chat.id, 'Настройка завершена', markup)
                else:
                    send_message(message.chat.id, 'Выбери группы или нажми "Завершить"', markup)

            if bot_condition[0][0] == 4:
                markup.row('\U0001F3C1 Завершить')
                markup.row('Выбрать все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1 AND ug.gid",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = groups_as_buttons_sub(vk_groups_list(), active_groups, markup)
                if check_if_all == 0:
                    send_message(message.chat.id, 'Ты подписан на все группы для получения новостей '
                                                  'в \U0001F306 Вечерней Вышке', False)
                    markup = press_done(message)
                    send_message(message.chat.id, 'Настройка завершена', markup)
                else:
                    send_message(message.chat.id, 'Выбери группы или нажми "Завершить"', markup)

            if bot_condition[0][0] == 1234:
                markup.row('\U000027A1 Далее')
                markup.row('Выбрать все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = groups_as_buttons_sub(groups_list(), active_groups, markup)
                if check_if_all == 0:
                    send_message(message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                                  'как только они выходят', False)
                    markup = press_done(message)
                    send_message(message.chat.id, 'Настройка завершена', markup)
                else:
                    send_message(message.chat.id, 'Выбери группы или нажми "Далее"', markup)

            database.close()

    if message.text == 'Отписаться от всех':
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()

        if bot_condition[0][0] == 1:
            db.execute("UPDATE UsersGroups SET upget = 0 WHERE uid = ?", (message.chat.id,))
            database.commit()
            send_message(message.chat.id, 'Ты отписался от всех групп, из которых получал новости, '
                                          'как только они выходили', False)
            markup = press_done(message)
            send_message(message.chat.id, 'Настройка завершена', markup)

        if bot_condition[0][0] == 3:
            db.execute("UPDATE UsersGroups SET fetget = 0 WHERE uid = ?", (message.chat.id,))
            database.commit()
            send_message(message.chat.id, 'Ты отписался от всех групп для \U0001F306 Вечерней Вышки', False)
            markup = press_done(message)
            send_message(message.chat.id, 'Настройка завершена', markup)

        database.close()

    if message.text == 'Выбрать все':
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()

        if bot_condition[0][0] == 2:
            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id", (message.chat.id,))
            uncreated = db.fetchall()
            db.execute("UPDATE UsersGroups SET upget = 1 WHERE uid = ?", (message.chat.id,))
            database.commit()
            for i in groups_list():
                if i not in uncreated:
                    db.execute("INSERT INTO UsersGroups (uid, gid, upget, fetget) VALUES (?, ?, 1, 0)",
                               (message.chat.id, i[0],))
                    database.commit()
            markup = press_done(message)
            send_message(message.chat.id, 'Настройка завершена', markup)

        if bot_condition[0][0] == 4:
            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id AND ug.gid NOT LIKE 'rss%'", (message.chat.id,))
            uncreated = db.fetchall()
            db.execute("UPDATE UsersGroups SET fetget = 1 WHERE uid = ? AND gid NOT LIKE 'rss%'", (message.chat.id,))
            database.commit()
            for i in vk_groups_list():
                if i not in uncreated:
                    db.execute("INSERT INTO UsersGroups (uid, gid, upget, fetget) VALUES (?, ?, 0, 1)",
                               (message.chat.id, i[0],))
                    database.commit()
            markup = press_done(message)
            send_message(message.chat.id, 'Настройка завершена', markup)

        if bot_condition[0][0] == 1234:
            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id", (message.chat.id,))
            uncreated = db.fetchall()
            db.execute("UPDATE UsersGroups SET upget = 1 WHERE uid = ?", (message.chat.id,))
            database.commit()
            for i in groups_list():
                if i not in uncreated:
                    db.execute("INSERT INTO UsersGroups (uid, gid, upget, fetget) VALUES (?, ?, 1, 0)",
                               (message.chat.id, i[0],))
                    database.commit()
            press_next(message)

        database.close()

    if message.text == '\U000027A1 Далее':
        press_next(message)

    if message.text == '\U0001F3C1 Завершить':
        markup = press_done(message)
        send_message(message.chat.id, 'Настройка завершена', markup)

    if message.text == '\U0001f527 Настройки':
        markup = types.ReplyKeyboardMarkup()
        markup.row('\U0001F4F1 Основные группы')
        markup.row('\U0001F306 Вечерняя Вышка')
        markup.row('\U0001F51D Назад в главное меню')
        send_message(message.chat.id, 'Выбери, что ты хочешь настроить:', markup)

    if message.text == '\U0001F4F1 Основные группы':
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        db.execute("UPDATE Users SET bcond = 12 WHERE id = ?", (message.chat.id,))
        database.commit()
        markup = types.ReplyKeyboardMarkup()
        markup.row('\U00002705 Выбрать группы для подписки')
        markup.row('\U0001F6AB Выбрать группы для отписки')
        markup.row('\U0001f527 Настройки')
        send_message(message.chat.id, 'Выбери, что ты хочешь сделать:', markup)

        database.close()

    if message.text == '\U0001F306 Вечерняя Вышка':
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        db.execute("UPDATE Users SET bcond = 34 WHERE id = ?", (message.chat.id,))
        database.commit()
        markup = types.ReplyKeyboardMarkup()
        markup.row('\U00002705 Выбрать группы для подписки')
        markup.row('\U0001F6AB Выбрать группы для отписки')
        markup.row('\U0001f527 Настройки')
        send_message(message.chat.id, '\U0001F306 Вечерняя Вышка - это рассылка до 5 самых популярных материалов '
                                      'за день.\nОна будет приходить ежедневно в 9 вечера \U0001F558'
                                      '\n\nВыбери, что ты хочешь сделать:', markup)

        database.close()

    if message.text == '\U0001F51D Назад в главное меню':
        markup = press_done(message)
        send_message(message.chat.id, 'Добро пожаловать в главное меню!', markup)

    if message.text == '\U00002139 О проекте':
        send_message(message.chat.id, 'Этот бот является дипломной работой студентов 4 курса ДКИ МИЭМ '
                                      '<a href="http://t.me/Ballahuginn">Барсукова Павла</a> и '
                                      '<a href="http://t.me/MAKS05">Садонцева Максима</a>.\n'
                                      'Этот бот является первым новостным ботом НИУ ВШЭ!\n'
                                      'Плагиат и копирование данного бота преследуются по закону!', True)

    if message.text == '\U0001F4DC Подписки' or message.text == '📜 Подписки':
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()

        if len(active_groups) != 0:
            grp = 'Ты уже подписан на следующие группы для получения новостей, как только они выходят:\n\n'
            for i in active_groups:
                grp += str(i[1]) + '\n'
            send_message(message.chat.id, grp, False)
        else:
            send_message(message.chat.id, 'Ты не подписан на группы для получения новостей, '
                                          'как только они выходят', False)

        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1 AND ug.gid NOT LIKE 'rss%'",
                   (message.chat.id,))
        active_groups = db.fetchall()

        if len(active_groups) != 0:
            grp = 'Список групп для \U0001F306 Вечерней Вышки:\n\n'
            for i in active_groups:
                grp += str(i[1]) + '\n'
            send_message(message.chat.id, grp, False)
        else:
            send_message(message.chat.id, '\U0001F306 Вечерняя Вышка не настроена', False)

        database.close()

    if message.text == '\U0001F4AC Оставить пожелания':
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        db.execute("UPDATE Users SET bcond = 5 WHERE id = ?", (message.chat.id,))
        database.commit()
        send_message(message.chat.id, 'Как ты думаешь, чего не хвататет этому боту? \n'
                                      'Напиши и отправь отзыв, как в обычный чат \U0001F609', markup_none)
        return

    if 1 == 1 and str(message.chat.id) in admin: #checking for learning responses
        database = sqlite3.connect(dbpath)
        db = database.cursor()
        db.execute("SELECT id, title FROM Categories ORDER BY id")
        categories = db.fetchall()
        for anlz in categories:
            if message.text == anlz[1]:
                db.execute("SELECT Cat, SentTo, id FROM ToCat WHERE SentTo = ? AND Cat = 0 ORDER BY id LIMIT 1", (message.chat.id,))
                lrng = db.fetchall()
                db.execute("UPDATE ToCat SET Cat = ? WHERE id = ?", (anlz[0], lrng[0][2],))
                database.commit()
                db.close()
                learning(message)

    else:
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()

        if bot_condition[0][0] == 5:
            if message.text is not '\U0001F51D Назад в главное меню':
                db.execute("INSERT INTO Reviews (uid, rev_text, rev_date) VALUES (?, ?, datetime('now', 'localtime'))",
                           (message.chat.id, message.text))
                db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
                database.commit()
                markup = press_done(message)
                send_message(message.chat.id, 'Спасибо за отзыв! '
                                              'Твое мнение очень важно для нас! \U0001F64F', markup)
            else:
                db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
                database.commit()
                markup = press_done(message)
                send_message(message.chat.id, 'Добро пожаловать в главное меню!', markup)

        if str(message.chat.id) in admin and bot_condition[0][0] == 666:
            db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
            database.commit()
            db.execute("SELECT id FROM Users")
            users = db.fetchall()
            usr_cnt = 0
            for i in users:
                usr_cnt += 1
                if usr_cnt > 30:
                    time.sleep(1)
                    usr_cnt = 0
                send_message(i[0], message.text, False)

        if str(message.chat.id) in admin and bot_condition[0][0] == 777:
            db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
            database.commit()

            try:
                # print(message.text.split('/')[3])
                group = vk_api.groups.getById(group_id=message.text.split('/')[3])
                # print(group[0]['name'])
                db.execute("INSERT INTO Groups (id, name, g_link) VALUES (?, ?, ?)",
                           (group[0]['id'], group[0]['name'], message.text))
                database.commit()
                send_message(message.chat.id, 'Группа "' + group[0]['name'] + '" добавлена в БД.', False)

            except:
                send_message(message.chat.id, 'Что-то пошло не так. Группа не была добавлена.', False)
                with open("logs.log", "a") as file:
                    file.write("\r\n\r\n" + time.strftime(
                        "%c") + "\r\n<<ERROR adding group>>\r\n" +
                               "\r\nGroup: " + message.text +
                               "\r\n" + traceback.format_exc() + "\r\n<<ERROR adding group>>")

        database.close()


def send_message(usr, msg, param):
    try:
        if type(param) is bool:
            if param:
                bot.send_message(usr, msg, disable_web_page_preview=True, parse_mode='HTML')
            else:
                bot.send_message(usr, msg, parse_mode='HTML')
        if type(param) is types.ReplyKeyboardMarkup:
            bot.send_message(usr, msg, reply_markup=param, parse_mode='HTML')
        if type(param) is types.ReplyKeyboardRemove:
            bot.send_message(usr, msg, reply_markup=param, parse_mode='HTML')

    except telebot.apihelper.ApiException:
        if traceback.format_exc().splitlines()[-1].split('"')[4].split(':')[1].split(',')[0] != '403':
            with open("logs.log", "a") as file:
                file.write("\r\n\r\n" + time.strftime(
                    "%c") + "\r\n<<ERROR sending message>>\r\n" + "\r\nUser: " + usr +
                           "\r\nUndelivered message: " + msg +
                           "\r\n" + traceback.format_exc() + "\r\n<<ERROR sending message>>")


def learning(message):
    if str(message.chat.id) in admin:
        database = sqlite3.connect(dbpath)
        dbl = database.cursor()
        dbl.execute("SELECT Post, SentTo, id FROM ToCat WHERE Cat = 0 "
                    "AND (SentTo IS NULL OR SentTo = ?) ORDER BY id LIMIT 1", (message.chat.id,))

        # dbc = database.cursor()
        # dbc.execute("SELECT name FROM Categories")

        lrng = dbl.fetchall()
        send_message(message.chat.id, 'Поучимся немножко', markup_none)
        markup = types.ReplyKeyboardMarkup()
        dbl.execute("SELECT id, title FROM Categories ORDER BY id")
        ctgs = dbl.fetchall()
        #for anlz in categories:
        markup.row(ctgs[1][1], ctgs[2][1])
        markup.row(ctgs[3][1], ctgs[4][1])
        markup.row(ctgs[5][1], ctgs[6][1])
        markup.row(ctgs[7][1], ctgs[8][1])
        markup.row(ctgs[0][1], '\U0001F51D Назад в главное меню')
        # markup.row('Образование','Мероприятия')
        # markup.row('Предпринимательство', 'Политика')
        # markup.row('Наука', 'Культура')
        # markup.row('Спорт', '\U0001F51D Главное меню')
        send_message(message.chat.id, lrng[0][0], markup)
        dbl.execute("UPDATE ToCat SET SentTo = ? WHERE id = ?",
                    (message.chat.id, lrng[0][2]))
        database.commit()
        dbl.close()
        # send_message(message.chat.id, l[0], markup)
    else:
        send_message(message.chat.id, 'Просим прощения, вам эта функция в данный момент недоступна \U0001F623',
                     markup_none)
        main_menu(message)


def get_rss_post():
    database = sqlite3.connect(dbpath)
    db = database.cursor()

    for i in rss_groups_list():
        try:
            db.execute("SELECT MAX(rss_date) FROM RSS WHERE rss_id = ?", (str(i[0]),))
            last_post = db.fetchall()
            db.execute("SELECT u.id FROM Users as u, UsersGroups as ug "
                       "WHERE u.id = ug.uid AND ug.upget = 1 AND ug.gid = ?", (str(i[0]),))
            sub_users = db.fetchall()
            rss = feedparser.parse(i[2])
            entr = rss['entries']
            # print("Parsing RSS:")
            # print(rss)
            if rss['feed']:
                for g in entr:
                    t = g['published'].split(' ')
                    if t[2] in Month:
                        t[2] = Month[t[2]]
                    rssdate = t[1:4]
                    for t in t[4].split(':'):
                        rssdate.append(t)
                    rssdate = '/'.join(rssdate)
                    utime = datetime.datetime.strptime(rssdate, "%d/%m/%Y/%H/%M/%S").strftime("%s")
                    if last_post[0][0]:
                        if int(utime) > int(last_post[0][0]):
                            link = '<b>' + str(i[1]) + '</b>\n\n' + str(g['title']) + \
                                   '\n\n<a href="' + str(g['links'][0]['href'] + '">Читать далее</a>')
                            # print(link)

                            for u in sub_users:
                                send_message(u[0], link, False)
                    else:
                        link = '<b>' + str(i[1]) + '</b>\n\n' + str(g['title']) + '\n\n<a href="' + \
                               str(g['links'][0]['href'] + '">Читать далее</a>')
                        # print(link)
                        usr_cnt = 0
                        for u in sub_users:
                            usr_cnt += 1
                            if usr_cnt > 30:
                                time.sleep(1)
                                usr_cnt = 0
                            send_message(u[0], link, False)
            else:
                with open("logs.log", "a") as file:
                    file.write("\r\n\r\n" + time.strftime(
                        "%c") + "\r\n<<ERROR RSS parse>>\r\n" +
                               "\r\n" + str(rss) + "\r\n<<ERROR RSS parse>>")
                    # print("ERROR RSS parse")
                    # print(rss)
        except:
            with open("logs.log", "a") as file:
                file.write("\r\n\r\n" + time.strftime(
                    "%c") + "\r\n<<ERROR RSS parse>>\r\n" +
                           "\r\n" + traceback.format_exc() + "\r\n<<ERROR RSS parse>>")
                # print("ERROR RSS parse")
    try:
        db.execute("DELETE FROM RSS")
        for i in rss_groups_list():
            rss = feedparser.parse(i[2])
            entr = rss['entries']
            if rss['feed']:
                for g in entr:
                    t = g['published'].split(' ')
                    if t[2] in Month:
                        t[2] = Month[t[2]]
                    rssdate = t[1:4]
                    for t in t[4].split(':'):
                        rssdate.append(t)
                    rssdate = '/'.join(rssdate)
                    utime = datetime.datetime.strptime(rssdate, "%d/%m/%Y/%H/%M/%S").strftime("%s")
                    db.execute("INSERT INTO RSS (rss_id, rss_date, rss_link, rss_title) VALUES (?, ?, ?, ?)",
                               (str(i[0]), str(utime), str(g['links'][0]['href']), g['title']))
        database.commit()
    except:
        with open("logs.log", "a") as file:
            file.write("\r\n\r\n" + time.strftime(
                "%c") + "\r\n<<ERROR RSS parse>>\r\n" +
                       "\r\n" + traceback.format_exc() + "\r\n<<ERROR RSS parse>>")
            # print("ERROR RSS table update")
    database.close()
    t = threading.Timer(rss_timer, get_rss_post)
    t.start()


def get_vk_post():
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    for i in vk_groups_list():
        db.execute("SELECT MAX(p_date) FROM Posts WHERE gid = ?", (str(i[0]),))
        last_post = db.fetchall()

        db.execute("SELECT u.id FROM Users as u, UsersGroups as ug "
                   "WHERE u.id = ug.uid AND ug.upget = 1 AND ug.gid = ?", (str(i[0]),))
        sub_users = db.fetchall()
        if last_post[0][0]:
            # print('Fetching posts from group ' + i[0])
            try:
                posts = vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
                for p in posts['items']:
                    if type(p) != int:
                        if 'id' in p:
                            if p['date'] > int(last_post[0][0]):
                                if p['text']:
                                    db.execute("SELECT id, title FROM Categories")
                                    categories = db.fetchall()
                                    text = re.sub(r'\[.*?\|(.*?)\]', r'\1', p['text'])
                                    category = categorizator.categorization(text, categories[0])
                                    cat_name = 'Образование'
                                    for c in categories:
                                        if c[0] == category:
                                            cat_name = c[1]
                                    usr_cnt = 0
                                    for u in sub_users:
                                        usr_cnt += 1
                                        if usr_cnt > 30:
                                            time.sleep(1)
                                            usr_cnt = 0
                                        if str(u[0]) in admin:
                                            link = '<b>' + str(i[1]) + '</b>\n\n' + str(
                                                p['text'].splitlines()[0].split('. ')[0]) + \
                                                   '\n\nКатегория: ' + cat_name + '\n\n<a href="https://vk.com/wall-' + str(
                                                i[0]) + '_' + str(p['id']) \
                                                   + '">Читать далее</a>'
                                        else:
                                            link = '<b>' + str(i[1]) + '</b>\n\n' + str(
                                                p['text'].splitlines()[0].split('. ')[0]) + \
                                                   '\n\n<a href="https://vk.com/wall-' + str(
                                                i[0]) + '_' + str(p['id']) \
                                                   + '">Читать далее</a>'
                                        link = (re.sub(r'\[.*?\|(.*?)\]', r'\1', link))
                                        send_message(u[0], link, False)

                                    db.execute("INSERT INTO Posts (id, gid, p_date, p_text, p_likes, p_reposts, cat) "
                                               "VALUES (?, ?, ?, ?, ?, ?, ?)",
                                               (str(i[0]) + '_' + str(p['id']), str(i[0]), str(p['date']),
                                                p['text'].splitlines()[0].split('.')[0], p['likes']['count'],
                                                p['reposts']['count'], category))
                                else:
                                    link = '<b>' + str(i[1]) + '</b>\n\n<i>Новость не содержит текст</i>\n\n' \
                                                               '<a href="https://vk.com/wall-' + str(i[0]) + \
                                           '_' + str(p['id']) + '">Читать далее</a>'
                                    usr_cnt = 0
                                    for u in sub_users:
                                        usr_cnt += 1
                                        if usr_cnt > 30:
                                            time.sleep(1)
                                            usr_cnt = 0
                                        link = (re.sub(r'\[.*?\|(.*?)\]', r'\1', link))
                                        send_message(u[0], link, False)

                                    db.execute("INSERT INTO Posts (id, gid, p_date, p_text, p_likes, p_reposts) "
                                               "VALUES (?, ?, ?, ' ', ?, ?)",
                                               (str(i[0]) + '_' + str(p['id']), str(i[0]), str(p['date']),
                                                p['likes']['count'], p['reposts']['count']))
                                    # print('Fetching successful')
            except Exception as e:
                with open("logs.log", "a") as file:
                    file.write("\r\n\r\n" + time.strftime(
                        "%c") + "\r\n<<ERROR fetching post>>\r\n" +
                               "\r\nGroup: " + i[0] +
                               "\r\n" + traceback.format_exc() + "\r\n<<ERROR fetching post>>")
                    # print(e)
                    # print('Unsuccessful fetch for group '+i[0])
        else:
            # print('Fetching posts from group ' + i[0])
            try:
                posts = vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
                for p in posts['items']:
                    if type(p) != int:
                        if 'id' in p:
                            if p['text']:
                                db.execute("INSERT INTO Posts (id, gid, p_date, p_text, p_likes, p_reposts) "
                                           "VALUES (?, ?, ?, ?, ?, ?)",
                                           (str(i[0]) + '_' + str(p['id']), str(i[0]), str(p['date']),
                                            p['text'].splitlines()[0].split('.')[0], p['likes']['count'],
                                            p['reposts']['count']))
                            else:
                                db.execute("INSERT INTO Posts (id, gid, p_date, p_text, p_likes, p_reposts) "
                                           "VALUES (?, ?, ?, ' ', ?, ?)",
                                           (str(i[0]) + '_' + str(p['id']), str(i[0]), str(p['date']),
                                            p['likes']['count'], p['reposts']['count']))
                                # print('Fetching successful')
            except Exception as e:
                with open("logs.log", "a") as file:
                    file.write("\r\n\r\n" + time.strftime(
                        "%c") + "\r\n<<ERROR fetching post>>\r\n" +
                               "\r\nGroup: " + i[0] +
                               "\r\n" + traceback.format_exc() + "\r\n<<ERROR fetching post>>")
                    # print(e)
                    # print('Unsuccessful fetch for group ' + i[0])

    database.commit()
    database.close()
    t = threading.Timer(vk_timer, get_vk_post)
    t.start()


def evening_hse():
    # print(datetime.time(15, 10))
    # print(datetime.datetime.now().time())
    if datetime.time(start_h, start_m) <= datetime.datetime.now().time() <= datetime.time(end_h, end_m):
        database = sqlite3.connect(dbpath)
        db = database.cursor()

        curr_time = int(time.time()) - 172800

        for i in vk_groups_list():
            db.execute("SELECT COUNT(id) FROM Posts WHERE gid = ?", (str(i[0]),))
            posts_count = db.fetchall()
            try:
                posts = vk_api.wall.get(owner_id='-' + i[0], count=posts_count[0][0], filter='owner')
                for p in posts['items']:
                    if type(p) != int:
                        if 'id' in p:
                            if p['date'] > (int(time.time()) - 93600):
                                db.execute("UPDATE Posts SET p_likes = ?, p_reposts = ? WHERE id = ?",
                                           (p['likes']['count'], p['reposts']['count'], str(i[0]) + '_'
                                            + str(p['id']),))
                                database.commit()
            except Exception as e:
                with open("logs.log", "a") as file:
                    file.write("\r\n\r\n" + time.strftime(
                        "%c") + "\r\n<<ERROR fetching post>>\r\n" +
                               "\r\nGroup: " + i[0] +
                               "\r\n" + traceback.format_exc() + "\r\n<<ERROR fetching post>>")
                    # print(e)
                    # print('Unsuccessful fetch for group ' + i[0])

            db.execute("SELECT COUNT(id) FROM Posts WHERE gid = ?", (i[0],))
            entr_numb = db.fetchall()
            if entr_numb[0][0] > 6:
                db.execute("DELETE FROM Posts WHERE gid = ? AND p_date <= ?", (i[0], str(curr_time),))
                database.commit()

        db.execute("SELECT uid FROM UsersGroups WHERE fetget = 1 GROUP BY uid")
        sub_users = db.fetchall()

        popular_post = []
        # print(sub_users)
        usr_cnt = 0
        for u in sub_users:
            # print(u[0])
            link = user_name(u[0])
            link += ',\n\n\U0001F306 Вечерняя Вышка специально для вас: \n\n'
            db.execute("SELECT gid FROM UsersGroups WHERE fetget = 1 AND uid = ?", (u[0],))
            usr_grps = db.fetchall()
            for g in usr_grps:
                db.execute("SELECT id, p_text, (p_likes + p_reposts*10) AS pop FROM Posts WHERE gid = ? AND p_date > ? "
                           "ORDER BY pop DESC ", (g[0], (int(time.time()) - 93600),))
                g_posts = db.fetchall()
                for gp in g_posts:
                    # print(gp)
                    if gp[1] == '':
                        gp = list(gp)
                        gp[1] = '<i>Новость не содержит текст</i>'
                        gp = tuple(gp)
                    popular_post.append(gp)
            pp = sorted(popular_post, key=lambda tup: tup[2], reverse=True)
            popular_post = []

            usr_cnt += 1
            if usr_cnt > 30:
                time.sleep(1)
                usr_cnt = 0
            if pp:
                if len(pp) >= 5:
                    for j in range(5):
                        link += pp[j][1] + '\n<a href="https://vk.com/wall-' + str(pp[j][0]) + \
                                '">Читать далее</a>\n\n'
                else:
                    for j in range(len(pp)):
                        link += pp[j][1] + '\n<a href="https://vk.com/wall-' + str(pp[j][0]) + \
                                '">Читать далее</a>\n\n'
                link += 'Спасибо, что читаете нас \U0001F60A\n\nЕсли вам нравится этот бот, поделитесь им с друзьми:' \
                        '\nhttp://t.me/hse_news_bot'

                link = (re.sub(r'\[.*?\|(.*?)\]', r'\1', link))
                send_message(u[0], link, True)
            else:
                send_message(u[0], '\U0001F306 Вечерняя Вышка:\n\nК сожалению, сегодня не было новостей \U0001F614',
                             False)

        database.close()
    t = threading.Timer(vk_timer, evening_hse)
    t.start()


def groups_as_buttons_sub(groups, active_groups, markup):
    check_if_all = 0
    for i in groups:
        if i not in active_groups:
            markup.row(i[1])
            check_if_all += 1
    return check_if_all


def groups_as_buttons_unsub(groups, active_groups, markup):
    check_if_all = 0
    for i in groups:
        if i in active_groups:
            markup.row(i[1])
            check_if_all += 1
    return check_if_all


def press_next(message):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
    bot_condition = db.fetchall()

    if bot_condition[0][0] == 1234:
        db.execute("UPDATE Users SET bcond = 4 WHERE id = ?", (message.chat.id,))
        database.commit()
        db.execute("SELECT g.id, g.name, g.g_link FROM Groups AS g, UsersGroups AS ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()
        markup = types.ReplyKeyboardMarkup()
        markup.row('\U0001F3C1 Завершить')
        markup.row('Выбрать все')
        check_if_all = groups_as_buttons_sub(vk_groups_list(), active_groups, markup)
        if check_if_all > 0:
            send_message(message.chat.id, 'Ты хочешь подписаться на \U0001F306 Вечернюю Вышку? \n\n'
                                          'Вечернаяя Вышка - это 5 самых популярных материалов за день. '
                                          'Она будет прихожить в 9 вечера.\nВыбери группы для Вечерней Вышки, '
                                          'а затем нажми "\U0001F3C1 Завершить"', markup)
            if len(active_groups) != 0:
                send_message(message.chat.id, 'Ты уже подписан на следующие группы:', False)
                for i in active_groups:
                    send_message(message.chat.id, i[1], False)
        else:
            send_message(message.chat.id, 'Ты уже подписан на все группы для \U0001F306 Вечерней Вышки', False)
            markup = press_done(message)
            send_message(message.chat.id, 'Настройка завершена', markup)

    database.close()


def press_done(message):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
    database.commit()
    markup = types.ReplyKeyboardMarkup()
    # markup.row('5 последних постов')
    # markup.row('5 последних постов из RSS')
    markup.row('\U0001F4DC Подписки', '\U0001F527 Настройки')
    # markup2.row('\U0001F527 Настройки')
    markup.row('\U00002139 О проекте')
    markup.row('\U0001F4AC Оставить пожелания')
    database.close()

    return markup


def group_selection(msg, grp_id, bot_condition):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT * FROM UsersGroups WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
    check_group = db.fetchall()
    # print(bot_condition[0][0])

    if bot_condition[0][0] == 1:
        # print(check_group)
        if check_group:
            if check_group[0][2] == 1:
                db.execute("UPDATE UsersGroups SET upget = 0 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                send_message(msg.chat.id, 'Ты отписался от группы "' + msg.text + '"', False)
            else:
                send_message(msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"', False)
        else:
            send_message(msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"', False)

    if bot_condition[0][0] == 2 or bot_condition[0][0] == 1234:
        # print(check_group)
        if not check_group:
            # print(msg.chat.id)
            db.execute("INSERT INTO UsersGroups (uid, gid, upget) VALUES (?, ?, 1)", (msg.chat.id, grp_id,))
            send_message(msg.chat.id, 'Ты подписался на группу "' + msg.text + '"', False)
        else:
            if check_group[0][2] == 0:
                db.execute("UPDATE UsersGroups SET upget = 1 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                send_message(msg.chat.id, 'Ты подписался на группу "' + msg.text + '"', False)
            else:
                send_message(msg.chat.id, 'Группа "' + msg.text + '" уже была выбрана', False)

    if bot_condition[0][0] == 3:
        # print(check_group)
        if check_group:
            if check_group[0][3] == 1:
                db.execute("UPDATE UsersGroups SET fetget = 0 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                send_message(msg.chat.id, 'Ты отписался от группы "' + msg.text + '"', False)
            else:
                send_message(msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"', False)
        else:
            send_message(msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"', False)

    if bot_condition[0][0] == 4:
        # print(check_group)
        if not check_group:
            # print(msg.chat.id)
            db.execute("INSERT INTO UsersGroups (uid, gid, fetget) VALUES (?, ?, 1)", (msg.chat.id, grp_id,))
            send_message(msg.chat.id, 'Ты подписался на группу "' + msg.text + '"', False)
        else:
            # print(check_group[0][3])
            if check_group[0][3] == 0:
                db.execute("UPDATE UsersGroups SET fetget = 1 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                send_message(msg.chat.id, 'Ты подписался на группу "' + msg.text + '"', False)
            else:
                send_message(msg.chat.id, 'Группа "' + msg.text + '" уже была выбрана', False)

    database.commit()
    database.close()


def groups_list():
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT * FROM Groups")
    groups = db.fetchall()
    database.close()
    return groups


def vk_groups_list():
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT * FROM Groups WHERE id NOT LIKE 'rss%'")
    groups = db.fetchall()
    database.close()
    return groups


def rss_groups_list():
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT * FROM Groups WHERE id LIKE 'rss%'")
    groups = db.fetchall()
    database.close()
    return groups


def user_name(usr_id):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    # print(id)
    db.execute("SELECT username, first_name FROM Users WHERE id = ?", (usr_id,))
    user = db.fetchall()
    database.close()
    # print(user)
    print(user[0])
    if user[0][1]:
        name = user[0][1]
    elif user[0][0]:
        name = user[0][0]
    else:
        name = 'Друг'
    return name


def administrator(message):
    #print(message.sticker)
    if str(message.chat.id) in admin:
        if message.sticker.file_id == broadcast:
            database = sqlite3.connect(dbpath)
            db = database.cursor()
            db.execute("UPDATE Users SET bcond = 666 WHERE id = ?", (message.chat.id,))
            database.commit()
            database.close()

        if message.sticker.file_id == new_group:
            database = sqlite3.connect(dbpath)
            db = database.cursor()
            db.execute("UPDATE Users SET bcond = 777 WHERE id = ?", (message.chat.id,))
            database.commit()
            database.close()

        if message.sticker.file_id == cancel:
            database = sqlite3.connect(dbpath)
            db = database.cursor()
            db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
            database.commit()
            database.close()
            markup = press_done(message)
            send_message(message.chat.id, 'Отмена произведена', markup)

        if message.sticker.file_id == number_of_users:
            database = sqlite3.connect(dbpath)
            db = database.cursor()
            db.execute("SELECT  COUNT(*) FROM Users")
            nmb_of_usr = db.fetchall()
            send_message(message.chat.id, 'Количество пользователей: ' + str(nmb_of_usr[0][0]), False)
            database.close()


def location(message):
    database = sqlite3.connect(dbpath)
    db = database.cursor()

    db.execute("SELECT * FROM Buildings")
    buildings = db.fetchall()

    def distance(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km

    clstadr = 1000000
    for _i in range(0, len(buildings)):
        dist = distance(message.location.longitude, message.location.latitude, buildings[_i][2], buildings[_i][3])
        if clstadr > dist:
            clstadr = dist
            adrid = buildings[_i][0]

    db.execute("SELECT * FROM Buildings WHERE id = ?", (adrid,))
    clstbld = db.fetchall()

    send_message(message.chat.id, 'Ближайшее здание Вышки располагается по адресу:\n' + clstbld[0][1], False)
    bot.send_location(message.chat.id, clstbld[0][3], clstbld[0][2])
    database.close()


def fetch_all_vk_posts():
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT id, name, g_link FROM Groups")
    groups = db.fetchall()
    for g in groups:
        posts = vk_api.wall.get(owner_id='-' + g[0], count=100, filter='owner', offset = 1900)
        for p in posts['items']:
            if type(p) != int:
                if 'id' in p:
                    if p['text']:
                        text = re.sub(r'\w+:\/{2}[\d\w-]+(\.[\d\w-]+)*(?:(?:\/[^\s/]*))*', '',
                                      re.sub(r'\[.*?\|(.*?)\]', r'\1', p['text']), flags=re.MULTILINE)
                        print('____________________________________________________________________________________')
                        print(text)
                        print(type(p['text']))
                        print(categorizator.translator(text))
                        db.execute("INSERT INTO ToCat (Post) VALUES "
                                   "(?)",
                                   [text])

                        database.commit()
    db.close()


def text_to_folders():
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT ts.id, ts.Post, c.path FROM ToCat as ts LEFT JOIN Categories as c ON c.id = ts.Cat")
    ftch = db.fetchall()
    for p in ftch:
        path = 'train_set/'+str(p[2])+'/'+str(p[0])
        with open(path, 'w') as f:
            #file = fi '\n' + p[1]
            f.write(p[1])
