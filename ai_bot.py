
import telebot
import requests
import json
import os
from datetime import datetime
from telebot import types

# === ТОКЕН ===
bot = telebot.TeleBot("ВАШ_ТОКЕН")

# === КЛЮЧ GROQ ===
api_key = "gsk_ваш_ключ"

# === ПРОКСИ ===
proxies = {
    "http": "http://127.0.0.1:12334",
    "https": "http://127.0.0.1:12334"
}

# === ФАЙЛЫ ===
HISTORY_FILE = "chat_history.json"
ROLES_FILE = "chat_roles.json"
SETTINGS_FILE = "chat_settings.json"

# === ЗАГРУЗКА / СОХРАНЕНИЕ ===
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === ЗАГРУЖАЕМ ===
history = load_json(HISTORY_FILE)
roles = load_json(ROLES_FILE)
settings = load_json(SETTINGS_FILE)

# === НАСТРОЙКИ ПО УМОЛЧАНИЮ ===
DEFAULT_SETTINGS = {"temperature": 0.7, "max_tokens": 1000}

def get_settings(user_id_str):
    if user_id_str not in settings:
        settings[user_id_str] = DEFAULT_SETTINGS.copy()
        save_json(SETTINGS_FILE, settings)
    return settings[user_id_str]

# === КНОПКИ ===
def main_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎭 Сменить роль", callback_data="role_help"))
    kb.add(types.InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    kb.add(types.InlineKeyboardButton("📜 История", callback_data="history"))
    kb.add(types.InlineKeyboardButton("📝 Резюме диалога", callback_data="summary"))
    kb.add(types.InlineKeyboardButton("⚙ Настройки", callback_data="settings"))
    kb.add(types.InlineKeyboardButton("🗑 Очистить", callback_data="clear"))
    return kb

# === AI ===
def ask_ai(question, user_id):
    user_id_str = str(user_id)
    if user_id_str not in history:
        history[user_id_str] = []

    system_msg = "Ты полезный ассистент."
    if user_id_str in roles:
        system_msg = "Ты — " + roles[user_id_str] + ". Отвечай в этой роли."

    messages = [{"role": "system", "content": system_msg}] + history[user_id_str]
    messages.append({"role": "user", "content": question})

    if len(messages) > 6:
        messages = [messages[0]] + messages[-4:]

    user_settings = get_settings(user_id_str)

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-oss-20b",
                "messages": messages,
                "temperature": user_settings["temperature"],
                "max_tokens": user_settings["max_tokens"]
            },
            proxies=proxies,
            timeout=60
        )
        data = response.json()
        if "choices" in data:
            answer = data["choices"][0]["message"]["content"]
            history[user_id_str].append({"role": "user", "content": question})
            history[user_id_str].append({"role": "assistant", "content": answer})
            if len(history[user_id_str]) > 10:
                history[user_id_str] = history[user_id_str][-10:]
            save_json(HISTORY_FILE, history)
            if len(answer) > 4000:
                answer = answer[:4000] + "..."
            return answer
        else:
            return "Ошибка: " + str(data)[:200]
    except Exception as e:
        return "Ошибка: " + str(e)[:200]

# === /start ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "Привет! Я AI-бот.\n\n"
        "Напиши вопрос — отвечу.\n"
        "Команды: /help, /role, /stats, /settings, /summary, /export, /clear",
        reply_markup=main_keyboard()
    )

# === /help ===
@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id,
        "📋 Что я умею:\n\n"
        "Задай вопрос — отвечу.\n\n"
        "Команды:\n"
        "/role [роль] — задать роль\n"
        "/stats — статистика\n"
        "/settings — настройки\n"
        "/set_temp 0.7 — креативность (0–1)\n"
        "/set_tokens 500 — длина (100–4000)\n"
        "/reset — сброс настроек\n"
        "/summary — резюме диалога\n"
        "/export — скачать историю\n"
        "/clear — очистить историю",
        reply_markup=main_keyboard()
    )

# === /role ===
@bot.message_handler(commands=['role'])
def set_role(message):
    text = message.text.replace("/role", "").strip()
    user_id_str = str(message.from_user.id)
    if not text:
        if user_id_str in roles:
            bot.reply_to(message, "Текущая роль: " + roles[user_id_str])
        else:
            bot.reply_to(message, "Роль не задана. Используй: /role учитель")
        return
    roles[user_id_str] = text
    save_json(ROLES_FILE, roles)
    bot.reply_to(message, "Роль установлена: " + text)

# === /stats ===
@bot.message_handler(commands=['stats'])
def stats(message):
    user_id_str = str(message.from_user.id)
    count = len(history.get(user_id_str, []))
    role = roles.get(user_id_str, "не задана")
    bot.reply_to(message, "Сообщений: " + str(count) + "\nРоль: " + role)

# === /settings ===
@bot.message_handler(commands=['settings'])
def show_settings(message):
    user_id_str = str(message.from_user.id)
    s = get_settings(user_id_str)
    bot.reply_to(message,
        "⚙ Текущие настройки:\n\n"
        "🌡 Креативность (temperature): " + str(s["temperature"]) + "\n"
        "📏 Длина ответа (max_tokens): " + str(s["max_tokens"]) + "\n\n"
        "Изменить:\n"
        "/set_temp 0.5\n"
        "/set_tokens 1500\n"
        "/reset — сброс"
    )

