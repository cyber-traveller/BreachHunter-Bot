import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from random import randint
from dotenv import load_dotenv
import html

# Load environment variables
load_dotenv()

# Configuration from environment variables
bot_token = os.getenv('BOT_TOKEN')
api_token = os.getenv('API_TOKEN')
url = os.getenv('API_URL')
limit = int(os.getenv('LIMIT', 100))
lang = os.getenv('LANG', 'en')

# Validate required environment variables
if not all([bot_token, api_token, url]):
    raise ValueError("Missing required environment variables. Please check .env file.")

cash_reports = {}

# Funksioni për gjenerimin e raporteve
def sanitize_text(text):
    if not isinstance(text, str):
        text = str(text)
    return html.escape(text)

def generate_report(query, query_id):
    try:
        data = {"token": api_token, "request": query, "limit": limit, "lang": lang}
        response = requests.post(url, json=data).json()
    except Exception as e:
        return [f"⚠️ Request failed: {sanitize_text(e)}"]

    if "Error code" in response:
        return [f"⚠️ Error: {sanitize_text(response['Error code'])}"]

    reports = []
    full_report = []
    for database_name, details in response.get("List", {}).items():
        text = [f"{sanitize_text(database_name)}", ""]
        text.append(sanitize_text(details.get("InfoLeak", "No additional info")) + "\n")

        if database_name != "No results found":
            for report_data in details.get("Data", []):
                for column_name, value in report_data.items():
                    line = f"{sanitize_text(column_name)}: {sanitize_text(value)}"
                    text.append(line)
                    full_report.append(line)
                text.append("-"*20)

        formatted_text = "\n".join(text)
        reports.append(formatted_text)

    if not reports:
        reports = ["No results found"]

    full_report_text = "\n".join(full_report) if full_report else "No results found"
    cash_reports[str(query_id)] = {"pages": reports, "full_report": full_report_text}
    return reports

# Funksioni për krijimin e tastierës inline
def create_inline_keyboard(query_id, page_id, count_page):
    markup = InlineKeyboardMarkup()
    buttons = []
    if count_page > 1:
        if page_id > 0:
            buttons.append(InlineKeyboardButton("⬅️", callback_data=f"/page {query_id} {page_id - 1}"))
        buttons.append(InlineKeyboardButton(f"{page_id + 1}/{count_page}", callback_data="ignore"))
        if page_id < count_page - 1:
            buttons.append(InlineKeyboardButton("➡️", callback_data=f"/page {query_id} {page_id + 1}"))
    buttons.append(InlineKeyboardButton("📥 Download", callback_data=f"/download {query_id}"))
    markup.row(*buttons)
    return markup

bot = telebot.TeleBot(bot_token)

# Print startup message
print(f"\n{'='*50}")
print(f"Bot started successfully!")
print(f"Bot username: @{bot.get_me().username}")
print(f"Configuration:")
print(f" - API URL: {url}")
print(f" - Query limit: {limit}")
print(f" - Language: {lang}")
print(f"{'='*50}\n")

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "🔍 Hi! Send me an email, IP, or URL to search data breaches.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    query_id = randint(0, 9999999)
    reports = generate_report(message.text, query_id)

    markup = create_inline_keyboard(query_id, 0, len(reports))
    bot.send_message(message.chat.id, reports[0][:3500], parse_mode="html", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: CallbackQuery):
    if call.data == "ignore":
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("/page "):
        _, query_id, page_id = call.data.split()

        if query_id not in cash_reports:
            bot.answer_callback_query(call.id, "⚠️ Results expired.", show_alert=True)
            return

        reports = cash_reports[query_id]["pages"]
        page_id = int(page_id)
        markup = create_inline_keyboard(query_id, page_id, len(reports))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=reports[page_id][:3500],
            parse_mode="html",
            reply_markup=markup
        )

    if call.data.startswith("/download "):
        query_id = call.data.split()[1]

        if query_id not in cash_reports:
            bot.answer_callback_query(call.id, "⚠️ Results expired.", show_alert=True)
            return

        full_report = cash_reports[query_id]["full_report"]
        import tempfile
        import os

        # Create a temporary file that will be automatically cleaned up
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as temp_file:
            temp_file.write(full_report)
            temp_path = temp_file.name

        try:
            with open(temp_path, "rb") as file:
                bot.send_document(call.message.chat.id, file)
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

if __name__ == "__main__":
    bot.polling()