import sqlite3
import time
import traceback
from telebot import types
import bot_modules

dbpath = bot_modules.dbpath
bot = bot_modules.bot

nextb = bot_modules.nextb

# botCondition 0 - простой, 1 - отказ для подписки,
# 2 - выбор для подписки, 3 - отказ для последних, 4 - выбор для последних

databasem = sqlite3.connect(dbpath)
dbm = databasem.cursor()
dbm.execute("SELECT id FROM Users")
users = dbm.fetchall()
for i in users:
    try:
        u = bot.get_chat(i[0]).username
        f = bot.get_chat(i[0]).first_name
        l = bot.get_chat(i[0]).last_name
        dbm.execute("UPDATE Users SET username = ?, first_name = ?, last_name = ? WHERE id = ?", (u, f, l, i[0],))
    except Exception as e:
        print(e)
databasem.commit()
databasem.close()


markup_none = types.ReplyKeyboardRemove()

# bot_modules.get_rss_post()

bot_modules.get_vk_post()

bot_modules.evening_hse()


@bot.message_handler(commands=['start'])
def send_welcome(message):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    markup = types.ReplyKeyboardMarkup()
    markup.row('\U00002705 Выбрать группы для подписки')
    db.execute("SELECT id FROM Users WHERE id = ?", (message.chat.id,))
    check_user = db.fetchall()

    if not check_user:
        db.execute("INSERT INTO Users (id, reg_date, bcond, username, first_name, last_name) VALUES "
                   "(?, datetime('now', 'localtime'), 0, ?, ?, ?)",
                   (message.chat.id, message.chat.username, message.chat.first_name, message.chat.last_name,))
        database.commit()
        database.close()
        # print(bot.get_chat(message.chat.id))
        bot_modules.send_message(message.chat.id, 'Привет, ' + bot_modules.user_name(message.chat.id) +
                                 '! Я бот, который поможет тебе следить за всеми новостями твоего любимого ВУЗа! \n'
                                 'Я могу присылать тебе новости из разных групп ВК, связанных с Вышкой.\n'
                                 'А еще у меня есть вечерняя рассылка популярных новостей \U0001F306', markup)
    else:
        markup.row('\U0001F6AB Выбрать группы для отписки')
        markup.row('\U0001F51D Главное меню')
        bot_modules.send_message(message.chat.id, 'Добро пожаловать. Снова.\U000026A1', markup)


