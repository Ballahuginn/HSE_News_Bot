import sqlite3
import datetime
import threading
import feedparser


Month = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'June': '06',
         'July': '07', 'Aug': '08', 'Sept': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}

databasem = sqlite3.connect('HSE_BOT_DB.sqlite')

dbm = databasem.cursor()

dbm.execute("SELECT * FROM Groups WHERE id LIKE 'rss%'")
rss_groups = dbm.fetchall()

dbm.execute("SELECT * FROM Groups WHERE id NOT LIKE 'rss%'")
vk_groups = dbm.fetchall()


def get_rss_post(bot):
    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    for i in rss_groups:
        print(i[1])
        db.execute("SELECT MAX(rss_date) FROM RSS WHERE rss_id = ?", (str(i[0]),))
        last_post = db.fetchall()
        db.execute("SELECT u.id FROM Users as u, UsersGroups as ug "
                   "WHERE u.id = ug.uid AND ug.upget = 1 AND ug.gid = ?", (str(i[0]),))
        sub_users = db.fetchall()
        print(sub_users)
        rss = feedparser.parse(i[2])
        entr = rss['entries']
        for g in entr:
            t = g['published'].split(' ')
            if t[2] in Month:
                t[2] = Month[t[2]]
            rssdate = t[1:4]
            for t in t[4].split(':'):
                rssdate.append(t)
            rssdate = '/'.join(rssdate)
            utime = datetime.datetime.strptime(rssdate, "%d/%m/%Y/%H/%M/%S").strftime("%s")
            if int(utime) > int(last_post[0][0]):
                link = str(i[1]) + '\n' + str(g['title']) + '\n' + str(g['links'][0]['href'])
                print(link)
                for u in sub_users:
                    bot.send_message(u[0], link)

    db.execute("DELETE FROM RSS")

    for i in rss_groups:
        rss = feedparser.parse(i[2])
        entr = rss['entries']
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
    database.close()
    t = threading.Timer(3600, get_rss_post)
    t.start()


def post_texts(vk_post):
    if 'text' in vk_post:
        psttxt = []
        mas = vk_post['text']
        mas1 = mas.split(' ')
        if len(mas1) < 5:
            for r in mas1:
                psttxt.append(r)
        else:
            v = mas1[4]
            if v[-1] == ',' or v[-1] == ':' or v[-1] == ';' or v[-1] == '-' or v[-1] == '—':
                psttxt.extend((mas1[0], ' ', mas1[1], ' ', mas1[2], ' ', mas1[3], ' ', v[:-1], '...'))
            elif v[-1] == '!' or v[-1] == '?' or v[-1] == '.':
                psttxt.extend((mas1[0], ' ', mas1[1], ' ', mas1[2], ' ', mas1[3], ' ', mas1[4]))
            else:
                psttxt.extend((mas1[0], ' ', mas1[1], ' ', mas1[2], ' ', mas1[3], ' ', mas1[4], '...'))
    return ''.join(psttxt)


def get_vk_post(bot, vk_api):
    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    for i in vk_groups:
        print(i[1])
        db.execute("SELECT MAX(p_date) FROM Posts WHERE gid = ?", (str(i[0]),))
        last_post = db.fetchall()
        db.execute("SELECT u.id FROM Users as u, UsersGroups as ug "
                   "WHERE u.id = ug.uid AND ug.upget = 1 AND ug.gid = ?", (str(i[0]),))
        sub_users = db.fetchall()
        print(sub_users)
        posts = vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
        for p in posts['items']:
            if type(p) != int:
                if 'id' in p:
                    if int(p['date']) > int(last_post[0][0]):
                        txt = post_texts(p)
                        print('new post')
                        link = str(i[1]) + '\n' + txt + '\n' + 'https://vk.com/wall-' + i[0] + '_' + str(p['id'])
                        for u in sub_users:
                            bot.send_message(u[0], link)

    db.execute("DELETE FROM Posts")

    for i in vk_groups:
        posts = vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
        for _k in posts['items']:
            if type(_k) != int:
                if 'id' in _k:
                    txt = post_texts(_k)
                    db.execute("INSERT INTO Posts (id, gid, p_date, p_text, p_likes, p_reposts) "
                               "VALUES (?, ?, ?, ?, ?, ?)",
                               (str(i[0]) + '_' + str(_k['id']), str(i[0]), str(_k['date']), str(txt),
                               _k['likes']['count'], _k['reposts']['count']))

    database.commit()
    database.close()
    t = threading.Timer(60, get_vk_post, [bot, vk_api])
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


