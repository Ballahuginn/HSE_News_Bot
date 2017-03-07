import datetime
import sqlite3
import threading
import time
import feedparser
import traceback
import telebot
import re
from telebot import types
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

Month = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'June': '06',
         'July': '07', 'Aug': '08', 'Sept': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}

bot = telebot.TeleBot(config['TELEGRAM.API']['TOKEN'])
api_ver = config['VK.API']['ver']
timeout = int(config['VK.API']['timeout'])

dbpath=config['DEFAULT']['DB']

start_h = int(config['EVENING']['start_h'])
start_m = int(config['EVENING']['start_m'])
end_h = int(config['EVENING']['end_h'])
end_m = int(config['EVENING']['end_m'])


config.read('locale_ru.ini')
nextb = (config['COMMANDS']['NEXT'])

def send_message(bot, usr, msg, param):
    try:
        print(type(param))
        if param and (type(param) is bool):
            print(param)
            bot.send_message(usr, msg, disable_web_page_preview=True)
        if not (param) and (type(param) is bool):
            bot.send_message(usr, msg)
        if type(param) is types.ReplyKeyboardMarkup:
            bot.send_message(usr, msg, reply_markup=param)
    except telebot.apihelper.ApiException:
        with open("logs.log", "a") as file:
            file.write("\r\n\r\n" + time.strftime(
                "%c") + "\r\n<<ERROR sending message>>\r\n" + "\r\nUser: "+ usr +
                       "\r\nUndelivered message: "+ msg +
                       "\r\n" + traceback.format_exc() + "\r\n<<ERROR sending message>>")
        print('User blocked the Bot. User: ' + usr)
        print('Undelivered message: ' + msg)


def get_rss_post(bot):
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
            print("Parsing RSS:")
            print(entr)
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
                            link = str(i[1]) + '\n' + str(g['title']) + '\n' + str(g['links'][0]['href'])
                            print(link)
                            for u in sub_users:
                                send_message(bot, u[0], link, False)
                    else:
                        link = str(i[1]) + '\n' + str(g['title']) + '\n' + str(g['links'][0]['href'])
                        print(link)
                        for u in sub_users:
                            send_message(bot, u[0], link, False)
            else:
                with open("logs.log", "a") as file:
                    file.write("\r\n\r\n" + time.strftime(
                        "%c") + "\r\n<<ERROR RSS parse>>\r\n" +
                               "\r\n" + str(rss) + "\r\n<<ERROR RSS parse>>")
                print("ERROR RSS parse")
                print(rss)
        except:
            with open("logs.log", "a") as file:
                file.write("\r\n\r\n" + time.strftime(
                    "%c") + "\r\n<<ERROR RSS parse>>\r\n" +
                           "\r\n" + traceback.format_exc() + "\r\n<<ERROR RSS parse>>")
            print("ERROR RSS parse")
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
        print("ERROR RSS table update")
    database.close()
    t = threading.Timer(1800, get_rss_post, [bot])
    t.start()


# def post_texts(vk_post):
#     if 'text' in vk_post:
#         psttxt = []
#         mas = vk_post['text']
#         mas1 = mas.split(' ')
#         if len(mas1) < 5:
#             for r in mas1:
#                 psttxt.append(r)
#         else:
#             v = mas1[4]
#             if v[-1] == ',' or v[-1] == ':' or v[-1] == ';' or v[-1] == '-' or v[-1] == '—':
#                 psttxt.extend((mas1[0], ' ', mas1[1], ' ', mas1[2], ' ', mas1[3], ' ', v[:-1], '...'))
#             elif v[-1] == '!' or v[-1] == '?' or v[-1] == '.':
#                 psttxt.extend((mas1[0], ' ', mas1[1], ' ', mas1[2], ' ', mas1[3], ' ', mas1[4]))
#             else:
#                 psttxt.extend((mas1[0], ' ', mas1[1], ' ', mas1[2], ' ', mas1[3], ' ', mas1[4], '...'))
#     return ''.join(psttxt)


