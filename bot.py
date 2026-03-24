import json
import os
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8749615890:AAHqCJAy7Dr23sXF6Z37YrIjxbCMKZ8Vuxw"
ADMIN_ID = 8190804216

# 🔗 PUT YOUR NETLIFY GAME URL HERE
WEB_APP_URL = "https://jovial-beignet-2537d3.netlify.app/"

# ===== DATABASE =====
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

# ===== MENU =====
def main_menu(uid):
    keyboard = [
        ["🎮 Play Game", "💰 Balance"],
        ["📥 Deposit", "📤 Withdraw"],
        ["🔗 Refer", "🏆 Leaderboard"]
    ]
    if uid == ADMIN_ID:
        keyboard.append(["⚙️ Admin Panel"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    users = load_users()

    ref = context.args[0] if context.args else None

    if uid not in users:
        users[uid] = {"balance": 20, "deposit_done": False}

        # Referral system
        if ref and ref != uid and ref in users:
            users[ref]["balance"] += 30
            await context.bot.send_message(ref, "🎉 You earned ₹30 referral bonus!")

        save_users(users)
        await update.message.reply_text("🎁 Welcome! ₹20 bonus added!")

    await update.message.reply_text("🏠 Main Menu", reply_markup=main_menu(update.effective_user.id))

# ===== MAIN HANDLER =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    users = load_users()
    text = update.message.text

    if uid not in users:
        users[uid] = {"balance": 0, "deposit_done": False}

    # BALANCE
    if text == "💰 Balance":
        await update.message.reply_text(f"💰 Your balance: ₹{users[uid]['balance']}")

    # GAME BUTTON
    elif text == "🎮 Play Game":
        game_url = f"{WEB_APP_URL}?uid={uid}"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=game_url))]
        ])

        await update.message.reply_text("🔥 Launching Game...", reply_markup=keyboard)

    # DEPOSIT
    elif text == "📥 Deposit":
        await update.message.reply_text("💳 Contact admin to deposit.\nSend payment screenshot after paying.")

    # WITHDRAW
    elif text == "📤 Withdraw":
        if not users[uid]["deposit_done"]:
            await update.message.reply_text("❌ You must deposit first!")
            return

        await update.message.reply_text("💸 Withdrawal request sent to admin.")

    # REFER
    elif text == "🔗 Refer":
        link = f"https://t.me/YOUR_BOT_USERNAME?start={uid}"
        await update.message.reply_text(f"Invite friends & earn ₹30 💸\n{link}")

    # LEADERBOARD
    elif text == "🏆 Leaderboard":
        sorted_users = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)
        msg = "🏆 Top Players:\n\n"

        for i, (u, data) in enumerate(sorted_users[:10]):
            msg += f"{i+1}. {u} → ₹{data['balance']}\n"

        await update.message.reply_text(msg)

# ===== BOT SETUP =====
bot_app = Application.builder().token(BOT_TOKEN).build()

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT, handle))

# ===== FLASK SERVER =====
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Bot is running 🚀"

# ===== START =====
if __name__ == "__main__":
    import asyncio
    asyncio.run(bot_app.initialize())
    asyncio.run(bot_app.start())
    app.run(host="0.0.0.0", port=10000)
