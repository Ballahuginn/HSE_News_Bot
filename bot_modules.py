import sqlite3
import datetime
import threading
import feedparser
import bot_main


Month = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'June': '06',
         'July': '07', 'Aug': '08', 'Sept': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}

databasem = sqlite3.connect('HSE_BOT_DB.sqlite')

dbm = databasem.cursor()

dbm.execute("SELECT * FROM Groups WHERE id LIKE 'rss%'")
rss_groups = dbm.fetchall()

dbm.execute("SELECT * FROM Groups WHERE id NOT LIKE 'rss%'")
vk_groups = dbm.fetchall()


def get_rss_post():
    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    db.execute("DELETE FROM RSS")

    for i in rss_groups:
        rss = feedparser.parse(i[2])
        entr = rss['entries']
        for g in entr:
            print(g['title'])
            print(g['links'][0]['href'])
            t = g['published'].split(' ')
            if t[2] in Month:
                t[2] = Month[t[2]]
            rssdate = t[1:4]
            print(rssdate)
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


def get_vk_post():
    database = sqlite3.connect('HSE_BOT_DB.sqlite')
    db = database.cursor()

    for i in vk_groups:
        print(i[1])
        db.execute("SELECT MAX(p_date) FROM Posts WHERE gid = ?", (str(i[0]),))
        last_post = db.fetchall()
        db.execute("SELECT u.id FROM Users as u, UsersGroups as ug "
                   "WHERE u.id = ug.uid AND u.is_sub = 1 AND ug.gid = ?", (str(i[0]),))
        sub_users = db.fetchall()
        print(sub_users)
        posts = bot_main.vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
        for p in posts['items']:
            if type(p) != int:
                if 'id' in p:
                    if int(p['date']) > int(last_post[0][0]):
                        txt = post_texts(p)
                        print('new post')
                        link = str(i[1]) + '\n' + txt + '\n' + 'https://vk.com/wall-' + i[0] + '_' + str(p['id'])
                        for u in sub_users:
                            bot_main.bot.send_message(u[0], link)

    db.execute("DELETE FROM Posts")

    for i in vk_groups:
        posts = bot_main.vk_api.wall.get(owner_id='-' + i[0], count=6, filter='owner')
        for _k in posts['items']:
            if type(_k) != int:
                if 'id' in _k:
                    txt = post_texts(_k)
                    db.execute("INSERT INTO Posts (id, gid, p_date, p_text) VALUES (?, ?, ?, ?)",
                               (str(i[0]) + '_' + str(_k['id']), str(i[0]), str(_k['date']), str(txt)))

    database.commit()
    database.close()
    t = threading.Timer(60, get_vk_post)
    t.start()


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
        bot_main.bot.send_message(msg.chat.id, 'Ты выбрал ' + msg.text)
    else:
        bot_main.bot.send_message(msg.chat.id, msg.text + ' уже была выбрана')

    dtbs.close()


def five_last_posts(msg):
    arr_link = []
    link_count = 0
    dtbs = sqlite3.connect('HSE_BOT_DB.sqlite')
    dtbs_c = dtbs.cursor()

    dtbs_c.execute("SELECT p.id, g.name, p.p_text FROM Posts as p, UsersGroups as ug, Groups as g "
                   "WHERE ug.uid = ? AND ug.gid = p.gid AND ug.gid = g.id "
                   "ORDER BY p.p_date DESC ", (msg.chat.id,))
    flp = dtbs_c.fetchall()
    for i in flp:
        link = str(i[1]) + '\n' + i[2] + '\n' + 'https://vk.com/wall-' + str(i[0])
        if link_count < 5:
            print(i)
            arr_link.append(link)
            link_count += 1
            print(link)

    dtbs.close()
    return arr_link


def five_last_rss(msg):
    arr_link = []
    rss_count = 0
    dtbs = sqlite3.connect('HSE_BOT_DB.sqlite')
    dtbs_c = dtbs.cursor()

    dtbs_c.execute("SELECT g.name, rss.rss_title, rss.rss_link FROM Groups as g, RSS as rss, UsersGroups as ug"
                   " WHERE ug.uid = ? AND ug.gid = rss.rss_id AND ug.gid = g.id "
                   "ORDER BY rss.rss_date DESC", (msg.chat.id,))
    last_rss = dtbs_c.fetchall()
    for i in last_rss:
        link = str(i[0]) + '\n' + i[1] + '\n' + i[2]
        if rss_count < 5:
            print(i)
            arr_link.append(link)
            rss_count += 1
            print(link)

    return arr_link