def get_vk_post(bot, vk_api):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    for i in vk_groups_list():
        db.execute("SELECT MAX(p_date) FROM Posts WHERE gid = ?", (str(i[0]),))
        last_post = db.fetchall()

        db.execute("SELECT u.id FROM Users as u, UsersGroups as ug "
                   "WHERE u.id = ug.uid AND ug.upget = 1 AND ug.gid = ?", (str(i[0]),))
        sub_users = db.fetchall()
        if last_post[0][0]:
            print('Fetching posts from group ' + i[0])
            try:
                posts = vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
                for p in posts['items']:
                    if type(p) != int:
                        if 'id' in p:
                            if p['date'] > int(last_post[0][0]):
                                link = str(i[1]) + '\n' + p['text'].splitlines()[0].split('.')[0] + '\nhttps://vk.com/wall-' + i[0] + '_' + str(p['id'])
                                for u in sub_users:
                                    link = (re.sub(r'\[.*?\|(.*?)\]', r'\1', link))
                                    send_message(bot, u[0], link, False)
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
                                                p['likes']['count'],
                                                p['reposts']['count']))
                print('Fetching successful')
            except Exception as e:
                with open("logs.log", "a") as file:
                    file.write("\r\n\r\n" + time.strftime(
                        "%c") + "\r\n<<ERROR fetching post>>\r\n" +
                               "\r\nGroup: " + i[0] +
                               "\r\n" + traceback.format_exc() + "\r\n<<ERROR fetching post>>")
                print(e)
                print('Unsuccessful fetch for group '+i[0])
        else:
            print('Fetching posts from group ' + i[0])
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
                                           (str(i[0]) + '_' + str(p['id']), str(i[0]), str(p['date']), p['likes']['count'],
                                            p['reposts']['count']))
                print('Fetching successful')
            except Exception as e:
                with open("logs.log", "a") as file:
                    file.write("\r\n\r\n" + time.strftime(
                        "%c") + "\r\n<<ERROR fetching post>>\r\n" +
                               "\r\nGroup: " + i[0] +
                               "\r\n" + traceback.format_exc() + "\r\n<<ERROR fetching post>>")
                print(e)
                print('Unsuccessful fetch for group ' + i[0])

    # db.execute("DELETE FROM Posts")

    # for i in vk_groups_list():
    #     # try:
    #     posts = vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
    #     # except requests.exceptions.ReadTimeout:
    #     #     print('VK Timed Out')
    #     for _k in posts['items']:
    #         if type(_k) != int:
    #             if 'id' in _k:
    #                 txt = post_texts(_k)
    #                 db.execute("INSERT INTO Posts (id, gid, p_date, p_text, p_likes, p_reposts) "
    #                            "VALUES (?, ?, ?, ?, ?, ?)",
    #                            (str(i[0]) + '_' + str(_k['id']), str(i[0]), str(_k['date']), str(txt),
    #                            _k['likes']['count'], _k['reposts']['count']))

    database.commit()
    database.close()
    t = threading.Timer(60, get_vk_post, [bot, vk_api])
    t.start()


def evening_hse(bot, vk_api):

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
                            if p['date'] > (int(time.time()) - 86400):
                                db.execute("UPDATE Posts SET p_likes = ?, p_reposts = ? WHERE id = ?",
                                           (p['likes']['count'], p['reposts']['count'], str(i[0]) + '_' + str(p['id']),))
            except Exception as e:
                with open("logs.log", "a") as file:
                    file.write("\r\n\r\n" + time.strftime(
                        "%c") + "\r\n<<ERROR fetching post>>\r\n" +
                               "\r\nGroup: " + i[0] +
                               "\r\n" + traceback.format_exc() + "\r\n<<ERROR fetching post>>")
                print(e)
                print('Unsuccessful fetch for group ' + i[0])
                
            db.execute("SELECT COUNT(id) FROM Posts WHERE gid = ?", (i[0],))
            entr_numb = db.fetchall()
            if entr_numb[0][0] > 6:
                db.execute("DELETE FROM Posts WHERE gid = ? AND p_date <= ?", (i[0], str(curr_time),))
                database.commit()

        db.execute("SELECT uid FROM UsersGroups WHERE fetget = 1 GROUP BY uid")
        sub_users = db.fetchall()

        popular_post = []
        for u in sub_users:
            link = user_name(u[0])
            link += ',\n\n\U0001F306 Вечерняя Вышка специально для вас: \n\n'
            db.execute("SELECT gid FROM UsersGroups WHERE fetget = 1 AND uid = ?", (u[0],))
            usr_grps = db.fetchall()
            for g in usr_grps:
                db.execute("SELECT id, p_text, (p_likes + p_reposts*10) as pop FROM Posts WHERE gid = ? AND p_date > ? "
                           "ORDER BY pop DESC ", (g[0], (int(time.time()) - 86400),))
                g_posts = db.fetchall()
                for gp in g_posts:
                    popular_post.append(gp)
            pp = sorted(popular_post, key=lambda tup: tup[2], reverse=True)
            popular_post = []

            if pp:
                if len(pp)>=5:
                    for j in range(5):
                        link += pp[j][1] + '\nhttps://vk.com/wall-' + str(pp[j][0]) + '\n\n'
                else:
                    for j in range(len(pp)):
                        link += pp[j][1] + '\nhttps://vk.com/wall-' + str(pp[j][0]) + '\n\n'
                link += 'Спасибо, что читаете нас \U0001F60A'

                link = (re.sub(r'\[.*?\|(.*?)\]', r'\1', link))
                send_message(bot, u[0], link, True)
            else:
                send_message(bot, u[0], "\U0001F306 Вечерняя Вышка:\n\nК сожалению, сегодня не было новостей \U0001F614", False)

        db.close()
    t = threading.Timer(60, evening_hse, [bot, vk_api])
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