@bot.message_handler(commands=['stop'])
def send_goodbye(message):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT id FROM Users WHERE id = ?", (message.chat.id,))
    check_user = db.fetchall()

    if check_user:
        db.execute("UPDATE UsersGroups SET upget = 0, fetget = 0 WHERE uid = ?", (message.chat.id,))
        database.commit()
        bot_modules.send_message(message.chat.id, 'Очень жаль, что ты решил отписаться от всего \U0001F614\n'
                                          'Но я всегда буду рад, если ты снова решишь подписаться!\n'
                                          'Нужно просто нажать /start \U0001F609', markup_none)
    else:
        bot_modules.send_message(message.chat.id, 'Мне кажется или ты еще не начинал пользоваться ботом?\n'
                                          'Чтобы начать им пользоваться нажми /start \U0001F60E', markup_none)


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
        check_if_all = bot_modules.groups_as_buttons_unsub(bot_modules.groups_list(), active_groups, markup)
        if check_if_all > 0:
            bot_modules.send_message(message.chat.id, 'Выбери группы, откуда ты НЕ хочешь получать новости, '
                                                           'как только они выходят, а затем нажми "Далее"', markup)
        else:
            bot_modules.send_message(message.chat.id, 'Ты не подписан ни на одну группу для получения новостей, '
                                                           'как только они выходят', False)
            bot_modules.press_next(message, bot_modules.groups_list())

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
        check_if_all = bot_modules.groups_as_buttons_sub(bot_modules.groups_list(), active_groups, markup)
        if check_if_all > 0:
            if len(active_groups) != 0:
                bot_modules.send_message(message.chat.id, 'Ты уже подписан на следующие группы:', False)
                for i in active_groups:
                    bot_modules.send_message(message.chat.id, i[1], False)
            bot_modules.send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости, '
                                                           'как только они выходят, а затем нажми "Далее"', markup)
        else:
            bot_modules.send_message(message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                                           'как только они выходят', False)
            bot_modules.press_next(message, bot_modules.groups_list())

    for j in bot_modules.groups_list():
        if message.text == str(j[1]):
            db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
            bot_condition = db.fetchall()
            bot_modules.group_selection(message, str(j[0]), bot_condition)
            markup = types.ReplyKeyboardMarkup()
            if bot_condition[0][0] == 1:
                markup.row('\U000027A1 Далее')
                markup.row('Отписаться от всех')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_unsub(bot_modules.groups_list(), active_groups, markup)
                if check_if_all == 0:
                    bot_modules.send_message(message.chat.id, 'Ты не подписан ни на одну группу для получения '
                                                                   'новостей, как только они выходят', False)
                    bot_modules.press_next(message, bot_modules.groups_list())
                else:
                    bot_modules.send_message(message.chat.id, 'Выбери группы или нажми "Далее"', markup)
            if bot_condition[0][0] == 2:
                markup.row('\U000027A1 Далее')
                markup.row('Выбрать все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_sub(bot_modules.groups_list(), active_groups, markup)
                if check_if_all == 0:
                    bot_modules.send_message(message.chat.id, 'Ты подписан на все группы для получения новостей, '
                                                                   'как только они выходят', False)
                    bot_modules.press_next(message, bot_modules.groups_list())
                else:
                    bot_modules.send_message(message.chat.id, 'Выбери группы или нажми "Далее"', markup)
            if bot_condition[0][0] == 3:
                markup.row('\U0001F3C1 Завершить')
                markup.row('Отписаться от всех')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_unsub(bot_modules.vk_groups_list(), active_groups, markup)
                if check_if_all == 0:
                    bot_modules.send_message(message.chat.id, 'Ты НЕ подписан на \U0001F306 Вечернюю Вышку',
                                             markup)
                    markup = bot_modules.press_done(message)
                    bot_modules.send_message(message.chat.id, 'Настройка завершена', markup)
                else:
                    bot_modules.send_message(message.chat.id, 'Выбери группы или нажми "Завершить"', markup)
            if bot_condition[0][0] == 4:

                markup.row('\U0001F3C1 Завершить')
                markup.row('Выбрать все')
                db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                           "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                           (message.chat.id,))
                active_groups = db.fetchall()
                check_if_all = bot_modules.groups_as_buttons_sub(bot_modules.vk_groups_list(), active_groups, markup)
                if check_if_all == 0:
                    bot_modules.send_message(message.chat.id, 'Ты подписан на все группы для получения новостей '
                                                                   'в \U0001F306 Вечерней Вышке', False)
                    markup = bot_modules.press_done(message)
                    bot_modules.send_message(message.chat.id, 'Настройка завершена', markup)
                else:
                    bot_modules.send_message(message.chat.id, 'Выбери группы или нажми "Завершить"', markup)

    if message.text == 'Отписаться от всех':
        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()
        if bot_condition[0][0] == 1:
            db.execute("UPDATE UsersGroups SET upget = 0 WHERE uid = ?", (message.chat.id,))
            database.commit()
            bot_modules.send_message(message.chat.id, 'Ты отписался от всех групп, из которых получал новости, '
                                                           'как только они выходили', False)
            bot_modules.press_next(message, bot_modules.vk_groups_list())
        if bot_condition[0][0] == 3:
            db.execute("UPDATE UsersGroups SET fetget = 0 WHERE uid = ?", (message.chat.id,))
            database.commit()
            bot_modules.send_message(message.chat.id, 'Ты отписался от всех групп для \U0001F306 Вечерней Вышки',
                                     False)
            markup = bot_modules.press_done(message)
            bot_modules.send_message(message.chat.id, 'Настройка завершена', markup)

    if message.text == 'Выбрать все':
        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()
        if bot_condition[0][0] == 2:
            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id", (message.chat.id,))
            uncreated = db.fetchall()
            db.execute("UPDATE UsersGroups SET upget = 1 WHERE uid = ?", (message.chat.id,))
            database.commit()
            for i in bot_modules.groups_list():
                if i not in uncreated:
                    db.execute("INSERT INTO UsersGroups (uid, gid, upget, fetget) VALUES (?, ?, 1, 0)",
                               (message.chat.id, i[0],))
                    database.commit()
            bot_modules.press_next(message, bot_modules.vk_groups_list())
        if bot_condition[0][0] == 4:
            db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                       "WHERE ug.uid = ? AND ug.gid = g.id", (message.chat.id,))
            uncreated = db.fetchall()
            db.execute("UPDATE UsersGroups SET fetget = 1 WHERE uid = ?", (message.chat.id,))
            database.commit()
            for i in bot_modules.groups_list():
                if i not in uncreated:
                    db.execute("INSERT INTO UsersGroups (uid, gid, upget, fetget) VALUES (?, ?, 0, 1)",
                               (message.chat.id, i[0],))
                    database.commit()
            markup = bot_modules.press_done(message)
            bot_modules.send_message(message.chat.id, 'Настройка завершена', markup)

    if message.text == '\U000027A1 Далее':
        bot_modules.press_next(message, bot_modules.groups_list())

    if message.text == '\U0001F3C1 Завершить':
        markup = bot_modules.press_done(message)
        bot_modules.send_message(message.chat.id, 'Настройка завершена', markup)

    # if message.text == '5 последних постов':
    #     vk_arr = bot_modules.five_last_posts(message)
    #     if vk_arr:
    #         for _i in vk_arr:
    #             bot_modules.send_message(bot, message.chat.id, _i, False)
    #     else:
    #         bot_modules.send_message(bot, message.chat.id, 'Ты не выбрал группы', False)
    #
    # if message.text == '5 последних постов из RSS':
    #     rss_arr = bot_modules.five_last_rss(message)
    #     if rss_arr:
    #         for _i in rss_arr:
    #             bot_modules.send_message(bot, message.chat.id, _i)
    #     else:
    #         bot_modules.send_message(bot, message.chat.id, 'Ты не выбрал RSS', False)

    if message.text == '\U0001f527 Настройки':
        markup = types.ReplyKeyboardMarkup()
        markup.row('\U00002705 Выбрать группы для подписки')
        markup.row('\U0001F6AB Выбрать группы для отписки')
        markup.row('\U0001F51D Главное меню')
        bot_modules.send_message(message.chat.id, 'Выбери, что ты хочешь сделать:', markup)

    if message.text == '\U0001F51D Главное меню':
        markup = bot_modules.press_done(message)
        bot_modules.send_message(message.chat.id, 'Добро пожаловать в главное меню!', markup)

    if message.text == '\U00002139 О проекте':
        bot_modules.send_message(message.chat.id, 'Этот бот является дипломной работой студентов 4 курса ДКИ МИЭМ '
                                                       'Барсукова Павла и Садонцева Максима.\n'
                                                       'Этот бот является первым новостным ботом НИУ ВШЭ!\n'
                                                       'Плагиат и копирование данного бота преследуются по закону!',
                                 False)

    if message.text == '\U0001F4DC Подписки':
        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.upget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()
        if len(active_groups) != 0:
            grp = 'Ты уже подписан на следующие группы для получения новостей, как только они выходят:\n\n'
            # bot_modules.send_message(bot, message.chat.id, 'Ты уже подписан на следующие группы для
            # получения новостей, как только они выходят:', False)
            for i in active_groups:
                grp += str(i[1]) + '\n'
            bot_modules.send_message(message.chat.id, grp, False)
        else:
            bot_modules.send_message(message.chat.id, 'Ты не подписан на группы для получения новостей, '
                                                           'как только они выходят', False)

        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()
        if len(active_groups) != 0:
            grp = 'Список групп для \U0001F306 Вечерней Вышки:\n\n'
            # bot_modules.send_message(bot, message.chat.id, 'Список групп для \U0001F306 Вечерней Вышки:', False)
            for i in active_groups:
                grp += str(i[1]) + '\n'
            bot_modules.send_message(message.chat.id, grp, False)
        else:
            bot_modules.send_message(message.chat.id, '\U0001F306 Вечерняя Вышка не настроена', False)

    if message.text == '\U0001F4AC Оставить пожелания':
        db.execute("UPDATE Users SET bcond = 5 WHERE id = ?", (message.chat.id,))
        database.commit()
        bot_modules.send_message(message.chat.id, 'Как ты думаешь, чего не хвататет этому боту? \n'
                                          'Напиши и отправь отзыв, как в обычный чат \U0001F609', markup_none)

    else:
        db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
        bot_condition = db.fetchall()
        if bot_condition[0][0] == 5:
            db.execute("INSERT INTO Reviews (uid, rev_text, rev_date) VALUES (?, ?, datetime('now', 'localtime'))",
                       (message.chat.id, message.text))
            db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
            database.commit()
            markup = bot_modules.press_done(message)
            bot_modules.send_message(message.chat.id, 'Спасибо за отзыв! '
                                                           'Твое мнение очень важно для нас! \U0001F64F', markup)


def telegram_polling():
    try:
        bot.polling(none_stop=True, timeout=60)  # constantly get messages from Telegram
    except:
        with open("logs.log", "a") as file:
            file.write("\r\n\r\n" + time.strftime("%c")+"\r\n<<ERROR polling>>\r\n"+ traceback.format_exc() +
                       "\r\n<<ERROR polling>>")
        print("ERROR polling")
        print(traceback.format_exc())
        bot.stop_polling()
        time.sleep(100)
        telegram_polling()

if __name__ == '__main__':
    telegram_polling()