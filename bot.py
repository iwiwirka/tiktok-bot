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
      "Привет! Скинь мне список видео (каждое с новой строки) в формате:\n"
      "`ссылка просмотры лайки избранное`\n\nПример:\n`https://tiktok.com/... 5000"
      " 150 20`",
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: "tiktok.com" in message.text and "http" in message.text
)
def handle_batch_input(message):
  lines = message.text.strip().split("\n")
  report_text = "📊 **Анализ и расчет накрутки:**\n\n"
  calculations = []

  for idx, line in enumerate(lines[:10], 1):
    # Ищем ссылку в строке
    link_match = re.search(r"https?://[^\s]+tiktok[^\s]+", line)
    if not link_match:
      continue

    link = link_match.group(0)

    # Ищем все числа в оставшейся части строки
    numbers = re.findall(r"\d+", line.replace(link, ""))

    current_views = int(numbers[0]) if len(numbers) > 0 else 0
    current_likes = int(numbers[1]) if len(numbers) > 1 else 0
    current_favs = int(numbers[2]) if len(numbers) > 2 else 0

    # Целевые диапазоны с рандомом
    target_views = random.randint(7500, 8500)
    target_likes = random.randint(240, 360)

    need_views = max(0, target_views - current_views)
    need_likes = max(0, target_likes - current_likes)

    calculations.append({"link": link, "views": need_views, "likes": need_likes})

    report_text += (
        f"**Видео {idx}**\n"
        f"🔗 {link}\n"
        f"• Просмотры: {current_views} (цель ~{target_views}) | докупить:"
        f" **{need_views}**\n"
        f"• Лайки: {current_likes} (цель ~{target_likes}) | докупить:"
        f" **{need_likes}**\n"
        f"• Избранное: {current_favs}\n\n"
    )

  if not calculations:
    bot.reply_to(
        message, "⚠️ Не удалось распознать формат. Проверьте пример и повторите."
    )
    return

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
    status_text += (
        "\n⚠️ Внимание: часть запросов не прошла (проверь баланс на сайте)."
    )
  bot.edit_message_text(status_text, chat_id, call.message.message_id)


def run_bot():
  bot.infinity_polling()


if __name__ == "__main__":
  t = threading.Thread(target=run_bot)
  t.start()
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
