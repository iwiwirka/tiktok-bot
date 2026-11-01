import os
import random
import re
import threading
from flask import Flask
import requests
import telebot

BOT_TOKEN = "8907166799:AAHGfIk4wcl1mNFhgRl-B9JjRHYEWXVG3Hw"

# Настройки VexBoost (Просмотры и Лайки)
VEXBOOST_API_URL = "https://vexboost.ru/api/v2"
VEXBOOST_KEY = "Y2qXohHbsChY0qHBrTBD6CiOlboYAALW5sSW1nkkCr8qlPjmNHXnpLqUqJX4"
SERVICE_LIKES = 2904
SERVICE_VIEWS = 2915

# Настройки Социограм (Избранное)
SOCIOGRAMM_API_URL = "https://sociogramm.ru/panel/api/v1"
SOCIOGRAMM_KEY = "BdeES2VrR9DGGS2JGKuRpstFsboao8PI"
SERVICE_FAVORS = 558

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
      "`ссылка просмотры лайки избранное`\n\nПример:\n"
      "`https://tiktok.com/... 5000 150 20`",
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: "tiktok.com" in message.text and "http" in message.text
)
def handle_batch_input(message):
  lines = message.text.strip().split("\n")
  report_text = "📊 **Анализ и расчет накрутки (VexBoost + Социограм):**\n\n"
  calculations = []

  for idx, line in enumerate(lines[:10], 1):
    link_match = re.search(r"https?://[^\s]+tiktok[^\s]+", line)
    if not link_match:
      continue

    link = link_match.group(0)
    numbers = re.findall(r"\d+", line.replace(link, ""))

    current_views = int(numbers[0]) if len(numbers) > 0 else 0
    current_likes = int(numbers[1]) if len(numbers) > 1 else 0
    current_favs = int(numbers[2]) if len(numbers) > 2 else 0

    target_views = random.randint(7500, 8500)
    target_likes = random.randint(240, 360)
    target_favs = random.randint(25, 45)

    need_views = max(0, target_views - current_views)
    need_likes = max(0, target_likes - current_likes)

    need_favs = max(0, target_favs - current_favs)
    if 0 < need_favs < 10:
      need_favs = 10

    calculations.append({
        "link": link,
        "views": need_views,
        "likes": need_likes,
        "favs": need_favs,
    })

    report_text += (
        f"**Видео {idx}**\n"
        f"🔗 {link}\n"
        f"• Просмотры: {current_views} (цель ~{target_views}) | докупить:"
        f" **{need_views}**\n"
        f"• Лайки: {current_likes} (цель ~{target_likes}) | докупить:"
        f" **{need_likes}**\n"
        f"• Избранное: {current_favs} (цель ~{target_favs}) | докупить:"
        f" **{need_favs}**\n\n"
    )

  if not calculations:
    bot.reply_to(
        message, "⚠️ Не удалось распознать формат. Проверьте пример и повторите."
    )
    return

  user_calculations[message.chat.id] = calculations

  markup = telebot.types.InlineKeyboardMarkup()
  btn = telebot.types.InlineKeyboardButton(
      "🚀 Отправить заказы (VexBoost + Социограм)",
      callback_data="send_orders",
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
  failed_items = []

  for idx, item in enumerate(calculations, 1):
    link = item["link"]
    views = item["views"]
    likes = item["likes"]
    favs = item["favs"]

    # 1. Просмотры (VexBoost)
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
        ).json()
        if "order" in r:
          success_count += 1
        else:
          failed_items.append(f"Видео {idx}: Просмотры ({views} шт.)")
      except:
        failed_items.append(f"Видео {idx}: Просмотры (ошибка сети)")

    # 2. Лайки (VexBoost)
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
        ).json()
        if "order" in r:
          success_count += 1
        else:
          failed_items.append(f"Видео {idx}: Лайки ({likes} шт.)")
      except:
        failed_items.append(f"Видео {idx}: Лайки (ошибка сети)")

    # 3. Избранное (Социограм)
    if favs > 0:
      try:
        r = requests.get(
            SOCIOGRAMM_API_URL,
            params={
                "key": SOCIOGRAMM_KEY,
                "action": "add",
                "service": SERVICE_FAVORS,
                "link": link,
                "quantity": favs,
            },
            timeout=10,
        ).json()
        if "order" in r or r.get("status") == "success":
          success_count += 1
        else:
          failed_items.append(f"Видео {idx}: Избранное ({favs} шт.)")
      except:
        failed_items.append(f"Видео {idx}: Избранное (ошибка сети)")

  bot.answer_callback_query(call.id, "Заказы обработаны!")

  status_text = f"✅ **Успешно отправлено заказов:** {success_count}\n"
  if failed_items:
    status_text += (
        "\n❌ **Не удалось отправить (проверь баланс):**\n"
        + "\n".join([f"• {err}" for err in failed_items])
    )

  bot.edit_message_text(status_text, chat_id, call.message.message_id)


def run_bot():
  bot.infinity_polling()


if __name__ == "__main__":
  t = threading.Thread(target=run_bot)
  t.start()
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