def press_next(message, groups):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("SELECT bcond FROM Users WHERE id = ?", (message.chat.id,))
    bot_condition = db.fetchall()
    if bot_condition[0][0] == 1:
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
            send_message(bot, message.chat.id, 'Выбери группы, откуда ты НЕ хочешь получать новости в \U0001F306 Вечерней Вышке'
                                              ', а затем нажми "Завершить"', markup)
        else:
            send_message(bot, message.chat.id, 'Ты НЕ подписан на \U0001F306 Вечернюю Вышку', False)
            markup = press_done(message)
            send_message(bot, message.chat.id, 'Настройка завершена', markup)

    if bot_condition[0][0] == 2:
        db.execute("UPDATE Users SET bcond = 4 WHERE id = ?", (message.chat.id,))
        database.commit()
        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()
        markup = types.ReplyKeyboardMarkup()
        markup.row('\U0001F3C1 Завершить')
        markup.row('Выбрать все')
        check_if_all = groups_as_buttons_sub(vk_groups_list(), active_groups, markup)
        if check_if_all > 0:
            send_message(bot, message.chat.id, 'Ты хочешь подписаться на \U0001F306 Вечернюю Вышку? \n\n'
                                                'Вечернаяя Вышка - это 5 самых популярных материалов за день. '
                                                'Она будет прихожить в 9 вечера.\nВыбери группы для Вечерней Вышки'
                                                ', а затем нажми "\U0001F3C1 Завершить"', markup)
            if len(active_groups) != 0:
                send_message(bot, message.chat.id, 'Ты уже подписан на следующие группы:', False)
                for i in active_groups:
                    send_message(bot, message.chat.id, i[1], False)
        else:
            send_message(bot, message.chat.id, 'Ты уже подписан на все группы для \U0001F306 Вечерней Вышки', False)
            markup = press_done(message)
            send_message(bot, message.chat.id, 'Настройка завершена', markup)


def press_done(message):
    database = sqlite3.connect(dbpath)
    db = database.cursor()
    db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
    database.commit()
    markup2 = types.ReplyKeyboardMarkup()
    # markup2.row('5 последних постов')
    # markup2.row('5 последних постов из RSS')
    markup2.row('\U0001F4DC Подписки', '\U0001F527 Настройки')
    # markup2.row('\U0001F527 Настройки')
    markup2.row('\U00002139 О проекте')
    markup2.row('\U0001F4AC Оставить пожелания')
    db.close()

    return markup2