# === /set_temp ===
@bot.message_handler(commands=['set_temp'])
def set_temp(message):
    user_id_str = str(message.from_user.id)
    try:
        val = float(message.text.replace("/set_temp", "").strip())
        if val < 0 or val > 1:
            bot.reply_to(message, "Значение должно быть от 0 до 1.")
            return
        s = get_settings(user_id_str)
        s["temperature"] = val
        save_json(SETTINGS_FILE, settings)
        bot.reply_to(message, "Креативность установлена: " + str(val))
    except:
        bot.reply_to(message, "Используй: /set_temp 0.7 (число от 0 до 1)")

# === /set_tokens ===
@bot.message_handler(commands=['set_tokens'])
def set_tokens(message):
    user_id_str = str(message.from_user.id)
    try:
        val = int(message.text.replace("/set_tokens", "").strip())
        if val < 100 or val > 4000:
            bot.reply_to(message, "Значение от 100 до 4000.")
            return
        s = get_settings(user_id_str)
        s["max_tokens"] = val
        save_json(SETTINGS_FILE, settings)
        bot.reply_to(message, "Длина ответа: " + str(val))
    except:
        bot.reply_to(message, "Используй: /set_tokens 500 (число от 100 до 4000)")

# === /reset ===
@bot.message_handler(commands=['reset'])
def reset_settings(message):
    user_id_str = str(message.from_user.id)
    settings[user_id_str] = DEFAULT_SETTINGS.copy()
    save_json(SETTINGS_FILE, settings)
    bot.reply_to(message, "Настройки сброшены.")

# === /history ===
@bot.message_handler(commands=['history'])
def show_history(message):
    user_id_str = str(message.from_user.id)
    msgs = history.get(user_id_str, [])
    if not msgs:
        bot.reply_to(message, "История пуста.")
        return
    last = msgs[-10:]
    text = "Последние сообщения:\n\n"
    for m in last:
        r = "👤" if m["role"] == "user" else "🤖"
        text += r + " " + m["content"][:150] + "\n\n"
    bot.reply_to(message, text[:4000])

# === /summary ===
@bot.message_handler(commands=['summary'])
def summary(message):
    user_id_str = str(message.from_user.id)
    msgs = history.get(user_id_str, [])
    if len(msgs) < 2:
        bot.reply_to(message, "Слишком короткий диалог.")
        return
    bot.reply_to(message, "Делаю резюме...")
    dialog_text = ""
    for m in msgs:
        role = "Пользователь" if m["role"] == "user" else "AI"
        dialog_text += role + ": " + m["content"][:300] + "\n"
    prompt = "Кратко перескажи диалог в 3-5 предложениях:\n\n" + dialog_text
    answer = ask_ai(prompt, user_id_str + "_summary")
    bot.reply_to(message, "📝 Резюме:\n\n" + answer)

# === /export ===
@bot.message_handler(commands=['export'])
def export_history(message):
    user_id_str = str(message.from_user.id)
    msgs = history.get(user_id_str, [])
    if not msgs:
        bot.reply_to(message, "История пуста.")
        return
    filename = "export_" + user_id_str + ".txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("Экспорт от " + datetime.now().strftime("%Y-%m-%d %H:%M") + "\n\n")
        for m in msgs:
            role = "Пользователь" if m["role"] == "user" else "AI"
            f.write("[" + role + "]\n" + m["content"] + "\n\n")
    with open(filename, "rb") as f:
        bot.send_document(message.chat.id, f)

# === /clear ===
@bot.message_handler(commands=['clear'])
def clear(message):
    history[str(message.from_user.id)] = []
    save_json(HISTORY_FILE, history)
    bot.reply_to(message, "История очищена.")

# === КНОПКИ ===
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id_str = str(call.from_user.id)
    if call.data == "role_help":
        bot.send_message(call.message.chat.id, "Напиши: /role учитель")
    elif call.data == "stats":
        count = len(history.get(user_id_str, []))
        role = roles.get(user_id_str, "не задана")
        bot.send_message(call.message.chat.id, "Сообщений: " + str(count) + "\nРоль: " + role)
    elif call.data == "settings":
        show_settings(call.message)
    elif call.data == "history":
        msgs = history.get(user_id_str, [])
        if not msgs:
            bot.send_message(call.message.chat.id, "История пуста.")
        else:
            last = msgs[-10:]
            text = "Последние:\n\n"
            for m in last:
                r = "👤" if m["role"] == "user" else "🤖"
                text += r + " " + m["content"][:150] + "\n\n"
            bot.send_message(call.message.chat.id, text[:4000])
    elif call.data == "summary":
        summary(call.message)
    elif call.data == "clear":
        history[user_id_str] = []
        save_json(HISTORY_FILE, history)
        bot.send_message(call.message.chat.id, "История очищена.")

# === ОБРАБОТКА ===
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    question = message.text
    user_id = message.from_user.id
    print("Пользователь:", question)
    bot.reply_to(message, "AI думает...")
    answer = ask_ai(question, user_id)
    try:
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, "Ошибка отправки: " + str(e)[:100])

# === ЗАПУСК ===
print("Бот с настройками запущен...")
telebot.apihelper.proxy = {'https': 'http://127.0.0.1:12334'}
bot.infinity_polling()
