import bot_modules
import sqlite3
import time
import traceback

dbpath = bot_modules.dbpath
bot = bot_modules.bot

# nextb = bot_modules.nextb

database = sqlite3.connect(dbpath)
db = database.cursor()
db.execute("SELECT id FROM Users")
users = db.fetchall()
for i in users:
    try:
        u = bot.get_chat(i[0]).username
        f = bot.get_chat(i[0]).first_name
        l = bot.get_chat(i[0]).last_name
        db.execute("UPDATE Users SET username = ?, first_name = ?, last_name = ? WHERE id = ?", (u, f, l, i[0],))
    except Exception as e:
        print(e)
database.commit()
database.close()

bot_modules.get_rss_post()

bot_modules.get_vk_post()

bot_modules.evening_hse()


@bot.message_handler(commands=['start'])
def welcome(message):
    bot_modules.send_welcome(message)


@bot.message_handler(commands=['stop'])
def bye(message):
    bot_modules.send_goodbye(message)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def menu(message):
    bot_modules.main_menu(message)


@bot.message_handler(func=lambda message: True, content_types=['location'])
def loc(message):
    bot_modules.location(message)


@bot.message_handler(func=lambda message: True, content_types=['sticker'])
def admin(message):
    bot_modules.administrator(message)


def telegram_polling():
    try:
        bot.polling(none_stop=True, timeout=60)  # constantly get messages from Telegram
    except:
        with open("logs.log", "a") as file:
            file.write("\r\n\r\n" + time.strftime("%c")+"\r\n<<ERROR polling>>\r\n" + traceback.format_exc() +
                       "\r\n<<ERROR polling>>")
        bot.stop_polling()
        time.sleep(100)
        telegram_polling()

if __name__ == '__main__':
    telegram_polling()
