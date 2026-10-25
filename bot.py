import os
import random
import re
import threading
from flask import Flask
import requests
import telebot

BOT_TOKEN = "8907166799:AAHGfIk4wcl1mNFhgRl-B9JjRHYEWXVG3Hw"
VEXBOOST_API_URL = "https://vexboost.ru/api/v2"
VEXBOOST_KEY = "Y2qXohHbsChY0qHBrTBD6CiOlboYAALW5sSW1nkkCr8qlPjmNHXnpLqUqJX4"

SERVICE_LIKES = 2904
SERVICE_VIEWS = 3129

bot = telebot.TeleBot(BOT_TOKEN)
user_calculations = {}

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running!"


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        "Привет! Бот на связи в облаке. Скинь мне список ссылок на TikTok, и я посчитаю нехватку до твоих целей с рандомом.",
    )


@bot.message_handler(func=lambda message: "tiktok.com" in message.text)
def handle_tiktok_links(message):
    links = re.findall(r"https?://[^\s]+tiktok[^\s]+", message.text)
    if not links:
        bot.reply_to(message, "Не нашел ссылок TikTok в сообщении.")
        return

    report_text = "📊 **Анализ видео и расчет накрутки:**\n\n"
    calculations = []

    for i, link in enumerate(links[:10], 1):
        current_views = random.randint(4500, 7400)
        current_likes = random.randint(100, 230)
        target_views = random.randint(7500, 8500)
        target_likes = random.randint(240, 360)

        need_views = max(0, target_views - current_views)
        need_likes = max(0, target_likes - current_likes)

        calculations.append(
            {"link": link, "views": need_views, "likes": need_likes}
        )
        report_text += (
            f"**Видео {i}**\n"
            f"🔗 {link}\n"
            f"• Просмотры: цель ~{target_views} | докупить: **{need_views}**\n"
            f"• Лайки: цель ~{target_likes} | докупить: **{need_likes}**\n\n"
        )

    user_calculations[message.chat.id] = calculations
    markup = telebot.types.InlineKeyboardMarkup()
    btn = telebot.types.InlineKeyboardButton(
        "🚀 Отправить заказы в VexBoost", callback_data="send_orders"
    )
    markup.add(btn)
    bot.send_message(message.chat.id, report_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "send_orders")
def callback_send_orders(call):
    chat_id = call.message.chat.id
    if chat_id not in user_calculations:
        bot.answer_callback_query(call.id, "Нет данных для заказа.")
        return

    calculations = user_calculations[chat_id]
    success_count = 0
    error_occurred = False

    for item in calculations:
        link = item["link"]
        views = item["views"]
        likes = item["likes"]

        if views > 0:
            try:
                r = requests.get(
                    VEXBOOST_API_URL,
                    params={
                        "key": VEXBOOST_KEY,
                        "action": "add",
                        "service": SERVICE_VIEWS,
                        "link": link,
                        "quantity": views,
                    },
                    timeout=10,
                )
                if "order" in r.json():
                    success_count += 1
                else:
                    error_occurred = True
            except:
                error_occurred = True

        if likes > 0:
            try:
                r = requests.get(
                    VEXBOOST_API_URL,
                    params={
                        "key": VEXBOOST_KEY,
                        "action": "add",
                        "service": SERVICE_LIKES,
                        "link": link,
                        "quantity": likes,
                    },
                    timeout=10,
                )
                if "order" in r.json():
                    success_count += 1
                else:
                    error_occurred = True
            except:
                error_occurred = True

    bot.answer_callback_query(call.id, "Заказы обработаны!")
    status_text = f"✅ **Готово! Успешных заказов:** {success_count}"
    if error_occurred:
        status_text += "\n⚠️ Внимание: часть запросов не прошла (проверь баланс)."
    bot.edit_message_text(status_text, chat_id, call.message.message_id)


def run_bot():
    bot.infinity_polling()


if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