def press_next(db, database, message, groups, bot, bot_modules, types):
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
        markup.row('Завершить')
        markup.row('Отменить все')
        check_if_all = bot_modules.groups_as_buttons_unsub(groups, active_groups, markup)
        if check_if_all > 0:
            bot.send_message(message.chat.id, 'Выбери группы, откуда ты НЕ хочешь получать новости, как только они '
                                              'выходят, а затем нажми "Завершить"', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, 'Ты НЕ подписан на получение новостей по запросу')
            markup = bot_modules.press_done(db, database, message, types)
            bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)

    if bot_condition[0][0] == 2:
        db.execute("UPDATE Users SET bcond = 4 WHERE id = ?", (message.chat.id,))
        database.commit()
        db.execute("SELECT g.id, g.name, g.g_link FROM Groups as g, UsersGroups as ug "
                   "WHERE ug.uid = ? AND ug.gid = g.id AND ug.fetget = 1",
                   (message.chat.id,))
        active_groups = db.fetchall()
        markup = types.ReplyKeyboardMarkup()
        markup.row('Завершить')
        markup.row('Выбрать все')
        check_if_all = bot_modules.groups_as_buttons_sub(groups, active_groups, markup)
        if check_if_all > 0:
            if len(active_groups) != 0:
                bot.send_message(message.chat.id, 'Ты уже подписан на следующие группы:')
                for i in active_groups:
                    bot.send_message(message.chat.id, i[1])
            bot.send_message(message.chat.id, 'Выбери группы, откуда ты хочешь получать новости по запросу'
                                              ', а затем нажми Завершить', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, 'Ты подписан на все группы для получения новостей '
                                              'по запросу')
            markup = bot_modules.press_done(db, database, message, types)
            bot.send_message(message.chat.id, 'Настройка завершена', reply_markup=markup)


def press_done(db, database, message, types):
    db.execute("UPDATE Users SET bcond = 0 WHERE id = ?", (message.chat.id,))
    database.commit()
    markup2 = types.ReplyKeyboardMarkup()
    markup2.row('5 последних постов')
    markup2.row('5 последних постов из RSS')
    markup2.row('Настройки')
    markup2.row('О проекте')
    markup2.row('Оставить пожелания')

    return markup2


def group_selection(bot, msg, grp_id, bot_condition):
    dtbs = sqlite3.connect('HSE_BOT_DB.sqlite')
    dtbs_c = dtbs.cursor()
    dtbs_c.execute("SELECT * FROM UsersGroups WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
    check_group = dtbs_c.fetchall()
    print(bot_condition[0][0])

    if bot_condition[0][0] == 1:
        print(check_group)
        if check_group:
            if check_group[0][2] == 1:
                dtbs_c.execute("UPDATE UsersGroups SET upget = 0 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                bot.send_message(msg.chat.id, 'Ты отписался от группы "' + msg.text + '"')
            else:
                bot.send_message(msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"')
        else:
            bot.send_message(msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"')

    if bot_condition[0][0] == 2:
        print(check_group)
        if not check_group:
            print(msg.chat.id)
            dtbs_c.execute("INSERT INTO UsersGroups (uid, gid, upget) VALUES (?, ?, 1)", (msg.chat.id, grp_id,))
            bot.send_message(msg.chat.id, 'Ты подписался на группу "' + msg.text + '"')
        else:
            if check_group[0][2] == 0:
                dtbs_c.execute("UPDATE UsersGroups SET upget = 1 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                bot.send_message(msg.chat.id, 'Ты подписался на группу "' + msg.text + '"')
            else:
                bot.send_message(msg.chat.id, 'Группа "' + msg.text + '" уже была выбрана')

    if bot_condition[0][0] == 3:
        print(check_group)
        if check_group:
            if check_group[0][3] == 1:
                dtbs_c.execute("UPDATE UsersGroups SET fetget = 0 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                bot.send_message(msg.chat.id, 'Ты отписался от группы "' + msg.text + '"')
            else:
                bot.send_message(msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"')
        else:
            bot.send_message(msg.chat.id, 'Ты не подписан на группу "' + msg.text + '"')

    if bot_condition[0][0] == 4:
        print(check_group)
        if not check_group:
            print(msg.chat.id)
            dtbs_c.execute("INSERT INTO UsersGroups (uid, gid, fetget) VALUES (?, ?, 1)", (msg.chat.id, grp_id,))
            bot.send_message(msg.chat.id, 'Ты подписался на группу "' + msg.text + '"')
        else:
            print(check_group[0][3])
            if check_group[0][3] == 0:
                dtbs_c.execute("UPDATE UsersGroups SET fetget = 1 WHERE gid = ? AND uid =?", (grp_id, msg.chat.id,))
                bot.send_message(msg.chat.id, 'Ты подписался на группу "' + msg.text + '"')
            else:
                bot.send_message(msg.chat.id, 'Группа "' + msg.text + '" уже была выбрана')

    dtbs.commit()
    dtbs.close()


def five_last_posts(msg):
    arr_link = []
    link_count = 0
    dtbs = sqlite3.connect('HSE_BOT_DB.sqlite')
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
    dtbs = sqlite3.connect('HSE_BOT_DB.sqlite')
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
