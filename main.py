import json
from telethon import TelegramClient, events, Button as button
import sqlite3
import os

db = "data.db"

if os.path.exists(db):
    os.remove(db)


def load_config(filename):
    with open(filename, 'r') as f:
        tconfig = json.load(f)
    return tconfig


config = load_config('config.json')

token = config['token']
api_id = config['api_id']
api_hash = config['api_hash']
admins = config['admins']

client = TelegramClient('init', api_id, api_hash).start(bot_token=token)

conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tgid INTEGER UNIQUE NOT NULL,
        name TEXT NOT NULL,
        emoji TEXT DEFAULT NULL
    )
''')
conn.commit()

user_emojis = {}
emojis = ['🐶', '🐈‍⬛', '🐭', '🐹', '🐰', '🦊', '🐼', '🦁', '🐵', '🐧']
used_emojis = set()
deletion = True
access_password = "Zfats-0271-ijks-0009"


@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))
    dummy = cur.fetchone()
    if not dummy:
        await event.respond('Введите пароль для доступа к боту\nФормат - /password <ваш пароль> ')
    else:
        cur.execute('SELECT emoji FROM users WHERE tgid = ?', (user_id,))
        user_data = cur.fetchone()
        if user_data and user_data[0]:
            await event.respond('Вы уже выбрали эмодзи. Можете продолжать общение.')
        else:
            buttons = [button.inline(emoji, data=emoji) for emoji in emojis]
            await event.respond('Привет! Выберите себе эмодзи для анонимного общения:', buttons=buttons)


@client.on(events.NewMessage)
async def handle_password(event):
    user_id = event.sender_id
    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))
    dummy = cur.fetchone()
    if not dummy and event.raw_text.startswith('/password '):
        entered_password = event.raw_text.split(' ', 1)[1]
        if entered_password == access_password:
            cur.execute('INSERT INTO users (tgid, name) VALUES (?, ?)', (user_id, event.sender.first_name))
            conn.commit()
            await event.respond('Пароль принят. Теперь вы можете использовать бота. Введите /start для начала.')
        else:
            await event.respond('Неверный пароль. Попробуйте снова.')
        return

    if not dummy:
        return


@client.on(events.CallbackQuery)
async def callback(event):
    user_id = event.sender_id
    chosen_emoji = event.data.decode('utf-8')
    cur.execute('SELECT emoji FROM users WHERE tgid = ?', (user_id,))
    user_data = cur.fetchone()
    if chosen_emoji in emojis:
        if user_data and chosen_emoji == user_data[0]:
            await event.answer('Этот эмодзи уже выбран, пожалуйста, выберите другой.')
        else:
            user_emojis[user_id] = chosen_emoji
            used_emojis.add(chosen_emoji)
            cur.execute('UPDATE users SET emoji = ? WHERE tgid = ?', (chosen_emoji, user_id))
            conn.commit()
            await event.edit(f'Вы выбрали эмодзи: {chosen_emoji}. Теперь вы анонимны под этим эмодзи.')
            await event.respond('Так-же вам доступен следующий функционал:',
                                buttons=[
                                    [button.inline("✅ Включить удаление сообщений", b'enable')],
                                    [button.inline("❌ Выключить удаление сообщений", b'disable')],
                                    # [button.inline("Удалить все сообщения", b'clear')]
                                ])


@client.on(events.NewMessage(pattern='/settings'))
async def setting(event):
    await event.respond('Настройки',
                        buttons=[
                            [button.inline("✅ Включить удаление сообщений", b'enable')],
                            [button.inline("❌ Выключить удаление сообщений", b'disable')],
                            # [button.inline("Удалить все сообщения", b'clear')]
                        ])


@client.on(events.NewMessage)
async def handle_message(event):
    global deletion
    user_id = event.sender_id
    cur.execute('SELECT tgid FROM users WHERE tgid = ?', (user_id,))
    if cur.fetchone() is None:
        return

    chosen_emoji = user_emojis.get(user_id)
    if chosen_emoji:
        message = f'{chosen_emoji}: {event.raw_text}'
        # buttons = [button.inline('Удалить', data=f'delete_{event.message.id}')]
        cur.execute('SELECT tgid FROM users')
        all_users = cur.fetchall()
        for user in all_users:
            if user[0] != user_id:
                if event.raw_text != '/settings' or event.raw_text != '/start':
                    await client.send_message(user[0], message)
        if deletion:
            await event.delete()


@client.on(events.CallbackQuery)
async def handle_callback_query(event):
    global deletion
    user_id = event.sender_id

    if event.data == b'enable':
        deletion = True
        await event.answer('Удаление сообщений включено.')
    elif event.data == b'disable':
        deletion = False
        await event.answer('Удаление сообщений отключено.')
    # elif event.data == b'clear':
    #     user_id = event.sender_id
    #     async for message in client.iter_messages(user_id):
    #         await client.delete_messages(user_id, message.id)


@client.on(events.NewMessage(pattern='/display'))
async def display(event):
    if event.sender_id in admins:
        cur.execute('SELECT * FROM USERS')
        message = cur.fetchall()
        await event.respond(str(message))

client.run_until_disconnected()
