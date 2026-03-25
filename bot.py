import json
import os
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = "8749615890:AAFO_V_-kR_g-gEBiQhsOSOHxnguKabRm_A"
ADMIN_ID = 8190804216
BOT_USERNAME = "CRYPWIN_BOT"
WEB_APP_URL = "https://jovial-beignet-2537d3.netlify.app/"

# ===== DATA =====
def load():
    try:
        return json.load(open("users.json"))
    except:
        return {}

def save(data):
    json.dump(data, open("users.json","w"), indent=4)

# ===== MENU =====
def menu(uid):
    kb = [
        ["🎮 Play Game","📊 Balance"],
        ["💰 Deposit","💸 Withdraw"],
        ["🔗 Refer","🏆 Leaderboard"],
        ["🏠 Menu"]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load()

    ref = context.args[0] if context.args else None

    if uid not in data:
        data[uid] = {"balance":20,"deposit_done":False}

        if ref and ref != uid and ref in data:
            data[ref]["balance"] += 30
            await context.bot.send_message(ref,"🎉 ₹30 referral bonus!")

        save(data)
        await update.message.reply_text("🎁 You got ₹20 bonus!")

    await update.message.reply_text("🏠 Menu", reply_markup=menu(update.effective_user.id))

# ===== MAIN =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load()
    text = update.message.text

    if text == "📊 Balance":
        await update.message.reply_text(f"💰 ₹{data.get(uid,{}).get('balance',0)}")

    elif text == "🎮 Play Game":
        url = f"{WEB_APP_URL}?uid={uid}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Play", web_app=WebAppInfo(url=url))]])
        await update.message.reply_text("Play now 🔥", reply_markup=kb)

# ===== TELEGRAM APP =====
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(MessageHandler(filters.TEXT, handle))

# 🔥 FIXED INIT (NEW WAY)
async def init_bot():
    await app_bot.initialize()
    await app_bot.start()

asyncio.run(init_bot())

# ===== FLASK =====
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    asyncio.run(app_bot.process_update(update))
    return "ok"

@app.route("/")
def home():
    return "Bot running 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
