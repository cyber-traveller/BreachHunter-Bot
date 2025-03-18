import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import os
from random import randint
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('BOT_TOKEN')
api_token = os.getenv('API_TOKEN')
url = os.getenv('URL')
limit = int(os.getenv('LIMIT', 100))
lang = os.getenv('LANG', 'en')
cache_reports = {}
html_file = os.getenv('HTML_FILE', '4622177546.html')

bot = telebot.TeleBot(bot_token, parse_mode="HTML")

static_html_data = ""
if os.path.exists(html_file):
    with open(html_file, "r", encoding="utf-8") as f:
        static_html_data = f.read()

def generate_full_report(query, query_id):
    data = {"token": api_token, "request": query, "limit": limit, "lang": lang}
    try:
        response = requests.post(url, json=data).json()
    except Exception:
        return {}, 0

    leaks_found = 0
    grouped_data = []

    if "List" in response:
        for db, details in response["List"].items():
            if "Data" in details:
                leaks_found += len(details["Data"])
                grouped_data.append({"db": db, "info": details.get("InfoLeak", "No info"), "data": details["Data"]})

    cache_reports[str(query_id)] = {"grouped": grouped_data, "leaks": leaks_found}
    return grouped_data, leaks_found

def format_database_text(entry):
    text = f"""🔗<b>{entry['db']}</b>\n\n{entry['info']}\n\n"""
    for row in entry['data']:
        for k, v in row.items():
            if k.lower() == 'email':
                text += f"📩Email: {v}\n"
            elif k.lower() == 'password':
                text += f"🔑Password: {v}\n"
            elif k.lower() == 'link':
                text += f"🔗Link: {v}\n"
            elif k.lower() == 'ip':
                text += f"🌐IP: {v}\n"
            elif k.lower() == 'username':
                text += f"👤Username: {v}\n"
            elif k.lower() == 'phone' or k.lower() == 'phone2':
                text += f"📞Phone: {v}\n"
            else:
                text += f"<b>{k}:</b> {v}\n"
        text += "\n"
    return text

def format_database_html(entry):
    html = f"<h3>🔗{entry['db']}</h3><p>{entry['info']}</p><table class='table table-bordered table-striped'>"
    for row in entry['data']:
        for k, v in row.items():
            html += f"<tr><th>{k}</th><td>{v}</td></tr>"
        html += "<tr><td colspan='2'><hr></td></tr>"
    html += "</table>"
    return html

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Send the email or domain to search breaches.")

@bot.message_handler(func=lambda m: True)
def search(message):
    query_id = randint(10000, 99999)
    bot.send_chat_action(message.chat.id, 'typing')
    grouped, leaks = generate_full_report(message.text, query_id)

    summary = f"🔎Request: {message.text}\n🔬Subqueries executed: 1\n📁Results: {'FOUND' if leaks else 'NOT FOUND'}\n💦Leaks: {leaks}\n\n🪞Problems? @KubaneZii"
    bot.send_message(message.chat.id, summary)

    if not grouped:
        return

    cache_reports[str(query_id)]["grouped"] = grouped
    cache_reports[str(query_id)]["index"] = 0

    show_database(message.chat.id, query_id, 0)

def show_database(chat_id, query_id, index, message_id=None):
    entry = cache_reports[str(query_id)]["grouped"][index]
    text = format_database_text(entry)

    markup = InlineKeyboardMarkup()
    if index > 0:
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data=f"/page {query_id} {index - 1}"))
    if index < len(cache_reports[str(query_id)]["grouped"]) - 1:
        markup.add(InlineKeyboardButton("Next ➡️", callback_data=f"/page {query_id} {index + 1}"))
    markup.add(InlineKeyboardButton("📥 Download Full Report", callback_data=f"/download_full {query_id}"))

    if message_id:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("/page"):
        _, query_id, index = call.data.split()
        show_database(call.message.chat.id, query_id, int(index), call.message.message_id)

    if call.data.startswith("/download_full"):
        _, query_id = call.data.split()
        full_html = ""
        for entry in cache_reports[str(query_id)]["grouped"]:
            full_html += format_database_html(entry)

        html_output = f"""
<!DOCTYPE html>
<html>
<head><meta charset='UTF-8'><title>Full Leak Report</title>
<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css'>
<style>body {{ background-color: #f8f9fa; }} h3 {{ color: #0d6efd; }} table {{ background: #fff; }}</style>
</head>
<body class='container'>
{static_html_data}
{full_html}
</body></html>"""
        file_path = f"leak_full_{query_id}.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_output)
        with open(file_path, "rb") as f:
            bot.send_document(call.message.chat.id, f)

bot.polling()