def group_selection(bot, msg, grp_id, bot_condition):
    dtbs = sqlite3.connect(dbpath)
    dtbs_c = dtbs.cursor()
    dtbs_c.execute("SELECT * FROM UsersGroups WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
    check_group = dtbs_c.fetchall()
    # print(bot_condition[0][0])

    if bot_condition[0][0] == 1:
        # print(check_group)
        if check_group:
            if check_group[0][2] == 1:
                dtbs_c.execute("UPDATE UsersGroups SET upget = 0 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                send_message(bot, msg.chat.id, 'Ты отписался от группы "' + msg.text + '"', False)
            else:
                send_message(bot, msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"', False)
        else:
            send_message(bot, msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"', False)

    if bot_condition[0][0] == 2:
        # print(check_group)
        if not check_group:
            # print(msg.chat.id)
            dtbs_c.execute("INSERT INTO UsersGroups (uid, gid, upget) VALUES (?, ?, 1)", (msg.chat.id, grp_id,))
            send_message(bot, msg.chat.id, 'Ты подписался на группу "' + msg.text + '"', False)
        else:
            if check_group[0][2] == 0:
                dtbs_c.execute("UPDATE UsersGroups SET upget = 1 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                send_message(bot, msg.chat.id, 'Ты подписался на группу "' + msg.text + '"', False)
            else:
                send_message(bot, msg.chat.id, 'Группа "' + msg.text + '" уже была выбрана', False)

    if bot_condition[0][0] == 3:
        # print(check_group)
        if check_group:
            if check_group[0][3] == 1:
                dtbs_c.execute("UPDATE UsersGroups SET fetget = 0 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                send_message(bot, msg.chat.id, 'Ты отписался от группы "' + msg.text + '"', False)
            else:
                send_message(bot, msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"', False)
        else:
            send_message(bot, msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"', False)

    if bot_condition[0][0] == 4:
        # print(check_group)
        if not check_group:
            # print(msg.chat.id)
            dtbs_c.execute("INSERT INTO UsersGroups (uid, gid, fetget) VALUES (?, ?, 1)", (msg.chat.id, grp_id,))
            send_message(bot, msg.chat.id, 'Ты подписался на группу "' + msg.text + '"', False)
        else:
            # print(check_group[0][3])
            if check_group[0][3] == 0:
                dtbs_c.execute("UPDATE UsersGroups SET fetget = 1 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                send_message(bot, msg.chat.id, 'Ты подписался на группу "' + msg.text + '"', False)
            else:
                send_message(bot, msg.chat.id, 'Группа "' + msg.text + '" уже была выбрана', False)

    dtbs.commit()
    dtbs.close()


def five_last_posts(msg):
    arr_link = []
    link_count = 0
    dtbs = sqlite3.connect(dbpath)
    dtbs_c = dtbs.cursor()

    dtbs_c.execute("SELECT p.id, g.name, p.p_text FROM Posts as p, UsersGroups as ug, Groups as g "
                   "WHERE ug.uid = ? AND ug.gid = p.gid AND ug.gid = g.id AND ug.fetget = 1 "
                   "ORDER BY p.p_date DESC ", (msg.chat.id,))
    flp = dtbs_c.fetchall()
    for i in flp:
        link = str(i[1]) + '\n' + i[2] + '\n' + 'https://vk.com/wall-' + str(i[0])
        if link_count < 5:
            arr_link.append(link)
            link_count += 1

    dtbs.close()
    return arr_link


def five_last_rss(msg):
    arr_link = []
    rss_count = 0
    dtbs = sqlite3.connect(dbpath)
    dtbs_c = dtbs.cursor()

    dtbs_c.execute("SELECT g.name, rss.rss_title, rss.rss_link FROM Groups as g, RSS as rss, UsersGroups as ug"
                   " WHERE ug.uid = ? AND ug.gid = rss.rss_id AND ug.gid = g.id AND ug.fetget = 1 "
                   "ORDER BY rss.rss_date DESC", (msg.chat.id,))
    last_rss = dtbs_c.fetchall()
    for i in last_rss:
        link = str(i[0]) + '\n' + i[1] + '\n' + i[2]
        if rss_count < 5:
            arr_link.append(link)
            rss_count += 1

    return arr_link

def groups_list():
    databasem = sqlite3.connect(dbpath)
    dbm = databasem.cursor()
    dbm.execute("SELECT * FROM Groups")
    groups = dbm.fetchall()
    dbm.close()
    return groups

def vk_groups_list():
    databasem = sqlite3.connect(dbpath)
    dbm = databasem.cursor()
    dbm.execute("SELECT * FROM Groups WHERE id NOT LIKE 'rss%'")
    groups = dbm.fetchall()
    dbm.close()
    return groups

def rss_groups_list():
    databasem = sqlite3.connect(dbpath)
    dbm = databasem.cursor()
    dbm.execute("SELECT * FROM Groups WHERE id LIKE 'rss%'")
    groups = dbm.fetchall()
    dbm.close()
    return groups

def user_name(id):
    databasem = sqlite3.connect(dbpath)
    dbm = databasem.cursor()
    print(id)
    dbm.execute("SELECT username, first_name FROM Users WHERE id = ?", (id,))
    user = dbm.fetchall()
    dbm.close()
    print (user)
    if user[0][1]:
        name = user[0][1]
    elif user[0][0]:
        name = user[0][0]
    else:
        name = 'Друг'
    return name