import json
import os
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = "8749615890:AAHqCJAy7Dr23sXF6Z37YrIjxbCMKZ8Vuxw"
ADMIN_ID = 8190804216
BOT_USERNAME = "CRYPWIN_BOT"
WEB_APP_URL = "https://jovial-beignet-2537d3.netlify.app/"

# ===== DATA =====
def load():
    try:
        with open("users.json","r") as f: 
            return json.load(f)
    except:
        return {}

def save(data):
    with open("users.json","w") as f:
        json.dump(data, f, indent=4)

# ===== MENU =====
def menu(uid):
    kb = [
        ["🎮 Play Game","📊 Balance"],
        ["💰 Deposit","💸 Withdraw"],
        ["🔗 Refer","🏆 Leaderboard"],
        ["🏠 Menu"]
    ]
    if uid == ADMIN_ID:
        kb.append(["👨‍💻 Admin Panel"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load()

    ref = context.args[0] if context.args else None

    if uid not in data:
        data[uid] = {"balance":20, "deposit_done":False}

        # Referral bonus
        if ref and ref != uid and ref in data:
            data[ref]["balance"] += 30
            await context.bot.send_message(ref, "🎉 You got ₹30 referral bonus!")

        save(data)
        await update.message.reply_text("🎁 Welcome! You got ₹20 bonus!")

    await update.message.reply_text("🏠 Main Menu", reply_markup=menu(update.effective_user.id))

# ===== MAIN HANDLER =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load()
    text = update.message.text

    if text == "🏠 Menu":
        await update.message.reply_text("🏠 Main Menu", reply_markup=menu(update.effective_user.id))

    elif text == "📊 Balance":
        await update.message.reply_text(f"💰 Balance: ₹{data.get(uid,{}).get('balance',0)}")

    elif text == "🎮 Play Game":
        url = f"{WEB_APP_URL}?uid={uid}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=url))]])
        await update.message.reply_text("🔥 Tap to play:", reply_markup=kb)

    elif text == "🔗 Refer":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        await update.message.reply_text(f"Invite friends & earn ₹30 💸\n{link}")

    elif text == "🏆 Leaderboard":
        sorted_users = sorted(data.items(), key=lambda x: x[1]["balance"], reverse=True)
        msg = "🏆 Top Players:\n\n"
        for i,(u,d) in enumerate(sorted_users[:10]):
            msg += f"{i+1}. {u} → ₹{d['balance']}\n"
        await update.message.reply_text(msg)

    elif text == "💰 Deposit":
        await update.message.reply_text("Enter amount (min ₹101):")
        context.user_data["action"] = "deposit"

    elif context.user_data.get("action") == "deposit":
        try:
            amt = int(text)
            if amt < 101:
                await update.message.reply_text("❌ Minimum ₹101")
                return

            await context.bot.send_message(ADMIN_ID, f"Deposit Request\nUser: {uid}\n₹{amt}")
            await update.message.reply_text("⏳ Waiting for approval")
            context.user_data.clear()
        except:
            await update.message.reply_text("❗ Enter valid number")

    elif text == "💸 Withdraw":
        if not data.get(uid,{}).get("deposit_done"):
            await update.message.reply_text("❌ You must deposit first")
            return
        await update.message.reply_text("Enter amount (min ₹300):")
        context.user_data["action"] = "withdraw"

    elif context.user_data.get("action") == "withdraw":
        try:
            amt = int(text)

            if amt < 300:
                await update.message.reply_text("❌ Minimum ₹300")
                return

            if amt > data[uid]["balance"]:
                await update.message.reply_text("❌ Insufficient balance")
                return

            data[uid]["balance"] -= amt
            save(data)

            await context.bot.send_message(ADMIN_ID, f"Withdraw Request\nUser: {uid}\n₹{amt}")
            await update.message.reply_text("✅ Withdrawal requested")
            context.user_data.clear()

        except:
            await update.message.reply_text("❗ Enter valid number")

# ===== TELEGRAM APP =====
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(MessageHandler(filters.TEXT, handle))

# ===== FLASK SERVER (WEBHOOK) =====
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    await app_bot.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Bot is running 🚀"

# ===== RUN SERVER =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
